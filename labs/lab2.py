CASE = {
    "client": "MedSync AI",
    "incident_id": "MS-2026-042",
    "severity": "HIGH",
    "role": "AI Security Analyst",
    "date": "2026-04-10",
    "business_impact": "The diagnostic model is misdiagnosing a specific rare condition, which could lead to severe medical malpractice risks.",
    "initial_alert": "After the last training round, the federated learning model started misdiagnosing a rare condition far too often. Something in that round is wrong.",
    "objective": "Identify the poisoned contributor node and determine the type of poisoning attack.",
}

CONCEPT = {
    "what_is_it": "Federated learning allows multiple hospitals to collaboratively train a shared global model without exchanging raw patient data. They only share model updates (gradients) with a central aggregator.",
    "normal_architecture": "Hospitals train locally on their private data → send model updates (gradients) to MedSync → MedSync aggregates the updates (e.g., using federated averaging) → global model is updated and distributed back.",
    "security_control": "Federated learning protects patient privacy by design, as raw data never leaves the hospital.",
    "attack_surface": "Because the aggregator cannot inspect the raw training data, it blindly trusts the model updates. A compromised node can send malicious updates (gradients) designed to 'poison' the global model, causing it to misclassify specific inputs.",
    "normal_behavior": "During normal training, gradient updates from different hospitals should have similar statistical distributions and magnitudes."
}

ACTIONS = [
    "viewed_architecture",
    "viewed_accuracy_log",
    "compared_updates",
    "identified_outlier",
    "reconstructed_attack",
    "analyst_interpretation_correct",
    "verified_fix",
]

ACTION_DEPENDENCIES = {
    "verified_fix": ["reconstructed_attack"],
    "viewed_accuracy_log": ["viewed_architecture"],
    "compared_updates": ["viewed_accuracy_log"],
    "identified_outlier": ["compared_updates"],
    "reconstructed_attack": ["identified_outlier"],
}

HYPOTHESIS = {
    "prompt": "Before you dig in — what do you think is happening?",
    "options": {
        "a": "A hospital accidentally leaked raw patient data to the central server.",
        "b": "The central aggregation server was hacked directly.",
        "c": "A participating node submitted a malicious model update that poisoned the global model.",
        "d": "The model simply overfitted due to too much training.",
    },
    "best_supported": "c",
}

HYPOTHESIS_SUPPORT = {
    "a": [],
    "b": [],
    "c": ["EV-001", "EV-002", "EV-003", "EV-004"],
    "d": [],
}

EVIDENCE_CATALOG = {
    "EV-001": {
        "title": "Federated Architecture Constraints",
        "source": "Architecture Diagram",
        "description": "Patient data stays local; only gradients are shared with the aggregator.",
        "relevance": "Rules out direct data breaches at the aggregator level.",
        "required_actions": ["viewed_architecture"],
    },
    "EV-002": {
        "title": "Accuracy Drop in Round 6",
        "source": "Per-Round Accuracy Log",
        "description": "Accuracy for the rare condition plummeted from 91% to 58% in Round 6.",
        "relevance": "Pinpoints exactly when the poisoning took effect.",
        "required_actions": ["viewed_accuracy_log"],
    },
    "EV-003": {
        "title": "Node 3 Gradient Anomaly",
        "source": "Gradient Comparator",
        "description": "Node 3's update magnitude in Round 6 (Δ=0.31) was ~20x the baseline (Δ≈0.015) — the attacker scaled/boosted the update so the label-flip would survive averaging, which is exactly why it stands out statistically.",
        "relevance": "Identifies Node 3 as the source of the anomalous update.",
        "required_actions": ["compared_updates"],
    },
    "EV-004": {
        "title": "Label Flipping Confirmation",
        "source": "Attack Reconstruction",
        "description": "Node 3's update systematically shifted the decision boundary to mislabel the rare condition as a common condition.",
        "relevance": "Confirms the exact attack technique used to poison the model.",
        "required_actions": ["reconstructed_attack"],
    },
    "EV-005": {
        "title": "Robust Aggregation Recommendation",
        "source": "Analyst recommendation",
        "description": "Recommended switching from simple Federated Averaging to a robust aggregation method (e.g., trimmed mean).",
        "relevance": "Closes the investigation with a control mapped to the specific failure mode found.",
        "required_actions": ["verified_fix"],
    },
}

