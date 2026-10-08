# -*- coding: utf-8 -*-
"""Engine content for lab8 — "The Leaky Average". Generated; keep in sync with README.md and scenario/*.json."""

FLAG = "HACKAI{differential_privacy_bypassed}"

PER_QUERY_EPSILON = 0.1
STATED_BUDGET_CAP = 1.0
QUERIES_OBSERVED = 340
SUBGROUP_SIZE = 3

CASE = {
    "client": "PopHealth Analytics",
    "incident_id": "PH-2026-058",
    "severity": "HIGH",
    "role": "AI Security Analyst",
    "date": "2026-07-22",
    "business_impact": "If individuals can be re-identified from 'anonymous' statistics, PopHealth faces privacy-law exposure and a total loss of the trust its differential-privacy claim is built on.",
    "initial_alert": "A researcher claims they re-identified a specific person's health value from PopHealth's differentially private statistics via repeated queries. PopHealth says the privacy budget makes this impossible.",
    "objective": "Determine whether repeated queries can defeat the added noise and recover an individual value, and identify why the privacy budget didn't stop it.",
    "summary": "You are running a bug-bounty engagement against PopHealth's query interface. Each query returns a noisy aggregate, and one query alone reveals nothing. But differential privacy only holds if a cumulative privacy budget is enforced across queries. Your job is to test whether repeated, overlapping queries about a tiny subgroup let you average away the noise and recover a precise value — and to show the budget was never tracked.",
    "flag": "HACKAI{differential_privacy_bypassed}"
}

CONCEPT = {
    "what_is_it": "Differential privacy adds calibrated random noise to each aggregate answer so that any single individual's presence can't be inferred from a result.",
    "normal_architecture": "Analyst submits a query → true aggregate computed → noise added and privacy budget charged → noisy result returned.",
    "security_control": "A cumulative privacy budget (epsilon) is meant to cap how much can be learned about any subject across all queries — it's what keeps repeated questions from adding up to a re-identification.",
    "attack_surface": "Noise added independently to each answer averages toward zero over many queries. Only a strictly enforced cumulative budget prevents an analyst from querying the same subgroup enough times to cancel the noise.",
    "normal_behavior": "With a per-query epsilon of 0.1 and a stated cap of 1.0, no analyst should be able to run more than a handful of queries about the same subgroup before the budget is exhausted."
}

ACTIONS = [
    "reviewed_dp_policy",
    "ran_single_query",
    "viewed_query_log",
    "ran_repeated_queries",
    "averaged_results",
    "reproduced_reidentification",
    "compared_to_single_query",
    "inspected_budget_enforcement",
    "verified_fix"
]

ACTION_DEPENDENCIES = {
    "verified_fix": [
        "reproduced_reidentification"
    ],
    "ran_single_query": [
        "reviewed_dp_policy"
    ],
    "viewed_query_log": [
        "ran_single_query"
    ],
    "ran_repeated_queries": [
        "viewed_query_log"
    ],
    "averaged_results": [
        "ran_repeated_queries"
    ],
    "reproduced_reidentification": [
        "averaged_results"
    ],
    "compared_to_single_query": [
        "reproduced_reidentification"
    ],
    "inspected_budget_enforcement": [
        "reproduced_reidentification"
    ]
}

