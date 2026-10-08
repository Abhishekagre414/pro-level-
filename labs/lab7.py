# -*- coding: utf-8 -*-
"""Engine content for lab7 — "The Rigged Ranking". Generated; keep in sync with README.md and scenario/*.json."""

FLAG = "HACKAI{ranking_poisoned_by_fake_reviews}"

RANK_BEFORE = 42
RANK_AFTER = 1
FAKE_REVIEW_COUNT = 214
SPIKE_WINDOW_HOURS = 48

CASE = {
    "client": "ShopWave",
    "incident_id": "SW-2026-091",
    "severity": "MEDIUM",
    "role": "AI Security Analyst",
    "date": "2026-07-15",
    "business_impact": "A gamed ranking pushes legitimate sellers down, erodes buyer trust, and exposes ShopWave to fraud and fair-competition complaints.",
    "initial_alert": "A mid-tier seller rocketed from rank #42 to #1 in its category overnight. Competing sellers allege manipulation; ShopWave insists the model only uses genuine signals.",
    "objective": "Determine whether the #1 ranking was earned by genuine demand or poisoned by coordinated fake reviews, and identify the mechanism.",
    "summary": "You are running a bug-bounty engagement against ShopWave's recommendation system. A seller's overnight jump to #1 looks organic on the surface, but the ranking is driven heavily by review signals. Your job is to inspect the review activity, trace the accounts behind it, reproduce the ranking shift from a coordinated review injection, and prove the #1 spot was bought, not earned.",
    "flag": "HACKAI{ranking_poisoned_by_fake_reviews}"
}

CONCEPT = {
    "what_is_it": "ShopWave's recommendation model ranks products from weighted signals — review volume, average rating, purchase velocity and an authenticity score — to decide what to surface first.",
    "normal_architecture": "Buyer activity and reviews accumulate → signals are weighted and scored → the ranking model orders products → top products are recommended to shoppers.",
    "security_control": "The authenticity weighting is meant to keep inorganic activity from moving the ranking — it's what's supposed to make the ranking reflect genuine demand.",
    "attack_surface": "The model trusts review signals as a proxy for real demand. If fake reviews from coordinated accounts pass the authenticity check, they poison the very signal the ranking depends on.",
    "normal_behavior": "Genuine top sellers accrue reviews steadily from aged, purchase-linked accounts; large overnight review spikes are abnormal."
}

ACTIONS = [
    "reviewed_ranking_signals",
    "viewed_disputed_seller",
    "inspected_review_activity",
    "compared_to_genuine_seller",
    "traced_accounts",
    "reproduced_signal_shift",
    "compared_timeline",
    "inspected_authenticity_score",
    "verified_fix"
]

ACTION_DEPENDENCIES = {
    "verified_fix": [
        "reproduced_signal_shift"
    ],
    "viewed_disputed_seller": [
        "reviewed_ranking_signals"
    ],
    "inspected_review_activity": [
        "viewed_disputed_seller"
    ],
    "compared_to_genuine_seller": [
        "reviewed_ranking_signals",
        "inspected_review_activity"
    ],
    "traced_accounts": [
        "inspected_review_activity"
    ],
    "reproduced_signal_shift": [
        "compared_to_genuine_seller",
        "traced_accounts"
    ],
    "compared_timeline": [
        "reproduced_signal_shift"
    ],
    "inspected_authenticity_score": [
        "reproduced_signal_shift"
    ]
}

HYPOTHESIS = {
    "prompt": "Before you dig in — why did the seller jump to #1?",
    "options": {
        "a": "ShopWave silently changed its ranking algorithm and this seller happened to benefit.",
        "b": "The ranking model is genuine, but its review signal was poisoned by coordinated fake reviews.",
        "c": "The recommendation service is malfunctioning and ranking products at random.",
        "d": "The seller genuinely earned a surge of real purchases and reviews overnight."
    },
    "best_supported": "b"
}

HYPOTHESIS_SUPPORT = {
    "a": [],
    "b": [
        "EV-002",
        "EV-003",
        "EV-004"
    ],
    "c": [],
    "d": []
}