INCIDENT_TIMELINE_SEED = [
    {"t": "2026-04-08 18:00", "label": "Round 5 aggregation completes successfully"},
    {"t": "2026-04-09 23:45", "label": "Round 6 aggregation completes"},
    {"t": "2026-04-10 07:12", "label": "Clinical QA flags high misdiagnosis rate for rare condition"},
    {"t": "2026-04-10 09:30", "label": "Case assigned to AI Security team"},
    {"t": "2026-04-10 09:45", "label": "Same 'mirage' toolmark spotted on the Node 3 update metadata"},
]

ANALYST_INTERPRETATION = {
    "prompt": "Based on the gradient comparisons in Round 6, what best describes the anomaly?",
    "options": {
        "a": "All nodes submitted highly variable updates.",
        "b": "Node 3 submitted an update with a magnitude significantly larger than the others.",
        "c": "Node 1 dropped out of the training round entirely.",
        "d": "The global model rejected all updates due to high loss.",
    },
    "correct": "b",
    "min_experiments": 1,
    "feedback": {
        "a": "Look at the comparator again. Nodes 1, 2, 4, and 5 have very similar, small update magnitudes.",
        "b": "Correct. Node 3 is a clear statistical outlier in Round 6, suggesting its update is malicious.",
        "c": "Node 1 submitted an update normally. Check the comparator.",
        "d": "The aggregation completed, which is why the model's accuracy dropped.",
    },
}

DECISION_POINT = {
    "id": "dp1",
    "prompt": "The accuracy log shows a sudden drop in Round 6. What do you investigate next?",
    "options": {
        "a": "Delete the Round 6 global model and pretend it didn't happen.",
        "b": "Compare the individual node updates (gradients) submitted during Round 6 to find an outlier.",
        "c": "Demand the raw patient data from all hospitals.",
        "d": "Conclude that federated learning is fundamentally broken.",
    },
    "correct": "b",
    "feedback": {
        "b": {
            "observation": "Since the aggregation process merges individual updates, inspecting those inputs is the only way to find the source.",
            "status": "Hypothesis testable — the Gradient Comparator can reveal anomalous submissions.",
            "next_action": "Open the Gradient Comparator and inspect Round 6.",
        },
        "a": {
            "observation": "Rolling back doesn't identify the attacker or patch the vulnerability.",
            "status": "Hypothesis untested.",
            "next_action": "Investigate to find the root cause.",
        },
        "c": {
            "observation": "Federated learning guarantees privacy; hospitals will not share raw data.",
            "status": "Action blocked by policy.",
            "next_action": "Find a way to investigate using only the shared model updates.",
        },
        "d": {
            "observation": "Federated learning has specific vulnerabilities, but they can be mitigated.",
            "status": "Hypothesis untested.",
            "next_action": "Investigate the specific failure mode in this instance.",
        },
    },
}

KNOWLEDGE_CHECKS = [
    {
        "level": 1, "label": "Recognition",
        "prompt": "What data is never shared in a federated learning setup?",
        "options": {
            "a": "Model gradients",
            "b": "Raw patient data",
            "c": "The global model architecture",
            "d": "Training loss metrics",
        },
        "correct": "b",
    },
    {
        "level": 2, "label": "Understanding",
        "prompt": "Why was the poisoned update able to ruin the global model?",
        "options": {
            "a": "The aggregator blindly trusted and averaged all submitted updates.",
            "b": "The attacker stole the aggregator's private key.",
            "c": "The global model was too small to handle the data.",
            "d": "The hospital network was unencrypted.",
        },
        "correct": "a",
    },
    {
        "level": 3, "label": "Application",
        "prompt": "What defense mechanism prevents a single outlier node from poisoning the global model?",
        "options": {
            "a": "Robust aggregation (e.g., trimmed mean or coordinate-wise median)",
            "b": "Stronger passwords for the hospital administrators",
            "c": "Increasing the number of training epochs",
            "d": "Encrypting the global model at rest",
        },
        "correct": "a",
    },
]