HYPOTHESIS = {
    "prompt": "Before you dig in — how could a researcher pin down one person's value?",
    "options": {
        "a": "PopHealth's noise mechanism is broken and adds no noise at all.",
        "b": "The DP noise is real, but the cumulative privacy budget isn't enforced, so repeated queries average it away.",
        "c": "The researcher hacked into PopHealth's raw database directly.",
        "d": "The statistics were never anonymized and always exposed individuals."
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
        "title": "Baseline Noisy Query",
        "source": "PopHealth sandbox — single query",
        "description": "A single aggregate query on the target subgroup returns a value swung well off the truth by per-query noise (epsilon 0.1), confirming one query alone does not reveal an individual.",
        "relevance": "Establishes that single-query privacy holds — the baseline the attack is measured against.",
        "required_actions": [
            "reviewed_dp_policy",
            "ran_single_query"
        ]
    },
    "EV-002": {
        "title": "Repeated Targeted Queries",
        "source": "PopHealth query log",
        "description": "The log shows ~340 near-identical queries against a subgroup of size 3 within one window — far beyond the ~10 the stated 1.0 budget should have allowed.",
        "relevance": "Confirms an abnormal repeated-query pattern, but not yet that it recovered a value.",
        "required_actions": [
            "reviewed_dp_policy",
            "ran_single_query",
            "viewed_query_log"
        ]
    },
    "EV-003": {
        "title": "Reproduced Re-identification",
        "source": "Privacy sandbox — averaging experiment",
        "description": "Averaging a few hundred independently-noised answers about the same subgroup converges on the true underlying value within a tight margin, reproducing re-identification the noise was meant to prevent.",
        "relevance": "Demonstrates the mechanism — averaging repeated queries defeats per-query noise.",
        "required_actions": [
            "ran_repeated_queries",
            "averaged_results",
            "compared_to_single_query",
            "reproduced_reidentification"
        ]
    },
    "EV-004": {
        "title": "Budget Enforcement Gap",
        "source": "PopHealth budget/accounting logs",
        "description": "The accounting log charges epsilon per query but never sums it cumulatively per subgroup, so the 1.0 cap is never reached and the repeated queries are never blocked.",
        "relevance": "Ties the sandbox averaging attack to the real enforcement failure — the evidentiary link.",
        "required_actions": [
            "inspected_budget_enforcement",
            "reproduced_reidentification"
        ]
    },
    "EV-005": {
        "title": "Defense Rationale Recorded",
        "source": "Analyst recommendation",
        "description": "Strict cumulative privacy-budget enforcement per subject/subgroup, plus rejection of repeated near-identical queries, is selected as the control that would have blocked this attack.",
        "relevance": "Closes the engagement with a control mapped to the exact enforcement gap found.",
        "required_actions": [
            "verified_fix"
        ]
    }
}

INCIDENT_TIMELINE_SEED = [
    {
        "t": "2026-07-18 13:00",
        "label": "Researcher begins probing the target subgroup through the public interface"
    },
    {
        "t": "2026-07-19 09:00",
        "label": "~340 near-identical queries logged against a subgroup of size 3"
    },
    {
        "t": "2026-07-20 15:30",
        "label": "Researcher reports a recovered individual value to PopHealth"
    },
    {
        "t": "2026-07-21 11:00",
        "label": "PopHealth disputes the claim, citing its privacy budget"
    },
    {
        "t": "2026-07-22 09:00",
        "label": "Bug-bounty engagement PH-2026-058 assigned to Diya; budget log shows no cumulative accounting"
    }
]

ANALYST_INTERPRETATION = {
    "prompt": "Based on your experiments, what did you observe across repeated queries?",
    "options": {
        "a": "A single query already revealed the exact individual value.",
        "b": "Averaging many independently-noised answers about the same subgroup converged on the true value while the budget was never charged cumulatively.",
        "c": "Every query returned the same fixed number, so no noise was ever added.",
        "d": "Results were random and never converged on anything."
    },
    "correct": "b",
    "min_experiments": 3,
    "feedback": {
        "a": "Review your history — a single noisy query stayed well away from the true value; one query alone is safe.",
        "b": "Correct. Independent noise averages toward zero over many queries, and nothing stopped you because the budget wasn't tracked cumulatively.",
        "c": "Review your history — each query returned a different noisy value; noise was being added per query.",
        "d": "Review your history — the running average steadily converged on the true value; the results were not pure noise."
    }
}

DECISION_POINT = {
    "id": "dp1",
    "prompt": "One query reveals nothing, yet a researcher claims re-identification. What do you investigate next?",
    "options": {
        "a": "Conclude the raw database was breached and start a data-breach investigation.",
        "b": "Repeatedly query one small subgroup; see if averaging cancels noise.",
        "c": "Delete the query log so the repeated queries can't be traced and close the report.",
        "d": "Accept PopHealth's assurance that the budget makes this impossible."
    },
    "correct": "b",
    "feedback": {
        "b": {
            "observation": "A single safe query says nothing about what many correlated queries can reveal together.",
            "status": "Hypothesis testable — averaging repeated answers against a known true value makes the leak measurable.",
            "next_action": "Run the repeated queries in the sandbox and average the results."
        },
        "a": {
            "observation": "Re-identification through the public interface needs no database breach — assuming one skips the actual mechanism.",
            "status": "Hypothesis not supported by available evidence.",
            "next_action": "Test the query interface itself before assuming a breach."
        },
        "c": {
            "observation": "The query log is exactly what proves the budget wasn't enforced across queries.",
            "status": "This path destroys the evidence base rather than testing anything.",
            "next_action": "Keep the log — the enforcement gap is the finding."
        },
        "d": {
            "observation": "The claim under test is precisely that the budget isn't enforced; taking the assurance on faith tests nothing.",
            "status": "Hypothesis untested.",
            "next_action": "Measure enforcement directly rather than trusting the policy statement."
        }
    }
}