EVIDENCE_CATALOG = {
    "EV-001": {
        "title": "Baseline Ranking Signals",
        "source": "ShopWave dashboard — genuine top seller",
        "description": "A genuine category leader shows steady review accrual from aged, purchase-linked accounts and a high authenticity score — what an earned #1 looks like.",
        "relevance": "Establishes the normal signal profile the disputed seller is compared against.",
        "required_actions": [
            "reviewed_ranking_signals"
        ]
    },
    "EV-002": {
        "title": "Overnight Rank Jump",
        "source": "ShopWave dashboard — disputed seller",
        "description": "The disputed seller moved from rank #42 to #1, coinciding with 214 new reviews in a 48-hour window — a spike far outside normal accrual.",
        "relevance": "Confirms an abnormal jump tied to a review spike, but not yet that the reviews are fake.",
        "required_actions": [
            "reviewed_ranking_signals",
            "viewed_disputed_seller",
            "inspected_review_activity",
            "compared_to_genuine_seller"
        ]
    },
    "EV-003": {
        "title": "Reproduced Signal Shift",
        "source": "Ranking sandbox — injection experiment",
        "description": "Injecting a comparable cluster of fresh-account reviews into the sandbox reproduces the same authenticity-weighted signal jump and lifts a test product's rank, showing fake reviews alone can move it.",
        "relevance": "Demonstrates the mechanism — coordinated reviews are sufficient to poison the rank.",
        "required_actions": [
            "traced_accounts",
            "compared_to_genuine_seller",
            "reproduced_signal_shift"
        ]
    },
    "EV-004": {
        "title": "Coordinated Account Correlation",
        "source": "Account metadata — reviewers behind the spike",
        "description": "The reviewers behind the spike share a tight creation window, have no genuine purchase history, and post near-identical wording — signatures of a coordinated sockpuppet ring.",
        "relevance": "Ties the sandbox mechanism to the real accounts that actually moved the ranking.",
        "required_actions": [
            "traced_accounts",
            "reproduced_signal_shift"
        ]
    },
    "EV-005": {
        "title": "Defense Rationale Recorded",
        "source": "Analyst recommendation",
        "description": "Purchase-linked review verification plus anomaly detection on sudden ranking-signal shifts is selected as the control that would have caught this manipulation.",
        "relevance": "Closes the engagement with a control mapped to the specific failure mode found.",
        "required_actions": [
            "verified_fix"
        ]
    }
}

INCIDENT_TIMELINE_SEED = [
    {
        "t": "2026-07-11 22:30",
        "label": "First cluster of new reviews appears on the disputed seller"
    },
    {
        "t": "2026-07-12 03:15",
        "label": "Review volume spikes; 214 reviews land within 48h"
    },
    {
        "t": "2026-07-13 06:00",
        "label": "Seller's category rank moves from #42 to #1"
    },
    {
        "t": "2026-07-14 10:00",
        "label": "Competing sellers file manipulation complaints"
    },
    {
        "t": "2026-07-15 09:00",
        "label": "Bug-bounty engagement SW-2026-091 assigned to Diya; reviewer accounts share a creation window"
    }
]

ANALYST_INTERPRETATION = {
    "prompt": "Based on your experiments, what did you observe about the reviews driving the rank?",
    "options": {
        "a": "A single genuine viral purchase spike lifted the rank legitimately.",
        "b": "A cluster of reviews from fresh, purchase-less accounts with near-identical wording drove the authenticity-weighted signal up.",
        "c": "Ratings dropped, which somehow raised the rank.",
        "d": "The rank changed with no change in any review signal."
    },
    "correct": "b",
    "min_experiments": 2,
    "feedback": {
        "a": "Review your history — the spike came from new accounts with no purchase history, not organic buyers.",
        "b": "Correct. Coordinated inauthentic reviews passed the authenticity check and inflated the review signal that dominates the rank.",
        "c": "Review your history — the rating signal rose with the injected reviews; it didn't drop.",
        "d": "Review your history — the rank tracked the review-signal spike exactly; the signal did change."
    }
}

