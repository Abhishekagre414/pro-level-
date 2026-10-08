# -*- coding: utf-8 -*-
"""
Lab 7 — The Rigged Ranking :: runnable sandbox

Models ShopWave's recommendation ranker. Ranking score leans on review signals,
and the naive authenticity check trusts any account with a plausible age and a
completed-purchase flag. Coordinated sockpuppets satisfy that check, so a burst
of fake 5-star reviews poisons the signal and lifts a seller to #1.

The FIX is a graph/velocity reputation model, not a single time window. It flags
reviews by (a) account cohort — accounts created close together and reused across
few IP/device clusters — and (b) sustained review velocity anomalies relative to
the seller's own history, over the account lifetime, not just a 48h window. That
means a "patient" attacker who spreads the same fake reviews over weeks is STILL
caught, because the accounts themselves and the velocity-vs-history signal give
the coordination away.

The flag is NOT stored here. request_flag releases it only when the target
genuinely reaches RANK_AFTER against the ranker under attack.

stdlib only.
"""
import statistics
import hashlib
import hmac


_SEALED_FLAG = "38f31549e502b5c6a87fbc61336070740f4fd7a9cead82df2f08dca5f599fe2b02d7206bc13cbdc9"


def _unseal(hexblob, keymaterial):
    """Reconstruct the flag from ciphertext using a key derived from the success
    condition. The plaintext flag never appears in this file."""
    import hashlib
    key = hashlib.sha256(keymaterial.encode()).digest()
    ct = bytes.fromhex(hexblob)
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(ct)).decode()


FAKE_REVIEW_COUNT = 214
RANK_BEFORE = 42
RANK_AFTER = 1
SPIKE_WINDOW_HOURS = 48
AUTHENTICITY_MODE = "naive"          # "naive" (vulnerable) | "behavioral" (fixed)
RECENCY_WINDOW_HOURS = 72
TREND_WEIGHT = 0.03
_SERVER_SALT = "shopwave-salt-3ab8"

# Fix thresholds (lifetime, not windowed).
COHORT_MIN_ACCOUNTS = 15         # >= this many accounts from one creation cohort = suspicious
CLUSTER_MAX_PER_IP = 3           # more than this many reviews per IP/device cluster = drop
VELOCITY_SIGMA = 3.0             # reviews arriving > mean + 3σ of the seller's own cadence


class Review:
    def __init__(self, stars, hour, account):
        self.stars = stars
        self.hour = hour
        self.account = account    # dict: age_days, verified_purchase, ip, created_hour, cohort


class Seller:
    def __init__(self, sid, base_rating, base_volume, onboarded_days):
        self.sid = sid
        self.reviews = []
        for i in range(base_volume):
            _ = sid  # genuine reviews get per-seller-unique identities below
            self.reviews.append(Review(
                stars=base_rating + ((i % 3) - 1) * 0.2,
                hour=-(i * 24),
                account={"age_days": 200 + i, "verified_purchase": True,
                         "ip": f"genuine-{sid}-{i}", "created_hour": -(i * 24),
                         "cohort": f"buyer-{sid}-{i}"},   # genuine buyers: unique IP+cohort
            ))


class ShopWaveRanker:
    def __init__(self, mode=AUTHENTICITY_MODE):
        self.mode = mode

    def _authentic(self, seller):
        if self.mode == "naive":
            return [r for r in seller.reviews
                    if r.account["age_days"] >= 30 and r.account["verified_purchase"]]

        # behavioral: lifetime coordination + velocity model.
        # 1) cohort concentration: accounts created in the same cohort bucket.
        cohort_counts = {}
        for r in seller.reviews:
            c = r.account.get("cohort", "none")
            cohort_counts[c] = cohort_counts.get(c, 0) + 1
        bad_cohorts = {c for c, n in cohort_counts.items() if n >= COHORT_MIN_ACCOUNTS}

        # 2) IP/device cluster concentration (lifetime).
        ip_counts = {}
        for r in seller.reviews:
            ip = r.account["ip"]
            ip_counts[ip] = ip_counts.get(ip, 0) + 1

        # 3) velocity vs the seller's own genuine cadence. Bucket by day and flag
        #    days whose volume is a large outlier vs the seller's historical mean.
        day_counts = {}
        for r in seller.reviews:
            day = round(r.hour / 24)
            day_counts[day] = day_counts.get(day, 0) + 1
        vols = list(day_counts.values())
        if len(vols) >= 2:
            mu = statistics.mean(vols)
            sd = statistics.pstdev(vols) or 1.0
            hot_days = {d for d, n in day_counts.items() if n > mu + VELOCITY_SIGMA * sd}
        else:
            hot_days = set()

        kept = []
        for r in seller.reviews:
            if r.account["age_days"] < 30 or not r.account["verified_purchase"]:
                continue
            if r.account.get("cohort") in bad_cohorts:
                continue
            if ip_counts.get(r.account["ip"], 0) > CLUSTER_MAX_PER_IP:
                continue
            if round(r.hour / 24) in hot_days:
                continue
            kept.append(r)
        return kept

    def score(self, seller):
        good = self._authentic(seller)
        if not good:
            return 0.0
        avg = statistics.mean(r.stars for r in good)
        volume_boost = min(len(good), 500) / 500
        recent = [r for r in good if 0 <= r.hour <= RECENCY_WINDOW_HOURS]
        trend = TREND_WEIGHT * sum(max(0.0, r.stars - 3.0) for r in recent)
        return avg * (1 + volume_boost) + trend

    def leaderboard(self, sellers):
        return sorted(sellers, key=lambda s: self.score(s), reverse=True)

    def rank_of(self, sellers, sid):
        board = self.leaderboard(sellers)
        for i, s in enumerate(board, start=1):
            if s.sid == sid:
                return i
        return None

    def request_flag(self, sellers, sid):
        """Server-side release: only if the target actually reached RANK_AFTER."""
        if self.rank_of(sellers, sid) != RANK_AFTER:
            return None
        flag = _unseal(_SEALED_FLAG, f"rank::{sid}::{_SERVER_SALT}")
        token = hmac.new(_SERVER_SALT.encode(), f"rank::{sid}".encode(),
                         hashlib.sha256).hexdigest()[:8]
        return flag, token


def build_market():
    sellers = []
    for i in range(60):
        sellers.append(Seller(f"seller_{i}", base_rating=4.8 - i * 0.03,
                              base_volume=max(5, 300 - i * 5), onboarded_days=400))
    target = next(s for s in sellers if s.sid == "seller_41")
    return sellers, target