ATTACK_CHAIN_LINKS = {
    "evidence": {
        "label": "Evidence",
        "correct": "EV-003",
        "options": {
            "EV-001": "EV-001: Architecture constraints",
            "EV-002": "EV-002: Accuracy drop in Round 6",
            "EV-003": "EV-003: Node 3 gradient anomaly",
            "EV-004": "EV-004: Attack reconstruction",
        },
    },
    "observation": {
        "label": "Observation",
        "correct": "outlier_update",
        "options": {
            "outlier_update": "Node 3 submitted an update with a massive magnitude compared to others.",
            "accuracy_drop": "Global accuracy dropped across all classes.",
            "data_leak": "Patient data was found on the public internet.",
            "server_crash": "The aggregation server crashed during Round 6.",
        },
    },
    "technique": {
        "label": "Technique",
        "correct": "label_flipping",
        "options": {
            "label_flipping": "Model poisoning via label flipping",
            "sql_injection": "SQL Injection into the aggregator database",
            "model_theft": "Model weight extraction",
            "prompt_injection": "Prompt injection",
        },
    },
    "control_failure": {
        "label": "Control Failure",
        "correct": "naive_aggregation",
        "options": {
            "naive_aggregation": "The aggregator blindly averaged updates without anomaly detection (naive aggregation).",
            "weak_encryption": "Transport encryption was weak or missing.",
            "missing_auth": "The API lacked authentication.",
            "watermark_failure": "The watermark signal was degraded.",
        },
    },
    "impact": {
        "label": "Impact",
        "correct": "misdiagnosis",
        "options": {
            "misdiagnosis": "The global model misdiagnoses a specific condition, causing medical risk.",
            "privacy_breach": "Patient data was compromised.",
            "financial_loss": "Money was stolen from the hospital.",
            "downtime": "The hospital network went offline.",
        },
    },
}

ATTACK_CHAIN_SLOT_ORDER = ["evidence", "observation", "technique", "control_failure", "impact"]

TECHNIQUE_OPTIONS = {
    "label_flipping": "Model poisoning via label flipping",
    "backdoor": "Backdoor trigger insertion",
    "data_breach": "Direct exfiltration of patient data",
    "ddos": "Distributed Denial of Service",
}
CORRECT_TECHNIQUE = "label_flipping"

REPORT_CONCEPT_GROUPS = {
    "root_cause": {
        "what_happened": ["poison", "malicious", "manipulat", "gradient", "update", "node 3"],
        "what_was_affected": ["global model", "aggregator", "diagnostic"],
        "mechanism": ["label flip", "misclassif", "shift", "magnitude", "outlier"],
    },
    "security_impact": {
        "business_consequence": ["misdiagnosis", "malpractice", "patient", "risk", "health"],
        "security_consequence": ["integrity", "trust", "poisoned", "compromised"],
    },
    "detection": {
        "how_to_detect": ["compare", "magnitude", "direction", "anomaly", "outlier", "deviation"],
        "what_to_look_for": ["delta", "variance", "statistical", "spike"],
    },
    "mitigation": {
        "aggregation_improvement": ["robust", "aggregation", "trimmed", "median", "clip", "discard"],
        "complementary_control": ["monitor", "reputation", "audit"],
    },
    "reasoning": {
        "evidence_reference": ["ev-001", "ev-002", "ev-003", "ev-004", "round 6", "comparator"],
        "causal_link": ["because", "therefore", "shows", "proves", "demonstrates", "confirms", "correlat"],
        "conclusion": ["poisoning", "node 3", "label flipping", "malicious"],
    },
}

CLAIM_TEXT = "Node 3 poisoned the global model using a label-flipping attack during Round 6."
CLAIM_SUPPORTING_EVIDENCE = {"EV-002", "EV-003", "EV-004"}
REPORT_MIN_GROUP_HITS = 2

HINTS = [
    {"level": 1, "penalty": 5, "text": "Look at the accuracy trend round by round, not just the final model."},
    {"level": 2, "penalty": 10, "text": "A poisoned update usually stands out statistically from the rest."},
    {"level": 3, "penalty": 15, "text": "Ask what condition specifically got worse — that tells you the attacker's target."},
    {"level": 4, "penalty": 20, "text": "The server trusted every update equally. Should it have?"},
]

SCORE_WEIGHTS = {
    "investigation": 20,
    "evidence": 15,
    "reasoning": 20,
    "knowledge": 15,
    "final_report": 25,
    "efficiency": 5,
}

SKILLS_DEMONSTRATED = [
    "AI Security Fundamentals",
    "Federated Learning Architectures",
    "Model Poisoning & Label Flipping",
    "Gradient Anomaly Detection",
    "Robust Aggregation Defenses",
]

REMEDIATION = [
    'Use robust aggregation (e.g., trimmed mean, coordinate-wise median, outlier clipping).',
    'Monitor per-round, per-node contribution statistics, not just global accuracy.',
    'Apply anomaly detection to submitted updates before aggregation.',
    'Consider reputation/weighting systems for repeat contributors.',
]
