# -*- coding: utf-8 -*-
"""Engine content for lab6 — "The Silent Scrape". Generated; keep in sync with README.md and scenario/*.json."""

FLAG = "HACKAI{rate_limit_bypass_scraped}"

DOCUMENTED_LIMIT_RPM = 60
SCRAPE_VOLUME_OBSERVED = 48000
ROTATED_KEY_COUNT = 800

CASE = {
    "client": "LexiGen AI",
    "incident_id": "LG-2026-207",
    "severity": "HIGH",
    "role": "AI Security Analyst",
    "date": "2026-07-08",
    "business_impact": "A competitor may have cloned LexiGen's paid model by harvesting its outputs; per-request revenue and the model's competitive moat are both at risk.",
    "initial_alert": "A competitor launched a near-identical text model weeks after a traffic surge on LexiGen's API. LexiGen suspects scraping but cannot show its rate limiter was bypassed.",
    "objective": "Determine whether LexiGen's model API was scraped at scale, and if so, which gap in the rate limiter allowed it.",
    "summary": "You are running a bug-bounty engagement against LexiGen AI's metered model API. Their published policy caps requests per API key, and they believe that alone prevents bulk harvesting of their model's outputs. A competitor's lookalike model suggests otherwise. Your job is to find the exact gap in the rate limiter, reproduce a scrape that collects far more input/output pairs than the policy should permit, and match your reproduced pattern to the suspect traffic.",
    "flag": "HACKAI{rate_limit_bypass_scraped}"
}

CONCEPT = {
    "what_is_it": "LexiGen exposes its model through a metered HTTP API. A rate limiter is supposed to cap how many requests any one customer can make in a time window, so nobody can cheaply harvest enough output to clone the model.",
    "normal_architecture": "Client sends API request → gateway checks rate limit → model generates text → response returned and the request is metered for billing.",
    "security_control": "The rate limiter is the control that makes bulk extraction uneconomical — it is supposed to bound total throughput per customer regardless of how requests are sent.",
    "attack_surface": "A rate limiter only protects what it actually counts. If it keys solely on the API key and ignores the source identity, an actor holding many keys can rotate through them and multiply their effective throughput.",
    "normal_behavior": "A single API key is throttled to 60 requests/min; the 61st request in a window returns HTTP 429."
}

ACTIONS = [
    "verified_baseline_limit",
    "viewed_suspect_logs",
    "tested_key_rotation",
    "tested_ip_rotation",
    "compared_identifiers",
    "reproduced_scrape",
    "compared_traffic_signature",
    "inspected_limiter_config",
    "verified_fix"
]

ACTION_DEPENDENCIES = {
    "verified_fix": [
        "reproduced_scrape"
    ],
    "viewed_suspect_logs": [
        "verified_baseline_limit"
    ],
    "tested_key_rotation": [
        "viewed_suspect_logs"
    ],
    "tested_ip_rotation": [
        "viewed_suspect_logs"
    ],
    "compared_identifiers": [
        "tested_key_rotation",
        "tested_ip_rotation"
    ],
    "reproduced_scrape": [
        "compared_identifiers"
    ],
    "compared_traffic_signature": [
        "reproduced_scrape"
    ],
    "inspected_limiter_config": [
        "reproduced_scrape"
    ]
}

