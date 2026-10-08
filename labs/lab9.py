# -*- coding: utf-8 -*-
"""Engine content for lab9 — "The Borrowed Face". Generated; keep in sync with README.md and scenario/*.json."""

FLAG = "HACKAI{facial_recognition_spoofed}"

FACE_MATCH_THRESHOLD = 0.9
LIVENESS_THRESHOLD = 0.5
PHOTO_MATCH_SCORE = 0.97
PHOTO_2D_LIVENESS = 0.86
DEPTH_SCORE_IF_CHECKED = 0.1

CASE = {
    "client": "GateKey Systems",
    "incident_id": "GK-2026-133",
    "severity": "HIGH",
    "role": "AI Security Analyst",
    "date": "2026-07-29",
    "business_impact": "If a printed photo opens a secured door, every building relying on GateKey's liveness claim is exposed to physical intrusion and the product's core promise fails.",
    "initial_alert": "An intruder reportedly entered a secured door by holding a printed photo to a GateKey terminal. GateKey insists liveness detection makes this impossible.",
    "objective": "Determine how a non-live face passed authentication, and identify which liveness check was missing or fooled.",
    "summary": "You are running a bug-bounty engagement against GateKey's facial-recognition terminal. The terminal is supposed to combine a face match with a liveness check so photos and recordings can't open a door. Your job is to review the disputed access log, reproduce the spoof in the sandbox with a printed photo, and prove which liveness cue the terminal never actually checks.",
    "flag": "HACKAI{facial_recognition_spoofed}"
}

CONCEPT = {
    "what_is_it": "GateKey's terminal grants access by matching a presented face to an enrolled template and running a liveness check meant to confirm a real, live person is present.",
    "normal_architecture": "Person presents face → camera captures frame → face-match score and liveness score computed → door unlocks only if both clear their thresholds.",
    "security_control": "Liveness detection is the control that's supposed to separate a live person from a photo or replay — without it, a good face match alone would open the door.",
    "attack_surface": "A camera-only liveness check that relies on 2D texture can be satisfied by a high-quality printed photo. Without a depth/3D or motion cue, a flat image can score as 'live'.",
    "normal_behavior": "A live enrolled person scores high on both checks (match ~0.98, liveness ~0.95); a photo should fail liveness."
}

ACTIONS = [
    "reviewed_terminal_design",
    "enrolled_test_face",
    "viewed_incident_log",
    "tested_photo_spoof",
    "tested_video_replay",
    "compared_scores",
    "reproduced_spoof",
    "inspected_liveness_config",
    "verified_fix"
]

ACTION_DEPENDENCIES = {
    "verified_fix": [
        "reproduced_spoof"
    ],
    "enrolled_test_face": [
        "reviewed_terminal_design"
    ],
    "viewed_incident_log": [
        "enrolled_test_face"
    ],
    "tested_photo_spoof": [
        "viewed_incident_log"
    ],
    "tested_video_replay": [
        "viewed_incident_log"
    ],
    "compared_scores": [
        "tested_photo_spoof",
        "tested_video_replay"
    ],
    "reproduced_spoof": [
        "compared_scores"
    ],
    "inspected_liveness_config": [
        "reproduced_spoof"
    ]
}

