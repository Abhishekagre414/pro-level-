CASE = {
    "incident_id": "SC-2026-099",
    "client": "VaultLine",
    "role": "AI Security Analyst",
    "severity": "CRITICAL",
    "date": "2026-07-01",
    "initial_alert": "An attacker bypassed the VoiceID biometric authentication gateway and authorized a wire transfer using a deepfake clone of the CEO's voice.",
    "objective": "Use the Voice Authenticity Analyzer to determine why the synthetic voice was accepted.",
    "business_impact": "Unauthorized financial transfer and breach of high-security biometric systems."
}

CONCEPT = {
    "what_is_it": "Biometric Authentication Bypass (Voice Cloning)",
    "normal_architecture": "VoiceID records the caller and compares the audio against the CEO's voiceprint model (matching pitch, cadence, and tone).",
    "security_control": "Voice Biometric Authentication (Similarity Matching)",
    "attack_surface": "A text-to-speech deepfake can easily match pitch and tone, fooling similarity checks if 'liveness' (artifacts, breath, background acoustics) is not rigorously evaluated.",
    "normal_behavior": "A genuine recording of a user should pass the similarity check and register natural acoustic artifacts."
}

HYPOTHESIS = {
    "prompt": "Based on the initial alert, what is your initial hypothesis about the bypass?",
    "options": {
        "H1": "The attacker stole the database of hashed voiceprints and cracked them.",
        "H2": "The authentication system trusted the high similarity of the deepfake voice without properly verifying acoustic liveness.",
        "H3": "The CEO's phone was infected with malware.",
        "H4": "A staff member was socially engineered into approving the transfer."
    },
    "best_supported": "H2"
}

EVIDENCE_CATALOG = {
    "EV-001": {
        "title": "Baseline Similarity Check",
        "description": "A genuine recording of the CEO scores 98% similarity and passes authentication.",
        "relevance": "Confirms the baseline system works for the real user.",
        "required_actions": ["verified_baseline"]
    },
    "EV-002": {
        "title": "Disputed Audio Analysis",
        "description": "The attacker's audio scored 95% similarity and bypassed the gateway.",
        "relevance": "Confirms the deepfake was convincing enough to fool the primary check.",
        "required_actions": ["verified_disputed"]
    },
    "EV-003": {
        "title": "Spectral Liveness Failure",
        "description": "Advanced spectral analysis shows the disputed audio lacks natural breath sounds and acoustic room reflections (Liveness Score: 12%).",
        "relevance": "Strongly indicates the audio was synthetically generated rather than a live human in a room.",
        "required_actions": ["run_spectral_analysis"]
    },
    "EV-004": {
        "title": "Threshold Misconfiguration",
        "description": "The VoiceID system was configured to only require 'Similarity > 85%' while ignoring the 'Liveness' metric entirely.",
        "relevance": "Identifies the root cause security control failure.",
        "required_actions": ["identified_misconfig"]
    },
    "EV-005": {
        "title": "Stricter Liveness Verified",
        "description": "With the corrected threshold and liveness check, the cloned voice is rejected while the genuine one still passes.",
        "relevance": "Closes the case: the defense is proven against the disputed call.",
        "required_actions": ["verified_fix"]
    }
}

INCIDENT_TIMELINE_SEED = [
    {"t": "16:20:00", "label": "Incoming call to automated wire transfer system."},
    {"t": "16:20:15", "label": "VoiceID captures caller audio and runs similarity match."},
    {"t": "16:20:25", "label": "Voiceprint matched. Authentication successful."},
    {"t": "16:22:00", "label": "Wire transfer initiated."},
    {"t": "16:40:00", "label": "Clone commission traced to the 'veil' marketplace — the through-line across all five cases."}
]