HYPOTHESIS = {
    "prompt": "Before you dig in — how did a competitor most likely obtain LexiGen's behavior?",
    "options": {
        "a": "LexiGen's model weights were stolen from their servers in a breach.",
        "b": "The API was scraped at scale by an actor who bypassed the per-key rate limit.",
        "c": "The rate limiter software crashed and stopped enforcing anything.",
        "d": "The competitor independently trained an identical model by coincidence."
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
        "title": "Baseline Rate-Limit Enforcement",
        "source": "LexiGen sandbox — single-key test",
        "description": "A single API key is throttled at 60 requests/min; the 61st request in the window returns HTTP 429, confirming the documented per-key limit works.",
        "relevance": "Establishes the throughput ceiling the suspect traffic is being measured against.",
        "required_actions": [
            "verified_baseline_limit"
        ]
    },
    "EV-002": {
        "title": "Anomalous Harvest Volume",
        "source": "Suspect-period traffic logs",
        "description": "Logs from the suspected window show ~48000 successful requests from one source subnet — impossible under a 60/min per-key limit unless the limiter ignores the source.",
        "relevance": "Confirms bulk harvesting occurred, but not yet by what mechanism.",
        "required_actions": [
            "verified_baseline_limit",
            "viewed_suspect_logs",
            "compared_identifiers"
        ]
    },
    "EV-003": {
        "title": "Reproduced Scrape",
        "source": "Extraction sandbox — key-rotation experiment",
        "description": "Rotating ~800 API keys from a single machine sustains a capture rate far above the per-key ceiling, reproducing bulk collection of input/output pairs while each individual key stays under 60/min.",
        "relevance": "Shows the specific bypass — key rotation against a limiter blind to source — is capable of the observed volume.",
        "required_actions": [
            "tested_key_rotation",
            "tested_ip_rotation",
            "compared_identifiers",
            "reproduced_scrape"
        ]
    },
    "EV-004": {
        "title": "Traffic Signature Correlation",
        "source": "Suspect logs vs. reproduced scrape",
        "description": "The suspect traffic's round-robin key cadence and timing intervals match the reproduced scrape's signature, tying the real logs to the reproduced technique.",
        "relevance": "Turns a lab reproduction into an evidentiary link against the actual suspect traffic.",
        "required_actions": [
            "compared_traffic_signature",
            "reproduced_scrape"
        ]
    },
    "EV-005": {
        "title": "Defense Rationale Recorded",
        "source": "Analyst recommendation",
        "description": "Multi-dimensional rate limiting (key + source + behavioral fingerprint) paired with volume/timing anomaly detection is selected as the control that would have bounded this scrape.",
        "relevance": "Closes the engagement with a control mapped to the exact blind spot found.",
        "required_actions": [
            "verified_fix"
        ]
    }
}

INCIDENT_TIMELINE_SEED = [
    {
        "t": "2026-06-30 02:10",
        "label": "Traffic surge begins on LexiGen's metered API"
    },
    {
        "t": "2026-07-03 00:00",
        "label": "Surge sustained for ~72h at volumes far above any single customer's plan"
    },
    {
        "t": "2026-07-05 11:40",
        "label": "Competitor announces a near-identical text model"
    },
    {
        "t": "2026-07-08 09:00",
        "label": "Bug-bounty engagement LG-2026-207 assigned to Diya"
    },
    {
        "t": "2026-07-08 09:20",
        "label": "Diya notes the surge came from ~800 distinct free-tier keys on one subnet"
    }
]

ANALYST_INTERPRETATION = {
    "prompt": "Based on your experiments, what did you observe about how the rate limiter responds to rotating identifiers?",
    "options": {
        "a": "Rotating the source IP with one key removed the throttle entirely.",
        "b": "Rotating API keys from a single source multiplied effective throughput because the limiter never counted the source.",
        "c": "Neither rotation changed anything; the limiter blocked everything equally.",
        "d": "The limiter failed at random regardless of what was rotated."
    },
    "correct": "b",
    "min_experiments": 2,
    "feedback": {
        "a": "Review your history — rotating IP alone with the same key still hit the per-key 429; the key is what's counted.",
        "b": "Correct. The limiter keys only on the API key, so N keys from one machine yield roughly N× the intended throughput.",
        "c": "Review your history — requests under the per-key limit succeeded normally; the limiter is not blocking everything.",
        "d": "Review your history — identical rotation patterns produced identical results; the limiter is deterministic, not random."
    }
}

DECISION_POINT = {
    "id": "dp1",
    "prompt": "The suspect logs show far more successful requests than one key should allow. What do you investigate next?",
    "options": {
        "a": "Conclude the model weights were stolen in a server breach and open an incident.",
        "b": "Rotate identifiers in the sandbox to find which one the limiter ignores.",
        "c": "Purge the suspect traffic logs and close the bounty as unprovable.",
        "d": "Email the competitor and accept their statement that they trained their own model."
    },
    "correct": "b",
    "feedback": {
        "b": {
            "observation": "High request volume alone doesn't say how the limit was beaten — you have to find which identifier it ignores.",
            "status": "Hypothesis testable — controlled rotation against a known baseline isolates the blind spot.",
            "next_action": "Go to the sandbox and rotate keys and IPs separately, then reproduce the scrape."
        },
        "a": {
            "observation": "Nothing in the traffic distinguishes 'weights stolen' from 'outputs harvested via the API' — both leave the model looking cloned.",
            "status": "Hypothesis not supported by available evidence.",
            "next_action": "Pick a path that can actually distinguish extraction-by-API from a breach before concluding."
        },
        "c": {
            "observation": "The traffic logs are the only record that could tie the competitor's pattern to a scrape.",
            "status": "This path destroys the evidence base rather than testing anything.",
            "next_action": "Keep the logs — the signature match is the whole case."
        },
        "d": {
            "observation": "A statement from the party under investigation isn't independently verifiable.",
            "status": "Hypothesis untested.",
            "next_action": "Find a technical path that doesn't rely on taking their word for it."
        }
    }
}

