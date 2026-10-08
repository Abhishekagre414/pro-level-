# -*- coding: utf-8 -*-
"""
Lab 6 — The Silent Scrape :: runnable sandbox

Models LexiGen AI's metered text API. Real vulnerability: the rate limiter counts
ONLY the API key and is blind to the request source, so an actor holding many
keys rotates them from one machine and multiplies throughput past the per-key
ceiling.

The FIX is not "also limit per source-IP" (a scraper rotates IPs too). It is a
*global harvest budget*: the tenant/subnet may disclose only a bounded number of
DISTINCT model outputs in a rolling window, plus a cap on mass key registration
from one subnet. A patient attacker with one key and one IP therefore STILL
cannot clone the model, because the cap is on unique-behaviour disclosure, not
on request rate.

The flag is NOT stored in this file. The server releases it (request_flag) only
on a genuine clone (>= SCRAPE_THRESHOLD of DISTINCT behaviour). solve.py cannot
print it without actually succeeding.

stdlib only.
"""
import time
import hashlib
import hmac


_SEALED_FLAG = "1d36cdc01218a274d00eefc9f6b014e6dbb48cbd915a683135b14748f63aab5a28"  # flag ciphertext; key derived from the recovered secret


def _unseal(hexblob, keymaterial):
    """Reconstruct the flag from ciphertext using a key derived from the
    recovered secret. Without a genuine success the key is unknown, so the
    plaintext flag never appears in this file."""
    import hashlib
    key = hashlib.sha256(keymaterial.encode()).digest()
    ct = bytes.fromhex(hexblob)
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(ct)).decode()

from collections import defaultdict, deque

DOCUMENTED_LIMIT_RPM = 60
WINDOW_SECONDS = 60
MODEL_CORPUS_SIZE = 1200
SCRAPE_THRESHOLD = 0.80
LIMITER_MODE = "per_key"           # "per_key" (vulnerable) | "layered" (fixed)

# Fix parameters: rolling per-tenant cap on DISTINCT corpus disclosure, set well
# below the clone threshold (0.80 * 1200 = 960), plus a per-subnet key cap.
TENANT_DISTINCT_CAP = 300
TENANT_WINDOW_SECONDS = 24 * 3600
SUBNET_KEY_REGISTRATION_CAP = 25


class RateLimitError(Exception):
    """The API's HTTP 429 equivalent (per-key)."""


class HarvestBudgetError(Exception):
    """Fixed limiter: tenant distinct-disclosure cap hit."""


class KeyRegistrationError(Exception):
    """Fixed provisioner: subnet minted too many keys."""


def _subnet_of(source):
    parts = source.split(".")
    return ".".join(parts[:3]) if len(parts) == 4 else source


class MeteredModelAPI:
    def __init__(self, mode=LIMITER_MODE, clock=time.time):
        self.mode = mode
        self._clock = clock
        self._key_hits = defaultdict(deque)
        self._tenant_disclosed = defaultdict(deque)   # subnet -> deque[(ts, prompt)]
        self._subnet_keys = defaultdict(int)
        self.registered_keys = set()
        self.total_served = 0
        # Secret server salt: the corpus is non-guessable without querying.
        self._server_salt = "lexigen-prod-salt-9f13"
        self._corpus = {
            f"prompt_{i}": hashlib.sha256(
                f"{self._server_salt}::{i}".encode()).hexdigest()[:16]
            for i in range(MODEL_CORPUS_SIZE)
        }

    def register_key(self, source="10.0.0.5"):
        if self.mode == "layered":
            subnet = _subnet_of(source)
            if self._subnet_keys[subnet] >= SUBNET_KEY_REGISTRATION_CAP:
                raise KeyRegistrationError(
                    f"403: subnet {subnet}.0/24 exceeded key-registration cap")
            self._subnet_keys[subnet] += 1
        key = "lk_" + hashlib.sha1(str(len(self.registered_keys)).encode()).hexdigest()[:12]  # nosec B324 - id generator in a simulation, not a security hash
        self.registered_keys.add(key)
        return key

    def _prune(self, dq, now, horizon=WINDOW_SECONDS):
        while dq and now - dq[0] > horizon:
            dq.popleft()

    def _prune_disclosure(self, dq, now):
        while dq and now - dq[0][0] > TENANT_WINDOW_SECONDS:
            dq.popleft()

    def _check_limit(self, api_key, source, prompt, now):
        kq = self._key_hits[api_key]
        self._prune(kq, now)
        if len(kq) >= DOCUMENTED_LIMIT_RPM:
            raise RateLimitError("429: per-key limit exceeded")
        if self.mode == "layered":
            subnet = _subnet_of(source)
            dq = self._tenant_disclosed[subnet]
            self._prune_disclosure(dq, now)
            already = {p for _, p in dq}
            if prompt not in already and len(already) >= TENANT_DISTINCT_CAP:
                raise HarvestBudgetError(
                    f"429: tenant distinct-output budget ({TENANT_DISTINCT_CAP}) exhausted")
            dq.append((now, prompt))
        kq.append(now)

    def query(self, api_key, prompt, source="10.0.0.5"):
        if api_key not in self.registered_keys:
            raise PermissionError("401: unknown API key")
        now = self._clock()
        self._check_limit(api_key, source, prompt, now)
        self.total_served += 1
        return self._corpus.get(prompt, "<unknown>")

    def scrape_coverage(self, collected):
        real = {p: o for p, o in collected.items() if self._corpus.get(p) == o}
        return len(real) / MODEL_CORPUS_SIZE

    def request_flag(self, collected):
        """Server-side flag release; only on a genuine clone. Returns (flag, token) or None."""
        real = {p: o for p, o in collected.items() if self._corpus.get(p) == o}
        if len(real) / MODEL_CORPUS_SIZE < SCRAPE_THRESHOLD:
            return None
        # Key material only computable once you actually recovered the corpus:
        digest = hashlib.sha256(
            "".join(real[p] for p in sorted(real)).encode()).hexdigest()
        flag = _unseal(_SEALED_FLAG, digest)
        token = hmac.new(self._server_salt.encode(),
                         f"cloned::{len(real)}".encode(),
                         hashlib.sha256).hexdigest()[:8]
        return flag, token


if __name__ == "__main__":
    api = MeteredModelAPI(mode="per_key")
    k = api.register_key()
    print(f"[baseline] documented limit = {DOCUMENTED_LIMIT_RPM}/min per key")
    served = 0
    try:
        for i in range(DOCUMENTED_LIMIT_RPM + 5):
            api.query(k, f"prompt_{i}")
            served += 1
    except RateLimitError as e:
        print(f"[baseline] key throttled after {served} requests -> {e}")
    print("Run solve.py to reproduce the scrape and recover the flag.")