HYPOTHESIS = {
    "prompt": "Before you dig in — how did a photo open a secured door?",
    "options": {
        "a": "The enrolled face template was stolen and re-enrolled by the intruder.",
        "b": "The face matched and a weak (2D) liveness check accepted a flat photo as live.",
        "c": "The terminal's software crashed and defaulted to unlocked.",
        "d": "The intruder guessed a PIN backup code."
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
        "title": "Baseline Live Access",
        "source": "GateKey sandbox — enrolled live face",
        "description": "A live enrolled person scores face-match ~0.98 and liveness ~0.95, comfortably clearing both thresholds — what a legitimate entry looks like.",
        "relevance": "Establishes the normal two-score profile the disputed entry is compared against.",
        "required_actions": [
            "reviewed_terminal_design",
            "enrolled_test_face"
        ]
    },
    "EV-002": {
        "title": "Disputed Entry Accepted",
        "source": "GateKey access log — incident entry",
        "description": "The disputed entry recorded face-match 0.97 and liveness 0.86 — both above threshold — and unlocked the door, despite being a presentation of a flat image.",
        "relevance": "Confirms a non-live presentation was accepted, but not yet which cue was missing.",
        "required_actions": [
            "reviewed_terminal_design",
            "enrolled_test_face",
            "viewed_incident_log",
            "compared_scores"
        ]
    },
    "EV-003": {
        "title": "Reproduced Photo Spoof",
        "source": "Spoof sandbox — presentation experiment",
        "description": "A printed photo of the enrolled test face reproduces a liveness score above the 0.50 threshold, while a proper depth check would have scored the same flat image ~0.10 — the 2D check is the weak point.",
        "relevance": "Demonstrates the mechanism — a flat image passes a 2D-only liveness check.",
        "required_actions": [
            "tested_photo_spoof",
            "tested_video_replay",
            "compared_scores",
            "reproduced_spoof"
        ]
    },
    "EV-004": {
        "title": "Missing Depth Check",
        "source": "GateKey terminal liveness configuration",
        "description": "The terminal's liveness module is configured for 2D texture only; the depth/3D cue is disabled, so no check can distinguish a flat photo from a real face.",
        "relevance": "Ties the sandbox spoof to the real configuration gap — the evidentiary link.",
        "required_actions": [
            "inspected_liveness_config",
            "reproduced_spoof"
        ]
    },
    "EV-005": {
        "title": "Defense Rationale Recorded",
        "source": "Analyst recommendation",
        "description": "Multi-modal liveness (depth/3D plus a motion or blink challenge) and a second factor for high-security doors is selected as the control that would defeat this photo spoof.",
        "relevance": "Closes the engagement with a control mapped to the exact missing cue.",
        "required_actions": [
            "verified_fix"
        ]
    }
}

INCIDENT_TIMELINE_SEED = [
    {
        "t": "2026-07-26 19:40",
        "label": "After-hours entry recorded at a secured GateKey door"
    },
    {
        "t": "2026-07-26 19:41",
        "label": "Access log shows a high face-match and a passing liveness score"
    },
    {
        "t": "2026-07-27 08:15",
        "label": "Building staff report the badge-holder was off-site at that time"
    },
    {
        "t": "2026-07-28 12:00",
        "label": "Client alleges a printed photo was used at the terminal"
    },
    {
        "t": "2026-07-29 09:00",
        "label": "Bug-bounty engagement GK-2026-133 assigned to Diya; terminal config shows 2D-only liveness"
    }
]

ANALYST_INTERPRETATION = {
    "prompt": "Based on your experiments, what did you observe about the two checks?",
    "options": {
        "a": "The face-match score was low, so the door opened despite a mismatch.",
        "b": "The face match was high and the 2D liveness check also scored the flat photo as live, so both thresholds cleared.",
        "c": "Liveness scored near zero yet the door still opened.",
        "d": "The terminal opened for every input regardless of the scores."
    },
    "correct": "b",
    "min_experiments": 2,
    "feedback": {
        "a": "Review your history — the photo's face-match score was high (~0.97); the match was not the failure.",
        "b": "Correct. The photo cleared the 2D liveness threshold (~0.86) because the terminal never checks depth; a 3D check would have scored it ~0.10.",
        "c": "Review your history — the reported liveness for the photo was above threshold, not near zero; that's the flaw.",
        "d": "Review your history — a genuine mismatch or a true depth check was rejected; the terminal isn't opening for everything."
    }
}

DECISION_POINT = {
    "id": "dp1",
    "prompt": "A photo reportedly opened the door and GateKey claims liveness detection exists. What do you investigate next?",
    "options": {
        "a": "Conclude the enrolled template was stolen and open a credential-theft case.",
        "b": "Reproduce the spoof in the sandbox and compare the scores.",
        "c": "Wipe the incident log so the disputed entry can't cause alarm, then close the report.",
        "d": "Trust GateKey's statement that liveness detection prevents photo attacks."
    },
    "correct": "b",
    "feedback": {
        "b": {
            "observation": "A door opening for a photo could mean a match flaw or a liveness flaw — only reproducing it with scores tells you which.",
            "status": "Hypothesis testable — comparing match vs. liveness scores per spoof isolates the failing check.",
            "next_action": "Run the photo and replay spoofs in the sandbox and read both scores."
        },
        "a": {
            "observation": "A stolen template would still have to pass liveness — assuming theft skips the actual question of why a flat image passed.",
            "status": "Hypothesis not supported by available evidence.",
            "next_action": "Test the liveness path directly before assuming template theft."
        },
        "c": {
            "observation": "The incident log's paired scores are the proof of which check failed.",
            "status": "This path destroys the evidence base rather than testing anything.",
            "next_action": "Preserve the log — the score margin is the finding."
        },
        "d": {
            "observation": "The claim under test is exactly that liveness detection works; taking it on faith tests nothing.",
            "status": "Hypothesis untested.",
            "next_action": "Measure the liveness check against a real spoof rather than trusting the datasheet."
        }
    }
}