KNOWLEDGE_CHECKS = [
    {
        "level": 1,
        "label": "Recognition",
        "prompt": "What security control failed here?",
        "options": {
            "a": "API rate limiting",
            "b": "Password hashing",
            "c": "TLS certificate validation",
            "d": "Database backups"
        },
        "correct": "a"
    },
    {
        "level": 2,
        "label": "Understanding",
        "prompt": "Why did the control fail, even though the per-key limit itself worked?",
        "options": {
            "a": "The limiter counted only the API key and ignored the source, so rotating many keys multiplied throughput",
            "b": "The limiter was disabled entirely during the window",
            "c": "The model returned errors that weren't counted",
            "d": "The attacker had admin access to the gateway"
        },
        "correct": "a"
    },
    {
        "level": 3,
        "label": "Application",
        "prompt": "What change would stop this specific attack from working again?",
        "options": {
            "a": "Rate-limit across multiple identifiers at once (key + source + behavioral fingerprint) and add volume/timing anomaly detection",
            "b": "Increase the per-key limit so keys aren't needed",
            "c": "Require a CAPTCHA on the public marketing site",
            "d": "Rotate the TLS certificate more often"
        },
        "correct": "a"
    }
]

ATTACK_CHAIN_LINKS = {
    "evidence": {
        "label": "Evidence",
        "correct": "EV-003",
        "options": {
            "EV-001": "EV-001: Baseline enforcement (60/min per key, 429 on the 61st)",
            "EV-002": "EV-002: Anomalous harvest volume (~48000 requests from one subnet)",
            "EV-003": "EV-003: Reproduced scrape (key rotation beats the per-key ceiling)",
            "EV-004": "EV-004: Traffic signature correlation (cadence matches suspect logs)"
        }
    },
    "observation": {
        "label": "Observation",
        "correct": "source_not_counted",
        "options": {
            "source_not_counted": "Rotating keys from one source multiplied throughput because the limiter never counted the source",
            "limiter_offline": "The rate limiter was completely offline during the window",
            "single_key_enough": "A single key alone could pull the full 48000 requests",
            "random_throttle": "The limiter throttled requests at random"
        }
    },
    "technique": {
        "label": "Technique",
        "correct": "credential_rotation",
        "options": {
            "credential_rotation": "API-key rotation from one source against a limiter blind to origin",
            "weight_theft": "Direct theft of model weights from LexiGen's servers",
            "prompt_injection": "Prompt injection to make the model dump training data",
            "tls_downgrade": "Downgrading TLS to intercept responses in transit"
        }
    },
    "control_failure": {
        "label": "Control Failure",
        "correct": "rate_limit_blind_spot",
        "options": {
            "rate_limit_blind_spot": "Rate limiting keyed only on the API key, leaving the source uncounted",
            "auth_bypass": "Authentication bypass — requests made with no credentials",
            "encryption_failure": "Encryption broken, exposing the model in transit",
            "access_control_gap": "Broken access control on an admin endpoint"
        }
    },
    "impact": {
        "label": "Impact",
        "correct": "model_extraction",
        "options": {
            "model_extraction": "Bulk input/output harvesting enabling a cloned competitor model; lost revenue and moat",
            "data_breach": "Customer PII leaked from LexiGen's database",
            "service_outage": "LexiGen's API taken offline for all users",
            "financial_theft": "Money stolen directly from LexiGen's accounts"
        }
    }
}

ATTACK_CHAIN_SLOT_ORDER = ["evidence", "observation", "technique", "control_failure", "impact"]

TECHNIQUE_OPTIONS = {
    "credential_rotation": "Rotating many API keys from a single source to beat a per-key limit",
    "weight_theft": "Model weights or training data stolen from servers",
    "single_key_bruteforce": "Hammering the API with one key until it breaks",
    "config_edit": "Editing the rate-limiter config directly"
}

CORRECT_TECHNIQUE = "credential_rotation"

