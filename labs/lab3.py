CASE = {
    "incident_id": "GB-2026-088",
    "client": "FinGuard Bank",
    "role": "AI Security Analyst",
    "severity": "HIGH",
    "date": "2026-05-15",
    "initial_alert": "Multiple high-net-worth clients received targeted phishing emails that bypassed our primary email filtering gateway.",
    "objective": "Determine the exact evasion technique used to bypass the Filter Confidence Analyzer.",
    "business_impact": "Potential account takeover leading to massive financial loss and reputational damage."
}

CONCEPT = {
    "what_is_it": "Adversarial Machine Learning (Evasion Attacks)",
    "normal_architecture": "Incoming emails are parsed and evaluated by an ML text classifier. If spam/phishing confidence exceeds a threshold (e.g., 80%), the email is blocked.",
    "security_control": "ML-based Spam Filter (Filter Confidence Analyzer)",
    "attack_surface": "The text parser and feature extraction pipeline can be manipulated to hide malicious keywords from the model while remaining readable to a human.",
    "normal_behavior": "A standard phishing lure containing typical keywords should be blocked with high confidence (>90%)."
}

HYPOTHESIS = {
    "prompt": "Based on the initial alert, what is your initial hypothesis about how the attack bypassed the filter?",
    "options": {
        "H1": "The attacker compromised the email server to whitelist their domain.",
        "H2": "The attacker used adversarial text obfuscation (homoglyphs/HTML) to lower the ML confidence.",
        "H3": "The ML model's training data was poisoned during the last update.",
        "H4": "The block threshold was accidentally configured too high."
    },
    "best_supported": "H2"
}

EVIDENCE_CATALOG = {
    "EV-001": {
        "title": "Baseline Spam Detection",
        "description": "Standard phishing lures are correctly blocked with high confidence.",
        "relevance": "Confirms the baseline model is functioning properly.",
        "required_actions": ["verified_baseline"]
    },
    "EV-002": {
        "title": "Disputed Email Analysis",
        "description": "The phishing email that reached the clients scored just under the block threshold.",
        "relevance": "Confirms a bypass occurred.",
        "required_actions": ["viewed_disputed", "verified_disputed"]
    },
    "EV-003": {
        "title": "Homoglyph Evasion",
        "description": "Replacing English characters with lookalike Cyrillic characters lowers the model's confidence.",
        "relevance": "Demonstrates one potential vector of attack.",
        "required_actions": ["tested_homoglyphs"]
    },
    "EV-004": {
        "title": "HTML Obfuscation Evasion",
        "description": "Two distinct tricks break tokenization: zero-width Unicode characters injected inside keywords, and hidden HTML spans that split a word the model is trained to catch.",
        "relevance": "Breaks the feature extractor, rendering the text invisible to the ML model.",
        "required_actions": ["tested_html"]
    },
    "EV-005": {
        "title": "Hardened Filter Verified",
        "description": "The fixed filter normalises lookalike characters and strips hidden text, so the same evasion emails are blocked again.",
        "relevance": "Closes the case: the control is mapped to the exact evasion techniques found.",
        "required_actions": ["verified_fix"]
    }
}

INCIDENT_TIMELINE_SEED = [
    {"t": "07:05:00", "label": "Attacker registers lookalike domain."},
    {"t": "08:12:45", "label": "Targeted phishing campaign launched."},
    {"t": "08:13:10", "label": "Emails pass through Filter Confidence Analyzer."},
    {"t": "08:15:30", "label": "Clients report suspicious emails."},
    {"t": "08:40:00", "label": "Lookalike domain traced to registrant 'veil-mail-services'."}
]

ANALYST_INTERPRETATION = {
    "min_experiments": 3,
    "prompt": "After experimenting in the sandbox, which combination of techniques drops the phishing confidence from >90% to below the 80% block threshold without changing the visual meaning?",
    "options": {
        "I1": "Replacing 50% of the text with random characters.",
        "I2": "Using Homoglyphs and HTML Obfuscation on key trigger words.",
        "I3": "Base64 encoding the entire email."
    },
    "correct": "I2",
    "feedback": {
        "I1": "Incorrect. That changes the visual meaning and ruins the phishing lure.",
        "I2": "Correct! These adversarial text techniques preserve visual readability for the victim while breaking the ML model's tokenization.",
        "I3": "Incorrect. Modern filters easily decode base64 before analysis."
    }
}