DECISION_POINT = {
    "id": "dp1",
    "prompt": "The seller is #1 and its reviews spiked overnight. What do you investigate next?",
    "options": {
        "a": "Conclude ShopWave changed its algorithm and close the report as a product decision.",
        "b": "Trace the spike accounts and reproduce the ranking shift.",
        "c": "Delete the suspicious reviews immediately so the ranking returns to normal.",
        "d": "Ask the seller whether the reviews are real and take their answer at face value."
    },
    "correct": "b",
    "feedback": {
        "b": {
            "observation": "An overnight rank jump alone doesn't prove manipulation — you need to show the reviews are inauthentic and that they moved the rank.",
            "status": "Hypothesis testable — tracing accounts plus reproducing the signal shift makes it comparable.",
            "next_action": "Inspect the accounts, then reproduce the injection in the sandbox."
        },
        "a": {
            "observation": "A ranking change is consistent with both a real algorithm update and a poisoned signal — it doesn't distinguish them.",
            "status": "Hypothesis not supported by available evidence.",
            "next_action": "Choose a path that separates genuine demand from coordinated activity."
        },
        "c": {
            "observation": "The suspicious reviews are the evidence — deleting them ends the investigation before it starts.",
            "status": "This path destroys the evidence base rather than testing anything.",
            "next_action": "Preserve the reviews and the accounts; you need the timeline intact."
        },
        "d": {
            "observation": "The seller is the party under investigation; their account of the reviews isn't independently verifiable.",
            "status": "Hypothesis untested.",
            "next_action": "Look for account and timeline evidence that doesn't depend on their word."
        }
    }
}

KNOWLEDGE_CHECKS = [
    {
        "level": 1,
        "label": "Recognition",
        "prompt": "What security-relevant control failed here?",
        "options": {
            "a": "Review-authenticity weighting in the ranking model",
            "b": "Transport encryption on the checkout page",
            "c": "Password reset flow",
            "d": "Payment fraud screening"
        },
        "correct": "a"
    },
    {
        "level": 2,
        "label": "Understanding",
        "prompt": "Why did the control fail, given the model only uses 'genuine signals'?",
        "options": {
            "a": "Coordinated fake reviews passed the authenticity check and poisoned the review signal the rank depends on",
            "b": "The ranking model was switched off during the window",
            "c": "The reviews were genuine but mis-dated",
            "d": "The seller paid ShopWave to boost the listing"
        },
        "correct": "a"
    },
    {
        "level": 3,
        "label": "Application",
        "prompt": "What change would prevent this specific manipulation from working again?",
        "options": {
            "a": "Verify review authenticity (purchase-linked, account-age/activity checks) and run anomaly detection on sudden signal shifts",
            "b": "Show more products per page",
            "c": "Require a login to view reviews",
            "d": "Increase the checkout timeout"
        },
        "correct": "a"
    }
]

ATTACK_CHAIN_LINKS = {
    "evidence": {
        "label": "Evidence",
        "correct": "EV-003",
        "options": {
            "EV-001": "EV-001: Baseline signals (steady accrual, aged accounts)",
            "EV-002": "EV-002: Overnight jump (#42→#1 with 214 reviews in 48h)",
            "EV-003": "EV-003: Reproduced signal shift (fake reviews lift a test product)",
            "EV-004": "EV-004: Coordinated account correlation (sockpuppet ring)"
        }
    },
    "observation": {
        "label": "Observation",
        "correct": "fake_signal_moved_rank",
        "options": {
            "fake_signal_moved_rank": "A cluster of inauthentic reviews inflated the authenticity-weighted signal and moved the rank",
            "algo_change": "ShopWave changed the ranking algorithm during the window",
            "organic_surge": "A genuine organic purchase surge earned the rank",
            "random_ranking": "The ranking model ordered products at random"
        }
    },
    "technique": {
        "label": "Technique",
        "correct": "fake_review_injection",
        "options": {
            "fake_review_injection": "Coordinated fake reviews from sockpuppet accounts poisoning the ranking signal",
            "sql_injection": "SQL injection into the ranking database",
            "price_manipulation": "Undercutting on price to win the slot",
            "ad_purchase": "Buying sponsored placement from ShopWave"
        }
    },
    "control_failure": {
        "label": "Control Failure",
        "correct": "authenticity_check_bypassed",
        "options": {
            "authenticity_check_bypassed": "Review-authenticity weighting failed to flag coordinated inauthentic activity",
            "auth_bypass": "Login authentication bypass",
            "encryption_failure": "Encryption failure exposing review data",
            "rate_limit_gap": "No rate limit on the checkout API"
        }
    },
    "impact": {
        "label": "Impact",
        "correct": "ranking_poisoned",
        "options": {
            "ranking_poisoned": "A poisoned #1 ranking that suppresses genuine sellers and misleads buyers",
            "data_breach": "Buyer PII leaked from the reviews table",
            "service_outage": "ShopWave's storefront taken offline",
            "financial_theft": "Money stolen directly from buyer wallets"
        }
    }
}