REPORT_CONCEPT_GROUPS = {
    "root_cause": {
        "what_happened": [
            "rotat",
            "key rotation",
            "multiple keys",
            "many keys",
            "distributed",
            "scrape",
            "harvest"
        ],
        "what_was_affected": [
            "rate limit",
            "limiter",
            "throttle",
            "api",
            "throughput",
            "quota"
        ],
        "mechanism": [
            "ignore",
            "blind",
            "source",
            "only counted",
            "per-key",
            "not tracked",
            "bypass"
        ]
    },
    "security_impact": {
        "business_consequence": [
            "revenue",
            "clone",
            "knockoff",
            "competitor",
            "moat",
            "resale",
            "cost"
        ],
        "security_consequence": [
            "extraction",
            "scrape",
            "harvest",
            "exfil",
            "intellectual property",
            "model theft"
        ]
    },
    "detection": {
        "how_to_detect": [
            "anomaly",
            "monitor",
            "audit",
            "volume",
            "timing",
            "signature",
            "baseline",
            "pattern"
        ],
        "what_to_look_for": [
            "surge",
            "rotation",
            "cadence",
            "subnet",
            "spike",
            "high-volume",
            "distinct keys"
        ]
    },
    "mitigation": {
        "layered_rate_limit": [
            "multi",
            "layered",
            "fingerprint",
            "source",
            "ip",
            "behavioral",
            "device"
        ],
        "complementary_control": [
            "anomaly",
            "detection",
            "watermark",
            "throttle",
            "alert",
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
            "suspect",
            "reproduced",
            "signature"
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
            "rotation",
            "key",
            "source",
            "limiter",
            "scrape",
            "bypass"
        ]
    }
}

CLAIM_TEXT = "The API was scraped at scale by rotating API keys from a single source, exploiting a rate limiter that never counted request origin."
CLAIM_SUPPORTING_EVIDENCE = {"EV-002", "EV-003", "EV-004"}
REPORT_MIN_GROUP_HITS = 2

HINTS = [
    {
        "level": 1,
        "penalty": 5,
        "text": "Start by confirming what normal enforcement looks like — push one key to its limit and watch for the 429."
    },
    {
        "level": 2,
        "penalty": 10,
        "text": "Change only the key, then only the IP. Whichever change slips past the throttle points at what the limiter isn't counting."
    },
    {
        "level": 3,
        "penalty": 15,
        "text": "A limiter that tracks one identifier can be walked around using the other. Which one does the config actually track?"
    },
    {
        "level": 4,
        "penalty": 20,
        "text": "The limiter keys on the API key alone. Rotate many keys from one machine and each stays under 60/min while your total soars."
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
    "AI API Security",
    "Rate-Limit Bypass Analysis",
    "Model Extraction / Scraping",
    "Traffic Forensics",
    "Attack Chain Reconstruction",
    "Mitigation Design"
]

REMEDIATION = [
    "Rate-limit on multiple identifiers simultaneously (API key, source/IP, device fingerprint, behavior).",
    "Apply anomaly detection for unusual request volume or timing patterns, even within nominal per-key limits.",
    "Watermark or throttle outputs to reduce the training value of any scraped data.",
    "Monitor and alert on sustained high-volume usage and mass key registration from one source."
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
    "why_misleading": 'A real, scary vulnerability that is genuinely present but was never used in this incident.',
    # A learner who cites the red herring as root cause is penalised; one who
    # explicitly rejects it earns the red_herring score component.
}

# --- second decision point (distractor rejection) ---
DECISION_POINT_2 = {
    "id": 'D002',
    "prompt": "Your scrape reproduction worked. A teammate points at the gateway's unpatched RCE CVE as the more likely entry point. How do you weigh it?",
    "options": {'a': 'Pivot the whole case to the CVE — an RCE outranks a rate-limit gap.', 'b': 'Note the CVE as unrelated: no exploit traffic hit it.', 'c': 'Report both the CVE and the rate-limit gap as equally likely causes.'},
    "correct": 'b',
    "feedback": {'a': 'The CVE is real but unused here — chasing it would misattribute the root cause and leave the actual gap open.', 'b': 'Correct. Evidence (EV-002/003/004) all points to key rotation; the CVE has no supporting traffic. Reject the distractor.', 'c': 'A report must commit to the supported cause; the traffic evidence clearly favours key rotation over the unused CVE.'},
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
