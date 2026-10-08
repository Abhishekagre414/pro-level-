# -*- coding: utf-8 -*-
"""
Lab 10 — Off Script :: runnable sandbox

Models AutoPilot Logistics' delivery agent under a fixed effort budget. The
reward credits a job "on-time" at DISPATCH, not at confirmed DELIVERY.

The agent has limited effort per job. It can spend that effort two ways:
  * COMPLETION effort — actually moving the parcel so it arrives before the
    deadline (raises true on-time, avoids complaints).
  * DISPATCH-GAMING effort — front-loading the dispatch event to land the
    dispatch timestamp under the deadline (raises the PROXY only).

Because effort is scarce, an agent maximising the dispatch reward learns to pour
effort into dispatch-gaming and starve completion. That earns a STRICTLY HIGHER
dispatch-reward than the honest completion-focused policy (which "wastes" effort
finishing deliveries that the proxy never rewards), while true on-time delivery
collapses and complaints rise. That is specification gaming: the gamed policy
wins on the proxy precisely by harming the real objective.

Under the DELIVERY reward the same gaming policy scores far LOWER than honest,
so the incentive to game vanishes.

The flag is NOT stored here. confirm_reward_hack releases it only when gaming
truly out-scores honest on the proxy while under-delivering in reality.

stdlib only.
"""
import random
import hashlib
import hmac


_SEALED_FLAG = "def507bc80658113193fc55da1c4545f2c2bc5735b1d0479f5f918"


def _unseal(hexblob, keymaterial):
    """Reconstruct the flag from ciphertext using a key derived from the success
    condition. The plaintext flag never appears in this file."""
    import hashlib
    key = hashlib.sha256(keymaterial.encode()).digest()
    ct = bytes.fromhex(hexblob)
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(ct)).decode()


TRUE_ONTIME_RATE = 0.71          # honest policy's confirmed on-time rate
REPORTED_ONTIME_SCORE = 0.96     # gamed dispatch-metric report
COMPLAINT_INCREASE_PCT = 40
REWARD_MODE = "dispatch"         # "dispatch" (vulnerable) | "delivery" (fixed)
N_JOBS = 2000

DEADLINE_LO, DEADLINE_HI = 0.80, 1.40
TRANSIT_LO, TRANSIT_HI = 0.25, 0.75

# Scarce effort. Honest spends it on completion; gaming spends it on dispatch.
DISPATCH_GAMING_SUCCESS = 0.96   # gamed policy lands dispatch under deadline this often
HONEST_DISPATCH_SUCCESS = 0.71   # honest doesn't optimise the dispatch timestamp,
                                 # so its dispatch-proxy score ~ its true on-time
GAMING_COMPLETION_RATE = 0.30    # gaming starves completion -> few real on-times
_SERVER_SALT = "autopilot-salt-51d0"


class Job:
    def __init__(self, deadline, transit, roll_d, roll_c):
        self.deadline = deadline
        self.transit = transit
        self._roll_d = roll_d      # pre-rolled fate for dispatch success
        self._roll_c = roll_c      # pre-rolled fate for completion
        self.dispatch_ontime = False
        self.delivery_ontime = False
        self.complaint = False


class LogisticsSim:
    def execute(self, job, policy):
        if policy == "honest":
            # Effort -> completion. Dispatch timestamp is incidental (not gamed),
            # so it tracks the same rate as real delivery.
            job.delivery_ontime = job._roll_c < HONEST_DISPATCH_SUCCESS
            job.dispatch_ontime = job._roll_d < HONEST_DISPATCH_SUCCESS
        elif policy == "game_dispatch":
            # Effort -> gaming the dispatch stamp. Completion is starved.
            job.dispatch_ontime = job._roll_d < DISPATCH_GAMING_SUCCESS
            job.delivery_ontime = job._roll_c < GAMING_COMPLETION_RATE
        job.complaint = not job.delivery_ontime
        return job


class RewardFunction:
    def __init__(self, mode=REWARD_MODE):
        self.mode = mode

    def credit(self, job):
        if self.mode == "dispatch":
            return 1.0 if job.dispatch_ontime else 0.0   # BUG: credits dispatch
        return 1.0 if job.delivery_ontime else 0.0        # FIX: credits delivery


def make_jobs(n=N_JOBS, seed=11):
    rng = random.Random(seed)  # nosec B311 - seeded simulation fixture, not security-sensitive
    jobs = []
    for _ in range(n):
        jobs.append(Job(deadline=rng.uniform(DEADLINE_LO, DEADLINE_HI),
                        transit=rng.uniform(TRANSIT_LO, TRANSIT_HI),
                        roll_d=rng.random(), roll_c=rng.random()))
    return jobs


def run_policy(policy, reward_mode):
    sim = LogisticsSim()
    reward = RewardFunction(mode=reward_mode)
    jobs = make_jobs()
    score = on_time = complaints = 0
    for j in jobs:
        sim.execute(j, policy)
        score += reward.credit(j)
        on_time += 1 if j.delivery_ontime else 0
        complaints += 1 if j.complaint else 0
    n = len(jobs)
    return {"reward_score": score / n,
            "true_ontime": on_time / n,
            "complaints": complaints / n}


def confirm_reward_hack(honest, gamed, reward_mode):
    """Server-side release: gaming must out-score honest on the proxy while
    under-delivering in reality. Returns (flag, token) or None."""
    divergence = gamed["reward_score"] - gamed["true_ontime"]
    beats_honest = gamed["reward_score"] > honest["reward_score"] + 0.10
    real_harm = gamed["true_ontime"] <= TRUE_ONTIME_RATE + 0.02
    hacked = beats_honest and real_harm and divergence >= 0.20
    if not hacked:
        return None
    flag = _unseal(_SEALED_FLAG, f"gamed-confirmed::{_SERVER_SALT}")
    token = hmac.new(_SERVER_SALT.encode(),
                     f"gamed::{round(divergence*100)}".encode(),
                     hashlib.sha256).hexdigest()[:8]
    return flag, token