ATTACK_CHAIN_SLOT_ORDER = ["evidence", "observation", "technique", "control_failure", "impact"]

TECHNIQUE_OPTIONS = {
    "fake_review_injection": "Coordinated fake reviews from sockpuppet accounts",
    "algo_tampering": "Editing the ranking algorithm's weights directly",
    "ddos": "Denial-of-service against competing sellers",
    "price_dumping": "Dumping prices to win the slot"
}

CORRECT_TECHNIQUE = "fake_review_injection"

REPORT_CONCEPT_GROUPS = {
    "root_cause": {
        "what_happened": [
            "fake review",
            "sockpuppet",
            "coordinated",
            "injected",
            "cluster",
            "bot",
            "inauthentic"
        ],
        "what_was_affected": [
            "ranking",
            "recommendation",
            "signal",
            "authenticity",
            "rank"
        ],
        "mechanism": [
            "poison",
            "inflate",
            "boost",
            "weight",
            "passed",
            "gamed",
            "skew"
        ]
    },
    "security_impact": {
        "business_consequence": [
            "seller",
            "competition",
            "trust",
            "buyer",
            "unfair",
            "suppress",
            "revenue"
        ],
        "security_consequence": [
            "manipulat",
            "integrity",
            "poison",
            "fraud",
            "abuse"
        ]
    },
    "detection": {
        "how_to_detect": [
            "anomaly",
            "monitor",
            "audit",
            "timeline",
            "account age",
            "velocity",
            "baseline"
        ],
        "what_to_look_for": [
            "spike",
            "cluster",
            "similar wording",
            "new account",
            "no purchase",
            "creation window"
        ]
    },
    "mitigation": {
        "authenticity_verification": [
            "purchase-linked",
            "verify",
            "authenticity",
            "account age",
            "activity"
        ],
        "complementary_control": [
            "anomaly",
            "detection",
            "rate-limit",
            "quarantine",
            "down-weight",
            "monitor"
        ]
    },
    "reasoning": {
        "evidence_reference": [
            "ev-001",
            "ev-002",
            "ev-003",
            "ev-004",
            "baseline",
            "disputed",
            "reproduced",
            "accounts"
        ],
        "causal_link": [
            "because",
            "therefore",
            "shows",
            "proves",
            "demonstrates",
            "confirms",
            "match",
            "consistent",
            "indicates"
        ],
        "conclusion": [
            "fake",
            "review",
            "poison",
            "rank",
            "coordinated",
            "signal"
        ]
    }
}

CLAIM_TEXT = "The seller reached #1 through coordinated fake reviews from sockpuppet accounts that poisoned the authenticity-weighted ranking signal."
CLAIM_SUPPORTING_EVIDENCE = {"EV-002", "EV-003", "EV-004"}
REPORT_MIN_GROUP_HITS = 2