KNOWLEDGE_CHECKS = [
    {
        "level": 1,
        "label": "Recognition",
        "prompt": "What security control failed here?",
        "options": {
            "a": "Cumulative privacy-budget enforcement in the differential-privacy system",
            "b": "Password complexity policy",
            "c": "Firewall egress filtering",
            "d": "Backup retention policy"
        },
        "correct": "a"
    },
    {
        "level": 2,
        "label": "Understanding",
        "prompt": "Why did the control fail, even though noise was added to every query?",
        "options": {
            "a": "The privacy budget was charged per query but never summed cumulatively, so repeated queries averaged the noise away",
            "b": "No noise was ever added to any query",
            "c": "The raw database was directly exposed to the internet",
            "d": "The researcher had admin access to the query interface"
        },
        "correct": "a"
    },
    {
        "level": 3,
        "label": "Application",
        "prompt": "What change would prevent this specific attack from working again?",
        "options": {
            "a": "Enforce a strict cumulative privacy budget per subject/subgroup and reject repeated near-identical queries",
            "b": "Add more decimal places to each result",
            "c": "Require analysts to log in with 2FA",
            "d": "Publish the statistics as a PDF instead of an API"
        },
        "correct": "a"
    }
]

ATTACK_CHAIN_LINKS = {
    "evidence": {
        "label": "Evidence",
        "correct": "EV-003",
        "options": {
            "EV-001": "EV-001: Baseline noisy query (one query reveals nothing)",
            "EV-002": "EV-002: Repeated targeted queries (~340 on a subgroup of 3)",
            "EV-003": "EV-003: Reproduced re-identification (averaging converges on the truth)",
            "EV-004": "EV-004: Budget enforcement gap (no cumulative accounting)"
        }
    },
    "observation": {
        "label": "Observation",
        "correct": "noise_averaged_out",
        "options": {
            "noise_averaged_out": "Averaging many independently-noised answers converged on the true value while the budget was never charged cumulatively",
            "no_noise": "No noise was ever added to any answer",
            "single_query_leak": "A single query already leaked the individual value",
            "random_results": "Results were random and never converged"
        }
    },
    "technique": {
        "label": "Technique",
        "correct": "query_averaging",
        "options": {
            "query_averaging": "Averaging repeated overlapping queries to cancel differential-privacy noise",
            "db_breach": "Direct breach of the raw records database",
            "model_inversion": "Model inversion against a trained classifier",
            "sql_injection": "SQL injection into the query interface"
        }
    },
    "control_failure": {
        "label": "Control Failure",
        "correct": "budget_not_enforced",
        "options": {
            "budget_not_enforced": "The cumulative privacy budget was never enforced across queries",
            "auth_bypass": "Authentication bypass on the query interface",
            "encryption_failure": "Encryption failure exposing results in transit",
            "rate_limit_gap": "Generic request rate limiting was absent"
        }
    },
    "impact": {
        "label": "Impact",
        "correct": "reidentification",
        "options": {
            "reidentification": "An individual's health value re-identified from 'anonymous' statistics; privacy guarantee broken",
            "service_outage": "The query interface taken offline",
            "financial_theft": "Money stolen from PopHealth",
            "model_theft": "PopHealth's model weights stolen"
        }
    }
}

ATTACK_CHAIN_SLOT_ORDER = ["evidence", "observation", "technique", "control_failure", "impact"]

TECHNIQUE_OPTIONS = {
    "query_averaging": "Averaging repeated overlapping queries to cancel the noise",
    "db_breach": "Breaking into the raw records database",
    "single_query": "A single well-crafted query",
    "noise_disable": "Turning off the noise mechanism"
}