ANALYST_INTERPRETATION = {
    "min_experiments": 1,
    "prompt": "After running the spectral analysis on the disputed audio, what proves it is a deepfake?",
    "options": {
        "I1": "The pitch is slightly lower than the genuine CEO.",
        "I2": "It lacks natural acoustic artifacts like breath and room reverberation.",
        "I3": "The file size was too small."
    },
    "correct": "I2",
    "feedback": {
        "I1": "Incorrect. Pitch variations happen naturally due to sickness or mood.",
        "I2": "Correct! Deepfakes often perfectly replicate the tone but fail to generate the complex, messy acoustics of a real human speaking in a physical room.",
        "I3": "Incorrect. File compression does not indicate a deepfake."
    }
}

DECISION_POINT = {
    "prompt": "You discovered the system only checked 'Similarity' and ignored 'Liveness'. How do you fix the biometric gateway?",
    "options": {
        "D1": "Increase the required Similarity threshold from 85% to 99%.",
        "D2": "Require both Similarity > 85% AND Liveness > 70%.",
        "D3": "Switch to facial recognition."
    },
    "correct": "D2",
    "feedback": {
        "D1": {"observation": "A perfect deepfake can easily hit 99% similarity, while the real CEO with a cold might fail.", "status": "Incorrect", "next_action": "Similarity is the wrong metric to rely on."},
        "D2": {"observation": "This enforces defense-in-depth, ensuring the voice is both correct and generated by a live human.", "status": "Correct", "next_action": "Update the authentication policy."},
        "D3": {"observation": "Facial recognition is also vulnerable to deepfakes if liveness isn't checked.", "status": "Suboptimal", "next_action": "Fix the current control first."}
    }
}

KNOWLEDGE_CHECKS = [
    {
        "level": 1,
        "label": "Concept",
        "prompt": "What does a 'Liveness Detection' system look for?",
        "options": {
            "A": "It checks if the person knows the password.",
            "B": "It looks for physiological signs of life, such as breath, blinking, or acoustic reflections.",
            "C": "It measures how quickly the user responds."
        },
        "correct": "B"
    },
    {
        "level": 2,
        "label": "Defense",
        "prompt": "Why is relying solely on biometric 'similarity' dangerous in the age of generative AI?",
        "options": {
            "A": "Because generative AI can easily replicate the biometric template itself (the voice or face) without needing the physical person.",
            "B": "Because AI models take too long to process.",
            "C": "Because biometric data changes every day."
        },
        "correct": "A"
    },
    {
        "level": 3,
        "label": "Application",
        "prompt": "What change stops a cloned voice even when it perfectly matches the similarity check?",
        "options": {
            "A": "Require an independent liveness check (and/or a second authentication factor).",
            "B": "Raise the similarity threshold to 99%.",
            "C": "Record a longer voice sample."
        },
        "correct": "A"
    }
]

HINTS = [
    {"level": 1, "text": "Run the baseline check, then run the disputed audio. They both pass, but look at the second metric.", "penalty": 5},
    {"level": 2, "text": "Run the Spectral Analysis. Compare the Liveness score of the baseline vs the disputed audio.", "penalty": 10},
    {"level": 3, "text": "The disputed audio passes similarity. Look at the SECOND metric the config gates on — or doesn't.", "penalty": 15},
    {"level": 4, "text": "Similarity proves 'sounds like'. Only liveness proves 'is a live human'.", "penalty": 20}
]

ATTACK_CHAIN_LINKS = {
    "evidence_link": {
        "label": "Evidence",
        "options": {
            "E1": "Baseline passes.",
            "E2": "Spectral Analysis shows Liveness of 12% on the disputed audio (EV-003).",
            "E3": "The wire transfer was initiated."
        },
        "correct": "E2"
    },
    "observation_link": {
        "label": "Observation",
        "options": {
            "O1": "The disputed audio passed similarity (95%) but carried no natural breath or room acoustics.",
            "O2": "The audio failed the similarity check outright.",
            "O3": "The caller entered the wrong PIN."
        },
        "correct": "O1"
    },
    "technique_link": {
        "label": "Technique",
        "options": {
            "T1": "Voice Deepfake / Cloning",
            "T2": "Replay Attack (playing a recording)",
            "T3": "Credential Stuffing"
        },
        "correct": "T1"
    },
    "control_failure_link": {
        "label": "Control Failure",
        "options": {
            "C1": "The gateway authenticated on similarity alone and ignored the liveness metric entirely.",
            "C2": "The password database was stored in plaintext.",
            "C3": "The API had no rate limiting."
        },
        "correct": "C1"
    },
    "impact_link": {
        "label": "Impact",
        "options": {
            "I1": "CEO was embarrassed.",
            "I2": "System crashed.",
            "I3": "Biometric bypass allowed unauthorized wire transfer."
        },
        "correct": "I3"
    }
}
ATTACK_CHAIN_SLOT_ORDER = ["evidence_link", "observation_link", "technique_link", "control_failure_link", "impact_link"]

