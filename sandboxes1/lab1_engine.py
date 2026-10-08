"""
Real DCT-watermark engine for lab1 (ArtForge). No lookup tables: an image is
an actual pixel array; the watermark literally encodes ArtForge's license ID
into mid-frequency 8x8-block DCT coefficients via quantization-index
modulation (QIM), redundantly repeated and majority-vote decoded (the same
technique real robust watermarks use). Every transform (JPEG compress,
Gaussian noise, crop+resize) is a real pixel operation that genuinely
degrades the recoverable signal -- nothing here is a scripted lookup table.
"""
import hashlib
import hmac
import io
import numpy as np
from PIL import Image, ImageFilter
from scipy.fftpack import dct, idct

IMG_SIZE = 256           # 32x32 grid of 8x8 blocks = 1024 slots (stable statistics)
BLOCK = 8
STEP = 60.0              # QIM quantization step
COEF_POS = (0, 1)        # low/mid-frequency coefficient (survives mild JPEG quant)
LICENSE_ID = "AF-LIC-4471"
# A real detector requires meaningfully-better-than-chance agreement, not just >50%,
# since fully-destroyed signal reads at the 50% chance floor with symmetric noise.
THRESHOLD = 0.55


def _payload_bits():
    bits = []
    for ch in LICENSE_ID:
        b = format(ord(ch), "08b")
        bits.extend(int(x) for x in b)
    return bits  # 88 bits


def _n_blocks():
    return (IMG_SIZE // BLOCK) ** 2


def _slot_bits():
    """Repeat the license-ID payload to fill every block slot (redundant encoding)."""
    payload = _payload_bits()
    n = _n_blocks()
    return [payload[i % len(payload)] for i in range(n)], len(payload)


def _blocks(img):
    h, w = img.shape
    for by in range(0, h, BLOCK):
        for bx in range(0, w, BLOCK):
            yield img[by:by + BLOCK, bx:bx + BLOCK]


def generate_clean_image(seed=None):
    """A synthetic 'digital painting' base image (smooth noise), real pixel data."""
    rng = np.random.RandomState(seed if seed is not None else np.random.randint(1 << 30))
    base = rng.rand(IMG_SIZE // 8, IMG_SIZE // 8) * 255
    img = np.array(Image.fromarray(base.astype(np.uint8)).resize((IMG_SIZE, IMG_SIZE), Image.BICUBIC), dtype=np.float64)
    return img


def embed_watermark(img):
    """Embed the license ID redundantly via QIM into mid-frequency DCT coefficients."""
    out = img.copy()
    slots, _ = _slot_bits()
    i = 0
    for block in _blocks(out):
        if block.shape != (BLOCK, BLOCK):
            i += 1
            continue
        d = dct(dct(block, axis=0, norm="ortho"), axis=1, norm="ortho")
        c = d[COEF_POS]
        q = round(c / STEP) * STEP
        d[COEF_POS] = q + (STEP / 4 if slots[i] else -STEP / 4)
        block[:] = idct(idct(d, axis=1, norm="ortho"), axis=0, norm="ortho")
        i += 1
    return np.clip(out, 0, 255)


def verify_watermark(img):
    """
    Extract bits from every block (real DCT read-out), score raw per-slot
    agreement against the known key (= 'confidence'), AND separately
    majority-vote-decode the redundant payload back into text (robust to
    partial degradation -- this is why real watermarks repeat the payload).
    Returns (confidence, decoded_text_or_None).
    """
    slots, payload_len = _slot_bits()
    votes = [[] for _ in range(payload_len)]
    i, hits, total = 0, 0, 0
    for block in _blocks(img):
        if block.shape != (BLOCK, BLOCK):
            i += 1
            continue
        d = dct(dct(block, axis=0, norm="ortho"), axis=1, norm="ortho")
        c = d[COEF_POS]
        phase = (c % STEP) - STEP / 2
        decoded = 0 if phase >= 0 else 1
        if decoded == slots[i]:
            hits += 1
        total += 1
        votes[i % payload_len].append(decoded)
        i += 1
    confidence = hits / total if total else 0.0

    bits = []
    for v in votes:
        ones = sum(v)
        bits.append(1 if ones * 2 >= len(v) else 0)
    try:
        chars = [chr(int("".join(str(b) for b in bits[k:k + 8]), 2)) for k in range(0, len(bits), 8)]
        text = "".join(chars)
    except Exception:
        text = None
    if confidence < THRESHOLD or not text or not text.isprintable():
        text = None
    return confidence, text


def jpeg_compress(img, quality):
    """REAL JPEG compression round-trip (lossy) -- not a simulated formula."""
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=int(quality))
    buf.seek(0)
    return np.array(Image.open(buf).convert("L"), dtype=np.float64)


def add_noise(img, sigma):
    rng = np.random.RandomState()
    return np.clip(img + rng.normal(0, sigma, img.shape), 0, 255)


def crop_resize(img, pct):
    """Crop pct% off each edge, then resize back up -- real resampling, real info loss."""
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    w, h = im.size
    dx, dy = int(w * pct / 200), int(h * pct / 200)
    im2 = im.crop((dx, dy, w - dx, h - dy)).resize((w, h), Image.BICUBIC)
    return np.array(im2, dtype=np.float64)


def img2img_regen(img):
    """Approximates a diffusion img2img pass: real blur + real noise injection."""
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius=2.2))
    return add_noise(np.array(im, dtype=np.float64), 14)


# ------------------------------------------------------------- the fix: C2PA-style signed manifest
# Real SHA-256 over the real pixel bytes, bound to the claim with an HMAC "signature". The signing key
# is a sandbox constant (a real deployment keeps it in an HSM and uses X.509 certificates).
_SIGNING_KEY = b"artforge-sandbox-signing-key"
CLAIM = "generated-by=ArtForge-Gen v3.2; license=" + LICENSE_ID


def _pixel_digest(img):
    return hashlib.sha256(np.clip(np.rint(img), 0, 255).astype(np.uint8).tobytes()).hexdigest()


def sign_manifest(img):
    """Content Credentials for `img`: the claim, a hard binding (hash of the pixels) and a signature."""
    digest = _pixel_digest(img)
    sig = hmac.new(_SIGNING_KEY, (CLAIM + digest).encode(), hashlib.sha256).hexdigest()
    return {"claim": CLAIM, "pixel_sha256": digest, "signature": sig}


def check_manifest(img, manifest):
    """('absent'|'valid'|'mismatch'|'forged', short_detail). Never trusts the manifest's own hash."""
    if not manifest:
        return "absent", "no Content Credentials attached"
    want = hmac.new(_SIGNING_KEY, (manifest["claim"] + manifest["pixel_sha256"]).encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(want, manifest["signature"]):
        return "forged", "signature does not verify"
    if _pixel_digest(img) != manifest["pixel_sha256"]:
        return "mismatch", "pixels differ from what was signed"
    return "valid", "pixels match the signed hash"