DECISION_POINT = {
    "prompt": "You've confirmed the email bypasses the filter due to adversarial text obfuscation. What is the most immediate defense mechanism you should deploy?",
    "options": {
        "D1": "Retrain the ML model on billions of obfuscated examples.",
        "D2": "Deploy a pre-processing normalization step to strip hidden HTML and map homoglyphs to ASCII before ML inference.",
        "D3": "Block all emails containing HTML tags."
    },
    "correct": "D2",
    "feedback": {
        "D1": {"observation": "Expensive and an arms race.", "status": "Suboptimal", "next_action": "It won't solve the immediate issue quickly."},
        "D2": {"observation": "Pre-processing defeats the obfuscation, allowing the ML model to see the true text.", "status": "Correct", "next_action": "Standardizing inputs is the best defense against adversarial evasion."},
        "D3": {"observation": "This will block legitimate marketing and formatting.", "status": "Incorrect", "next_action": "Too disruptive to business operations."}
    }
}

KNOWLEDGE_CHECKS = [
    {
        "level": 1,
        "label": "Concept",
        "prompt": "Why are homoglyphs effective against ML text classifiers?",
        "options": {
            "A": "They encrypt the text.",
            "B": "They look identical to humans but have different Unicode values, breaking the model's vocabulary mapping.",
            "C": "They trigger buffer overflows in the parser."
        },
        "correct": "B"
    },
    {
        "level": 2,
        "label": "Defense",
        "prompt": "Which component of the ML pipeline is actually failing in an HTML obfuscation attack?",
        "options": {
            "A": "The neural network weights.",
            "B": "The gradient descent optimizer.",
            "C": "The tokenization and feature extraction phase."
        },
        "correct": "C"
    },
    {
        "level": 3,
        "label": "Application",
        "prompt": "What single change would most reliably neutralize this evasion class before ML inference?",
        "options": {
            "A": "Normalize/canonicalize text (map homoglyphs to ASCII, strip zero-width characters and hidden HTML) before the classifier sees it.",
            "B": "Raise the block threshold to 99%.",
            "C": "Reject all emails from non-English senders."
        },
        "correct": "A"
    }
]

HINTS = [
    {"level": 1, "text": "Look at the disputed email text closely. Notice any strange HTML tags or characters?", "penalty": 5},
    {"level": 2, "text": "Try the sandbox: Apply HTML obfuscation to the trigger words 'Password' and 'Reset'. Watch the confidence drop.", "penalty": 10},
    {"level": 3, "text": "Diff the bypass email against a blocked one at the character level — inspect the actual Unicode code points, not how they render.", "penalty": 15},
    {"level": 4, "text": "No single trick crosses the threshold on its own. It takes homoglyphs AND hidden HTML together.", "penalty": 20}
]

ATTACK_CHAIN_LINKS = {
    "evidence_link": {
        "label": "Evidence",
        "options": {
            "E1": "Disputed email bypasses filter.",
            "E2": "Sandbox confirms homoglyphs lower confidence.",
            "E3": "Sandbox confirms HTML obfuscation lowers confidence.",
            "E4": "Both Homoglyphs and HTML Obfuscation (EV-003, EV-004)"
        },
        "correct": "E4"
    },
    "observation_link": {
        "label": "Observation",
        "options": {
            "O1": "Confidence dropped below the block threshold only when homoglyphs and hidden HTML were combined.",
            "O2": "The filter blocked every email regardless of content.",
            "O3": "The confidence score never changed under any transform."
        },
        "correct": "O1"
    },
    "technique_link": {
        "label": "Technique",
        "options": {
            "T1": "Data Poisoning",
            "T2": "Adversarial Text Evasion (Obfuscation)",
            "T3": "Model Extraction"
        },
        "correct": "T2"
    },
    "control_failure_link": {
        "label": "Control Failure",
        "options": {
            "C1": "The tokenizer/feature extractor ran on raw, un-normalized text, so perturbed tokens never matched trained features.",
            "C2": "Transport encryption was missing.",
            "C3": "The mail server lacked authentication."
        },
        "correct": "C1"
    },
    "impact_link": {
        "label": "Impact",
        "options": {
            "I1": "Malicious payload executed on server.",
            "I2": "Phishing emails reach victim inboxes, risking credential theft.",
            "I3": "Spam filter crashes."
        },
        "correct": "I2"
    }
}
ATTACK_CHAIN_SLOT_ORDER = ["evidence_link", "observation_link", "technique_link", "control_failure_link", "impact_link"]