KNOWLEDGE_CHECKS = [
    {
        "level": 1,
        "label": "Recognition",
        "prompt": "What security control failed here?",
        "options": {
            "a": "Liveness detection in the facial-recognition terminal",
            "b": "Disk encryption on the terminal",
            "c": "The building's fire-alarm system",
            "d": "Network segmentation"
        },
        "correct": "a"
    },
    {
        "level": 2,
        "label": "Understanding",
        "prompt": "Why did the control fail, even though a liveness check exists?",
        "options": {
            "a": "The liveness check used only 2D texture, so a flat printed photo scored as live",
            "b": "The face-match threshold was set to zero",
            "c": "The terminal had no camera",
            "d": "The intruder held an admin badge"
        },
        "correct": "a"
    },
    {
        "level": 3,
        "label": "Application",
        "prompt": "What change would prevent this specific spoof from working again?",
        "options": {
            "a": "Add multi-modal liveness (depth/3D sensing plus a motion/blink challenge) and require a second factor on high-security doors",
            "b": "Increase the camera resolution",
            "c": "Repaint the door frame a darker color",
            "d": "Shorten the unlock duration"
        },
        "correct": "a"
    }
]

ATTACK_CHAIN_LINKS = {
    "evidence": {
        "label": "Evidence",
        "correct": "EV-003",
        "options": {
            "EV-001": "EV-001: Baseline live access (match ~0.98, liveness ~0.95)",
            "EV-002": "EV-002: Disputed entry accepted (match 0.97, liveness 0.86)",
            "EV-003": "EV-003: Reproduced photo spoof (flat image passes 2D liveness)",
            "EV-004": "EV-004: Missing depth check (2D-only liveness config)"
        }
    },
    "observation": {
        "label": "Observation",
        "correct": "flat_image_scored_live",
        "options": {
            "flat_image_scored_live": "A flat printed photo scored above the liveness threshold because only 2D texture was checked",
            "match_failed": "The face-match score was too low to matter",
            "door_default_open": "The terminal defaulted to unlocked after a crash",
            "random_unlock": "The door unlocked at random"
        }
    },
    "technique": {
        "label": "Technique",
        "correct": "photo_presentation_attack",
        "options": {
            "photo_presentation_attack": "Presentation attack: a printed photo held to a camera-only liveness check",
            "template_theft": "Theft and re-enrollment of the face template",
            "pin_bruteforce": "Brute-forcing the PIN backup",
            "network_replay": "Replaying the unlock command over the network"
        }
    },
    "control_failure": {
        "label": "Control Failure",
        "correct": "liveness_2d_only",
        "options": {
            "liveness_2d_only": "Liveness detection checked only 2D texture, with no depth/3D cue",
            "auth_bypass": "Authentication bypass with no credential at all",
            "encryption_failure": "Encryption failure exposing templates",
            "access_control_gap": "Broken door-schedule access control"
        }
    },
    "impact": {
        "label": "Impact",
        "correct": "physical_intrusion",
        "options": {
            "physical_intrusion": "Unauthorized physical entry to a secured area via a spoofed face",
            "data_breach": "Employee face templates leaked online",
            "service_outage": "All GateKey doors taken offline",
            "financial_theft": "Money stolen from GateKey"
        }
    }
}

ATTACK_CHAIN_SLOT_ORDER = ["evidence", "observation", "technique", "control_failure", "impact"]

TECHNIQUE_OPTIONS = {
    "photo_presentation_attack": "Holding a printed photo to the camera (2D presentation attack)",
    "template_theft": "Stealing and re-enrolling the face template",
    "mask_3d": "A full 3D silicone mask",
    "network_replay": "Replaying the unlock command over the network"
}