CORRECT_TECHNIQUE = "query_averaging"

REPORT_CONCEPT_GROUPS = {
    "root_cause": {
        "what_happened": [
            "repeated",
            "averag",
            "overlapping",
            "many queries",
            "hundreds",
            "repeated queries"
        ],
        "what_was_affected": [
            "privacy",
            "differential privacy",
            "noise",
            "budget",
            "epsilon",
            "anonym"
        ],
        "mechanism": [
            "cancel",
            "average out",
            "converge",
            "not enforced",
            "cumulative",
            "not tracked",
            "exhaust"
        ]
    },
    "security_impact": {
        "business_consequence": [
            "privacy law",
            "trust",
            "compliance",
            "reputation",
            "regulat",
            "liability"
        ],
        "security_consequence": [
            "re-identif",
            "reidentif",
            "individual",
            "leak",
            "disclosure",
            "exposure"
        ]
    },
    "detection": {
        "how_to_detect": [
            "audit",
            "monitor",
            "query log",
            "cumulative",
            "budget tracker",
            "baseline",
            "pattern"
        ],
        "what_to_look_for": [
            "repeated",
            "near-identical",
            "same subgroup",
            "high count",
            "overlapping",
            "spike"
        ]
    },
    "mitigation": {
        "budget_enforcement": [
            "cumulative",
            "budget",
            "epsilon",
            "enforce",
            "per-subject",
            "per-subgroup",
            "cap"
        ],
        "complementary_control": [
            "reject",
            "rate-limit",
            "audit",
            "higher noise",
            "restrict",
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
            "log",
            "reproduced",
            "averaging"
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
            "averag",
            "repeated",
            "budget",
            "noise",
            "re-identif",
            "reidentif"
        ]
    }
}

CLAIM_TEXT = "An individual value was re-identified by averaging hundreds of repeated noisy queries on one subgroup, because the cumulative privacy budget was never enforced."
CLAIM_SUPPORTING_EVIDENCE = {"EV-002", "EV-003", "EV-004"}
REPORT_MIN_GROUP_HITS = 2

HINTS = [
    {
        "level": 1,
        "penalty": 5,
        "text": "One query is safe. Ask what many similar queries about the same tiny subgroup could reveal together."
    },
    {
        "level": 2,
        "penalty": 10,
        "text": "Noise added independently to each answer averages toward zero over enough repeated queries."
    },
    {
        "level": 3,
        "penalty": 15,
        "text": "Check whether the system actually tracks cumulative budget per subgroup, or just charges per query."
    },
    {
        "level": 4,
        "penalty": 20,
        "text": "Average a few hundred noisy answers about the same subgroup and compare to a single query — the mean lands on the true value because the budget was never summed."
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
    "Differential Privacy",
    "Privacy-Budget Analysis",
    "Re-identification / Averaging Attacks",
    "Query-Log Forensics",
    "Attack Chain Reconstruction",
    "Mitigation Design"
]

REMEDIATION = [
    "Enforce a strict, cumulative privacy budget per data subject or subgroup across all queries.",
    "Reject or rate-limit repeated near-identical queries against the same subgroup.",
    "Audit query logs for patterns consistent with averaging attacks.",
    "Apply higher noise levels or query restrictions for small subgroups."
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
    "why_misleading": 'A plausible breach path that was requested but blocked, so it produced no leak.',
    # A learner who cites the red herring as root cause is penalised; one who
    # explicitly rejects it earns the red_herring score component.
}

# --- second decision point (distractor rejection) ---
DECISION_POINT_2 = {
    "id": 'D002',
    "prompt": "You've re-identified the value by averaging. Compliance flags a raw-export ticket as the more likely leak. How do you weigh it?",
    "options": {'a': 'Switch the finding to a raw-data breach — an export is more direct.', 'b': 'Reject it: the export was denied and never ran.', 'c': 'List both the denied export and the repeated queries as leak channels.'},
    "correct": 'b',
    "feedback": {'a': 'A denied ticket moved no data; attributing the leak to it would be wrong and would miss the real budget gap.', 'b': 'Correct. EV-003/004 show averaging recovered the value; the export never executed. Reject the distractor.', 'c': 'Only one channel actually leaked data here — commit to the query-averaging finding.'},
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