ACTIONS = ["verified_baseline", "verified_disputed", "run_spectral_analysis", "identified_misconfig", "verified_fix"]
ACTION_DEPENDENCIES = {
    "verified_fix": ["identified_misconfig"],
    "verified_disputed": ["verified_baseline"],
    "run_spectral_analysis": ["verified_disputed"],
    "identified_misconfig": ["run_spectral_analysis"],
}
SKILLS_DEMONSTRATED = ["Biometric Security", "Voice Liveness Detection", "Deepfake Analysis"]

CLAIM_TEXT = "The attacker used a voice deepfake to fool the similarity check, which succeeded because the system failed to enforce liveness verification."

HYPOTHESIS_SUPPORT = {
    "H1": [],
    "H2": ["EV-002", "EV-003", "EV-004"],
    "H3": [],
    "H4": [],
}

TECHNIQUE_OPTIONS = {
    "voice_deepfake": "AI voice cloning / deepfake bypass of biometric auth",
    "replay_attack": "Replay of a genuine recording",
    "credential_stuffing": "Credential stuffing against the auth API",
    "voiceprint_theft": "Theft and cracking of stored voiceprints",
}
CORRECT_TECHNIQUE = "voice_deepfake"

REPORT_CONCEPT_GROUPS = {
    "root_cause": {
        "what_happened": ["deepfake", "clone", "synthetic", "synthesiz", "tts", "text-to-speech",
                          "text to speech", "generated voice", "ai voice"],
        "what_was_affected": ["voiceid", "biometric", "authentication", "voiceprint", "gateway",
                              "similarity"],
        "mechanism": ["liveness", "missing", "ignored", "not enforced", "no liveness",
                      "similarity only", "spectral", "artifact", "breath"],
    },
    "security_impact": {
        "business_consequence": ["wire transfer", "fraud", "financial", "unauthorized", "transfer",
                                 "account", "high-value", "high value"],
        "security_consequence": ["bypass", "impersonat", "spoof", "trust", "single factor",
                                 "single-factor"],
    },
    "detection": {
        "how_to_detect": ["liveness", "spectral", "confidence", "compare", "baseline", "score",
                          "monitor", "audit", "anomal"],
        "what_to_look_for": ["breath", "reverberation", "room reflection", "artifact", "12%",
                             "low liveness", "micro-timing", "micro timing"],
    },
    "mitigation": {
        "liveness_detection": ["liveness", "challenge", "real-time", "real time", "spectral check",
                               "acoustic"],
        "complementary_control": ["multi-factor", "mfa", "multi factor", "second factor",
                                  "callback", "out-of-band", "out of band", "defense-in-depth",
                                  "defense in depth", "threshold"],
    },
    "reasoning": {
        "evidence_reference": ["ev-001", "ev-002", "ev-003", "ev-004", "baseline", "disputed",
                               "spectral", "liveness"],
        "causal_link": ["because", "therefore", "shows", "proves", "demonstrates", "confirms",
                        "consistent", "indicates", "suggests"],
        "conclusion": ["deepfake", "clone", "liveness", "similarity", "biometric"],
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
    'Add liveness detection (e.g., challenge phrases, real-time interaction cues) alongside voice matching.',
    'Require multi-factor authentication for high-value account actions.',
    'Monitor and flag authentication attempts with anomalous confidence-score patterns.',
    'Periodically red-team the voice-auth system against current cloning techniques.',
]