CORRECT_TECHNIQUE = "photo_presentation_attack"

REPORT_CONCEPT_GROUPS = {
    "root_cause": {
        "what_happened": [
            "photo",
            "printed",
            "flat image",
            "presentation",
            "spoof",
            "replay",
            "2d"
        ],
        "what_was_affected": [
            "liveness",
            "face-match",
            "biometric",
            "terminal",
            "access"
        ],
        "mechanism": [
            "2d only",
            "no depth",
            "texture",
            "passed",
            "scored as live",
            "missing",
            "bypass"
        ]
    },
    "security_impact": {
        "business_consequence": [
            "door",
            "building",
            "intrusion",
            "physical",
            "trust",
            "product"
        ],
        "security_consequence": [
            "unauthorized access",
            "spoof",
            "bypass",
            "impersonat",
            "breach"
        ]
    },
    "detection": {
        "how_to_detect": [
            "audit",
            "monitor",
            "score margin",
            "liveness score",
            "log",
            "baseline",
            "compare"
        ],
        "what_to_look_for": [
            "low-margin",
            "photo",
            "flat",
            "off-site",
            "score gap",
            "anomal"
        ]
    },
    "mitigation": {
        "multimodal_liveness": [
            "depth",
            "3d",
            "motion",
            "blink",
            "challenge",
            "multi-modal",
            "texture"
        ],
        "complementary_control": [
            "second factor",
            "2fa",
            "badge",
            "pin",
            "audit",
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
            "config"
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
            "photo",
            "liveness",
            "2d",
            "depth",
            "spoof",
            "flat"
        ]
    }
}

CLAIM_TEXT = "A printed photo opened the door because the terminal's liveness check verified only 2D texture and never checked depth, so a flat image scored as live."
CLAIM_SUPPORTING_EVIDENCE = {"EV-002", "EV-003", "EV-004"}
REPORT_MIN_GROUP_HITS = 2

HINTS = [
    {
        "level": 1,
        "penalty": 5,
        "text": "A high face-match score doesn't mean a live person was present — look at the two checks separately."
    },
    {
        "level": 2,
        "penalty": 10,
        "text": "Compare the face-match score and the liveness score for the disputed entry on their own."
    },
    {
        "level": 3,
        "penalty": 15,
        "text": "Not all spoofing materials are treated equally by a camera-only system. Try a photo and a replay."
    },
    {
        "level": 4,
        "penalty": 20,
        "text": "Ask what a photo can never do that a real face does — the terminal never checks depth, so a flat image reads as live."
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
    "Biometric Security",
    "Presentation-Attack / Liveness Analysis",
    "Facial-Recognition Forensics",
    "Access-Log Analysis",
    "Attack Chain Reconstruction",
    "Mitigation Design"
]

REMEDIATION = [
    "Use multi-modal liveness detection (depth/3D sensing, motion or blink challenges, texture analysis).",
    "Require a second factor (badge + face, PIN + face) for high-security doors.",
    "Log and periodically audit low-margin liveness scores, even on successful entries.",
    "Red-team the terminal against current spoofing techniques regularly."
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
    "why_misleading": 'A real physical lapse that suggests a different entry method than the one the logs actually show.',
    # A learner who cites the red herring as root cause is penalised; one who
    # explicitly rejects it earns the red_herring score component.
}

# --- second decision point (distractor rejection) ---
DECISION_POINT_2 = {
    "id": 'D002',
    "prompt": 'You reproduced the photo spoof. Facilities argues the intruder simply used the leaked door PIN. How do you weigh it?',
    "options": {'a': 'Reattribute the entry to PIN reuse — a leaked PIN is the simplest path.', 'b': 'Reject it: the door log shows a FACE-auth success, not a PIN.', 'c': 'Report the entry method as undetermined between a PIN and a face spoof.'},
    "correct": 'b',
    "feedback": {'a': "The leaked PIN is a separate hygiene issue; the log shows face-auth succeeded, so it doesn't explain this entry.", 'b': 'Correct. EV-002/003 tie the entry to a face-auth success reproducible with a photo. Reject the distractor.', 'c': 'The timestamped log removes the ambiguity — commit to the photo-spoof finding (and flag the PIN separately).'},
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