ACTIONS = ["verified_baseline", "viewed_disputed", "verified_disputed", "tested_homoglyphs", "tested_html", "verified_fix"]
ACTION_DEPENDENCIES = {
    "verified_fix": ["tested_html"],
    "viewed_disputed": ["verified_baseline"],
    "verified_disputed": ["viewed_disputed"],
    "tested_homoglyphs": ["verified_disputed"],
    "tested_html": ["tested_homoglyphs"],
}
SKILLS_DEMONSTRATED = ["Adversarial ML", "Evasion Attacks", "Phishing Analysis"]

CLAIM_TEXT = "The attacker evaded the ML spam filter by manipulating the input text to preserve human readability while breaking machine tokenization."

HYPOTHESIS_SUPPORT = {
    "H1": [],
    "H2": ["EV-002", "EV-003", "EV-004"],
    "H3": [],
    "H4": [],
}

TECHNIQUE_OPTIONS = {
    "adversarial_evasion": "Adversarial text evasion (homoglyphs + HTML obfuscation)",
    "data_poisoning": "Training-data poisoning of the classifier",
    "server_compromise": "Email-server compromise / domain whitelisting",
    "model_extraction": "Model extraction / weight theft",
}
CORRECT_TECHNIQUE = "adversarial_evasion"

REPORT_CONCEPT_GROUPS = {
    "root_cause": {
        "what_happened": ["homoglyph", "obfuscat", "adversarial", "perturb", "evasion",
                          "lookalike", "cyrillic", "zero-width", "zero width", "invisible"],
        "what_was_affected": ["filter", "classifier", "tokeniz", "feature", "confidence"],
        "mechanism": ["drop", "below", "threshold", "lower", "reduced", "broke", "break", "hide"],
    },
    "security_impact": {
        "business_consequence": ["phishing", "credential", "account takeover", "takeover",
                                 "financial", "reputational", "client"],
        "security_consequence": ["bypass", "inbox", "delivered", "undetected", "trust"],
    },
    "detection": {
        "how_to_detect": ["confidence", "score", "compare", "baseline", "monitor", "audit",
                          "heatmap", "token"],
        "what_to_look_for": ["drop", "unicode", "non-ascii", "non ascii", "homoglyph",
                             "hidden", "span", "encoding", "anomal"],
    },
    "mitigation": {
        "normalization": ["normaliz", "canonical", "strip", "ascii", "map", "sanitiz",
                          "pre-process", "preprocess"],
        "complementary_control": ["adversarial training", "retrain", "rule-based", "reputation",
                                  "layer", "defense-in-depth", "defense in depth"],
    },
    "reasoning": {
        "evidence_reference": ["ev-001", "ev-002", "ev-003", "ev-004", "baseline", "disputed",
                               "sandbox", "experiment"],
        "causal_link": ["because", "therefore", "shows", "proves", "demonstrates", "confirms",
                        "consistent", "indicates"],
        "conclusion": ["homoglyph", "obfuscat", "adversarial", "evasion", "tokeniz"],
    },
}

CLAIM_SUPPORTING_EVIDENCE = {"EV-002", "EV-003", "EV-004"}
REPORT_MIN_GROUP_HITS = 2

SCORE_WEIGHTS = {
    "investigation": 20,
    "evidence": 15,
    "reasoning": 20,
    "knowledge": 15,
    "final_report": 25,
    "efficiency": 5,
}

REMEDIATION = [
    'Use adversarial training with known evasion patterns included in the training set.',
    'Normalize/canonicalize text (homoglyph mapping, HTML stripping) before classification.',
    'Layer ML detection with rule-based and reputation-based checks.',
    'Continuously retrain on newly observed bypass samples.',
]