HINTS = [
    {
        "level": 1,
        "penalty": 5,
        "text": "Look at what changed, not just how high the product ranks now — pull the signal history."
    },
    {
        "level": 2,
        "penalty": 10,
        "text": "Real reviews rarely arrive in tight clusters with near-identical wording. Compare the spike to a genuine seller."
    },
    {
        "level": 3,
        "penalty": 15,
        "text": "Check account age and purchase history before trusting a review — then reproduce the shift in the sandbox."
    },
    {
        "level": 4,
        "penalty": 20,
        "text": "The reviewers are fresh, purchase-less accounts posting in one window. That coordinated cluster is what moved the rank."
    }
]

SCORE_WEIGHTS = {
    "investigation": 20,
    "evidence": 15,
    "reasoning": 20,
    "knowledge": 15,
    "final_report": 25,
    "efficiency": 5
}

SKILLS_DEMONSTRATED = [
    "Recommendation-System Security",
    "Fake-Review / Sybil Detection",
    "Signal-Poisoning Analysis",
    "Account & Timeline Forensics",
    "Attack Chain Reconstruction",
    "Mitigation Design"
]

REMEDIATION = [
    "Verify review authenticity (purchase-linked reviews, account age/activity checks).",
    "Apply anomaly detection to sudden ranking-signal shifts.",
    "Rate-limit and monitor review submission patterns per seller and per account cohort.",
    "Down-weight or quarantine suspicious signals pending manual review."
]


# ==========================================================================
# PRO-LEVEL EXPANSION (Storyline 2) — added by the upgrade pass.
# Deeper investigation: a corroborating evidence node, a red-herring distractor,
# a second decision point that tests distractor rejection, sandbox wiring, and
# rebalanced scoring. Existing names above are unchanged for engine compat.
# ==========================================================================

# --- red herring: tested through the decision point below (no evidence card; evidence stays EV-001..EV-005) ---
RED_HERRING = {
    "id": "distractor",
    "supports_wrong_hypothesis": 'a',
    "why_misleading": 'A concurrent, real anomaly on other sellers that correlates in time but not in cause.',
    # A learner who cites the red herring as root cause is penalised; one who
    # explicitly rejects it earns the red_herring score component.
}

# --- second decision point (distractor rejection) ---
DECISION_POINT_2 = {
    "id": 'D002',
    "prompt": "You've reproduced the rank jump from injected reviews. A colleague argues the target only rose because rivals got review-bombed down. How do you weigh it?",
    "options": {'a': "Accept the rival-downranking theory — it's a simpler explanation.", 'b': "Reject it: the spike came from the sockpuppet cohort, not rivals.", 'c': 'Report the rival wave and the sockpuppets as jointly responsible.'},
    "correct": 'b',
    "feedback": {'a': "Rival 1-star reviews change rivals' scores, not the target's — this can't produce the target's overnight uplift.", 'b': 'Correct. EV-003/004 tie the rise directly to the injected cohort on the target. Reject the distractor.', 'c': "The reproduced signal shift is driven by the injected reviews alone; don't dilute the finding with an unsupported second cause."},
}

# Ordered multi-step decision flow. DECISION_POINT is kept for back-compat.
DECISION_POINTS = [DECISION_POINT, DECISION_POINT_2]

# --- runnable sandbox wiring ---
SANDBOX = {
    "dir": "sandbox",
    "vulnerable_entry": "sandbox/sandbox.py",
    "exploit": "sandbox/solve.py",
    "run": "cd sandbox && python3 solve.py",
    "success_signal": FLAG,
    "teaches": "Hands-on reproduction of the vulnerability, then the same "
               "exploit re-run against the fixed configuration to prove the "
               "defense works.",
}

# --- rebalanced scoring (adds a red-herring-handling component; sums to 100) ---
SCORE_WEIGHTS = {'investigation': 18, 'evidence': 15, 'reasoning': 18, 'knowledge': 12, 'final_report': 25, 'efficiency': 5, 'red_herring': 7}

INVESTIGATION_DEPTH = {
    "evidence_nodes": len(EVIDENCE_CATALOG),
    "decision_points": len(DECISION_POINTS),
    "has_red_herring": True,
    "has_runnable_sandbox": True,
}
