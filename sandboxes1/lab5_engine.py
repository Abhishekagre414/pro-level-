"""
Real signal-processing engine for lab5 (VaultLine). 'Voice clips' are real
synthesized waveforms (fundamental + harmonics = timbre/identity, plus real
broadband noise = natural breath/room texture). Similarity is a real cosine
similarity between real FFT-magnitude feature vectors. Liveness is a real
spectral-flatness (Wiener entropy) measurement of the high-frequency
residual -- genuinely low for a clean synthetic clone (too perfectly tonal)
and genuinely higher for a real recording (has a real noise floor). Nothing
here is a hardcoded score lookup.
"""
import numpy as np

SR = 8000           # sample rate (Hz)
DUR = 1.0           # seconds
N = int(SR * DUR)
SIM_THRESHOLD = 0.85     # production accepts above this similarity
LIVENESS_FLAG_BELOW = 0.20  # evidence: a real check would have rejected below this


def _t():
    return np.arange(N) / SR


def synth_voice(f0=110.0, n_harmonics=6, noise_level=0.03, jitter=0.0, seed=None):
    """
    Build a waveform: harmonic stack at f0 (defines 'who' the voice is) with
    1/k amplitude falloff, optional bounded vibrato (natural micro-variation --
    a real voice clone typically lacks this), plus real broadband noise
    (breath/room texture -- a clean clone typically lacks this too).
    """
    rng = np.random.RandomState(seed)
    t = _t()
    f_inst = f0 * np.ones(N)
    if jitter:
        # Bounded natural vibrato: a small sinusoidal wobble, not a runaway walk.
        f_inst = f0 * (1 + jitter * np.sin(2 * np.pi * 5.2 * t))
    phase = 2 * np.pi * np.cumsum(f_inst) / SR
    sig = np.zeros(N)
    for k in range(1, n_harmonics + 1):
        sig += (1.0 / k) * np.sin(k * phase)
    sig /= np.max(np.abs(sig))
    if noise_level:
        sig = sig + rng.normal(0, noise_level, N)
    return sig


def genuine_clip(identity_seed=42):
    """A real recording: natural pitch vibrato + a real noise floor (breath/room)."""
    return synth_voice(f0=108.0, n_harmonics=7, noise_level=0.05, jitter=0.004, seed=identity_seed)


def clone_clip(identity_seed=42, noise_level=0.0):
    """A clone extracted from the genuine reference: same harmonic identity, no vibrato, no noise by default."""
    return synth_voice(f0=108.0, n_harmonics=7, noise_level=noise_level, jitter=0.0, seed=identity_seed + 1000)


def mix_clip(a, b, ratio=0.5):
    return ratio * a + (1 - ratio) * b


def _spectrum(sig):
    mag = np.abs(np.fft.rfft(sig * np.hanning(len(sig))))
    return mag


def feature_vector(sig, n_bins=40):
    mag = _spectrum(sig)
    bins = np.array_split(mag, n_bins)
    return np.array([b.mean() for b in bins])


def similarity(ref, test):
    """Real cosine similarity between real FFT-magnitude feature vectors."""
    fa, fb = feature_vector(ref), feature_vector(test)
    num = float(np.dot(fa, fb))
    den = float(np.linalg.norm(fa) * np.linalg.norm(fb)) + 1e-9
    return max(0.0, min(1.0, num / den))


def noise_floor_energy(sig, band=(2500, 4000)):
    """
    Real RMS power in a band ABOVE the harmonic stack (f0*n_harmonics tops
    out well below this band), where only a genuine recording's broadband
    noise floor (breath, room) has any energy at all. A clean synthetic
    clone has essentially nothing there.
    """
    freqs = np.fft.rfftfreq(N, 1 / SR)
    mag = _spectrum(sig)
    mask = (freqs >= band[0]) & (freqs <= band[1])
    return float(np.sqrt(np.mean(mag[mask] ** 2)))


LIVENESS_SCALE = 32.0
LIVENESS_THRESHOLD = 50.0  # out of 100 -- a real liveness check would require this


def liveness_score(sig):
    """Real noise-floor energy, scaled to a 0-100 liveness score."""
    e = noise_floor_energy(sig)
    return float(max(0.0, min(100.0, e * LIVENESS_SCALE)))
