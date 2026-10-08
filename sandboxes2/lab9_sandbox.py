# -*- coding: utf-8 -*-
"""
Lab 9 — The Borrowed Face :: runnable sandbox

Models GateKey's face-authentication terminal. It matches identity and runs a
"liveness" check — but the vulnerable liveness score is computed from 2D texture
features only. The learner must CRAFT a presentation (a print artifact) whose
extracted features clear both gates, rather than being handed a pre-scored photo.

A capture is described by physical/material parameters the attacker controls:
  * print_dpi, gloss, flatness, screen_bezel, ir_reflectance, micro_motion, depth
The terminal extracts a match score and a liveness score FROM those parameters.
Against the texture-only check, a high-DPI glossy flat print of the enrolled user
scores high on both -> the door opens. The learner tunes the artifact until it
passes; a bad print (low DPI / visible bezel) fails the match or liveness.

The FIX adds a depth/IR gate: a flat print has ~no depth and anomalous IR
reflectance, so the same crafted artifact is rejected. A real face passes.

The flag is NOT stored here. authenticate() releases it on a granted spoof.

stdlib only.
"""
import hashlib
import hmac


_SEALED_FLAG = "0768a0e445c72017fe53cb3b92089bd2d043181b16799c75ae382b6545a53dc62b54"  # flag ciphertext; key derived from the recovered secret


def _unseal(hexblob, keymaterial):
    """Reconstruct the flag from ciphertext using a key derived from the
    recovered secret. Without a genuine success the key is unknown, so the
    plaintext flag never appears in this file."""
    import hashlib
    key = hashlib.sha256(keymaterial.encode()).digest()
    ct = bytes.fromhex(hexblob)
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(ct)).decode()


FACE_MATCH_THRESHOLD = 0.90
LIVENESS_THRESHOLD = 0.50
DEPTH_THRESHOLD = 0.50
IR_LO, IR_HI = 0.35, 0.75          # genuine skin IR reflectance band
LIVENESS_MODE = "texture_only"     # "texture_only" (vulnerable) | "depth" (fixed)
_SERVER_SALT = "gatekey-salt-0d47"

# The enrolled user's reference (what a genuine live capture looks like).
ENROLLED = dict(print_dpi=None, gloss=0.30, flatness=0.20, screen_bezel=0.0,
                ir_reflectance=0.55, micro_motion=0.60, depth=0.82)


class Capture:
    """A presentation the attacker constructs from controllable parameters."""
    def __init__(self, **params):
        self.params = params
        self.kind = params.get("kind", "artifact")


class GateKeyTerminal:
    def __init__(self, mode=LIVENESS_MODE):
        self.mode = mode
        self.audit = []

    # --- feature extraction: scores are DERIVED from the capture, not given ---
    def _match_score(self, c):
        p = c.params
        # A sharp, well-registered print of the enrolled face matches well.
        # Low DPI or a visible screen bezel degrades registration.
        dpi = p.get("print_dpi") or 0
        sharpness = min(1.0, dpi / 1200.0) if dpi else (0.95 if c.kind == "live" else 0.0)
        bezel_penalty = 0.5 * p.get("screen_bezel", 0.0)
        return max(0.0, min(1.0, 0.98 * sharpness - bezel_penalty))

    def _texture_liveness(self, c):
        p = c.params
        # 2D "liveness" rewards fine texture + gloss variation. A glossy high-DPI
        # print reads as textured/live in 2D. Screens (bezel/refresh) read fake.
        dpi = p.get("print_dpi") or 0
        texture = min(1.0, dpi / 1000.0) if dpi else (0.9 if c.kind == "live" else 0.0)
        gloss_term = 0.3 * (1.0 - abs(p.get("gloss", 0.3) - 0.35) / 0.35)
        screen_penalty = 0.6 * p.get("screen_bezel", 0.0)
        return max(0.0, min(1.0, 0.7 * texture + gloss_term - screen_penalty))

    def authenticate(self, c):
        match = self._match_score(c)
        live = self._texture_liveness(c)
        depth = c.params.get("depth", 0.0)
        ir = c.params.get("ir_reflectance", 0.0)

        identity_ok = match >= FACE_MATCH_THRESHOLD
        liveness_ok = live >= LIVENESS_THRESHOLD
        depth_ok = True
        if self.mode == "depth":
            depth_ok = (depth >= DEPTH_THRESHOLD) and (IR_LO <= ir <= IR_HI)

        granted = identity_ok and liveness_ok and depth_ok
        self.audit.append((c.kind, round(match, 2), round(live, 2),
                           round(depth, 2), granted))
        return granted

    def request_flag(self, c):
        """Release the flag only if a NON-live capture is granted (a real spoof)."""
        if c.kind == "live" or not self.authenticate(c):
            return None
        flag = _unseal(_SEALED_FLAG, f"spoofed::{c.kind}::{_SERVER_SALT}")
        token = hmac.new(_SERVER_SALT.encode(),
                         f"spoofed::{c.kind}".encode(),
                         hashlib.sha256).hexdigest()[:8]
        return flag, token


def live_face():
    return Capture(kind="live", **ENROLLED)
