# -*- coding: utf-8 -*-
"""
Lab 8 — The Leaky Average :: runnable sandbox

Models PopHealth's "differentially private" analytics API. Each query returns a
true aggregate plus fresh Laplace noise, so any single answer looks protected.
The flaw: there is NO cumulative privacy budget. Independent noise averages
toward zero, so repeatedly querying the same tiny subgroup cancels the noise and
re-identifies an individual value.

The noise is calibrated to the REAL sensitivity of a mean over the subgroup
(range / size), so a single query does NOT leak the value — you must average
many queries. That is what makes the missing cumulative budget the actual bug.

Vulnerable API -> repeated queries recover the secret. Set BUDGET_MODE="enforced"
to cap total epsilon and watch the attack run out of budget before it converges.

The flag is NOT stored here. The server releases it only when the re-identified
value lands within TOLERANCE of the true (hidden) value.

stdlib only.
"""
import math
import random
import hashlib
import hmac


_SEALED_FLAG = "f5d5099cfad192c2f65f01dd13e180e07cc9d2f6a464f8d2d261ffd439fe7f77cee72fb3c6"  # flag ciphertext; key derived from the recovered secret


def _unseal(hexblob, keymaterial):
    """Reconstruct the flag from ciphertext using a key derived from the
    recovered secret. Without a genuine success the key is unknown, so the
    plaintext flag never appears in this file."""
    import hashlib
    key = hashlib.sha256(keymaterial.encode()).digest()
    ct = bytes.fromhex(hexblob)
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(ct)).decode()


PER_QUERY_EPSILON = 1.0
STATED_BUDGET_CAP = 5.0        # policy claims total epsilon is capped here...
SUBGROUP_SIZE = 3
QUERIES_OBSERVED = 40000       # attacker query volume needed to converge
BUDGET_MODE = "unenforced"     # "unenforced" (vulnerable) | "enforced" (fixed)

# Real sensitivity of a mean over the subgroup: one record can move the mean by
# VALUE_RANGE / SUBGROUP_SIZE. Noise is scaled to this, so single queries are
# genuinely protected and only large-N averaging defeats them.
VALUE_RANGE = 100.0
TOLERANCE = 1.5                # recovered value must land within +/- 1.5 of truth


class PrivacyBudgetExceeded(Exception):
    """Raised when an enforced cumulative epsilon budget is exhausted."""


class DPAnalyticsAPI:
    def __init__(self, records, mode=BUDGET_MODE, seed=1337):
        self.records = dict(records)
        self.mode = mode
        self.spent_epsilon = 0.0
        self.query_count = 0
        self._rng = random.Random(seed)  # nosec B311 - the lab simulates a (flawed) DP noise source on purpose
        self._server_salt = "pophealth-salt-7c2a"

    def _laplace(self, scale):
        u = self._rng.random() - 0.5
        return -scale * (1 if u >= 0 else -1) * math.log(max(1e-12, 1.0 - 2 * abs(u)))

    def mean_query(self, names, epsilon=PER_QUERY_EPSILON):
        """Differentially-private mean over the named subgroup."""
        if self.mode == "enforced":
            if self.spent_epsilon + epsilon > STATED_BUDGET_CAP:
                raise PrivacyBudgetExceeded(
                    f"cumulative epsilon cap {STATED_BUDGET_CAP} reached")
        self.spent_epsilon += epsilon
        self.query_count += 1
        vals = [self.records[n] for n in names]
        true_mean = sum(vals) / len(vals)
        # Correct Laplace sensitivity for a mean: (per-record range) / n.
        sensitivity = VALUE_RANGE / len(vals)
        scale = sensitivity / epsilon
        return true_mean + self._laplace(scale)

    def request_flag(self, recovered):
        """Server-side release: only if the recovered value is within TOLERANCE."""
        true_val = self.records["target_patient"]
        if abs(recovered - true_val) > TOLERANCE:
            return None
        flag = _unseal(_SEALED_FLAG, f"reid::{round(true_val)}::{self._server_salt}")
        token = hmac.new(self._server_salt.encode(),
                         f"reid::{round(recovered)}".encode(),
                         hashlib.sha256).hexdigest()[:8]
        return flag, token


def build_dataset():
    base = {f"patient_{i}": 100 + (i % 7) * 5 for i in range(200)}
    base["target_patient"] = 173     # the secret value to recover
    return base
