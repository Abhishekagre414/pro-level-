"""
Phishing-filter engine for lab3 (FinGuard).

The classifier is a real logistic regression over a bag-of-words, trained at
import time with numpy gradient descent on a deterministic synthetic corpus
(seeded RNG, 600 short emails, phish vs. legitimate). Nobody typed the weights
in: the model learns that "verify", "password", "suspended", ... are
phishing-indicative, and that words like "meeting" or "invoice" are not.

The bug the lab teaches is real too. Tokenization is a literal regex over the
RAW text -- no Unicode normalization (NFKC), no stripping of zero-width
characters, no HTML parsing. So:

* a Cyrillic "e" turns "verify" into a different, unseen token,
* a U+200B inside "password" splits it into "pass" + "word",
* a hidden <span> inside "account" splits it into "acc" + markup + "ount".

Those are real string transforms; the model just never sees the feature again.
Honest scope: the corpus is synthetic and small, and the model is a linear
bag-of-words (the kind of filter these CVEs affected), not a neural network.
"""
import math
import random
import re
import unicodedata

import numpy as np

THRESHOLD = 0.80
_TOKEN = re.compile(r"\w+")          # literal match on raw text -- THE bug

HOMOGLYPHS = {
    "a": "\u0430", "e": "\u0435", "o": "\u043e", "p": "\u0440",
    "c": "\u0441", "x": "\u0445", "i": "\u0456",
}


# ------------------------------------------------------------- corpus
# Both classes share the same framing language (greetings, closings, deadlines, URLs)
# so a bag-of-words model has to learn WHICH words carry the signal. The class-specific
# vocabulary is where the phish and legitimate mail actually differ -- including a few
# benign emails that mention "account", "login" or "password" in harmless contexts.
_GREET = ["Dear customer,", "Hello,", "Hi,", "Dear user,", "Dear member,"]
_CLOSE = ["Thank you.", "Regards, Support", "This is an automated message.", "Reply if you have questions."]
_TIME = ["within 24 hours", "by Friday", "today", "this week", "before the end of the day"]
_FROM = ["security", "support", "noreply", "team", "billing", "admin"]
_HOST = ["bank", "secure", "portal", "mail", "pay", "cloud", "service", "docs", "hr", "login"]
_PATH_PHISH = ["verify", "login", "secure", "update", "verify"]
_PATH_LEGIT = ["home", "files", "docs", "wiki", "portal", "login"]

_PHISH_SENT = [
    "Your {thing} is {state}.",
    "Please {act} your {thing2} {time}.",
    "We detected unusual activity on the {thing}.",
    "Click here to {act} your {thing} or it will stay {state}.",
    "Failure to {act} the {thing2} {time} will leave it {state}.",
    "You must {act} your {thing} at {url} {time}.",
    "The {thing} will be {state} unless you {act} it {time}.",
]
_ACT = ["verify", "verify", "verify", "confirm", "update", "validate", "restore"]
_THING = ["account", "account", "password", "password", "login", "billing details", "card"]
_STATE = ["suspended", "locked", "limited", "disabled", "restricted"]

# Legitimate mail uses the same shared words ("your", "urgent", links, deadlines) so the
# model cannot lean on them -- real internal mail is full of "urgent". The model has to learn
# the genuine indicators (verify, password, account, ...) instead.
_LEGIT_SENT = [
    "The {doc} for {topic} is attached.",
    "Please review your {doc} {time}.",
    "Let me know if your team is missing anything.",
    "Your meeting about {topic} is on Thursday.",
    "You can find your files at {url} {time}.",
    "Your {doc} is ready in the portal and no action is needed.",
    "Please confirm your attendance {time}.",
    "I updated the plan for {topic}, see {url}.",
    "To reset a forgotten password use the settings page.",
    "You can log in to the wiki to leave your comments {time}.",
    "Thanks for your call, I will send the schedule {time}.",
    "Your invoice is due at the end of the month.",
    "The account statement is attached for your records.",
    "Please verify the figures in the {doc} with finance {time}.",
]
_DOC = ["invoice", "report", "agenda", "notes", "budget", "account statement", "schedule"]
_TOPIC = ["the quarterly review", "the office move", "the product launch", "the team offsite",
          "the vendor contract", "the hiring plan", "the audit", "the roadmap"]


def _url(rng, paths):
    return f"https://{rng.choice(_HOST)}-{rng.choice(_HOST)}.example/{rng.choice(paths)}"


def _frame(rng, sentences, subject):
    body = " ".join(sentences)
    return (f"From: {rng.choice(_FROM)}@example.com\nSubject: {subject}\n\n"
            f"{rng.choice(_GREET)} {body} {rng.choice(_CLOSE)}")


def _phish(rng):
    f = dict(act=rng.choice(_ACT), thing=rng.choice(_THING), thing2=rng.choice(_THING),
             state=rng.choice(_STATE), time=rng.choice(_TIME), url=_url(rng, _PATH_PHISH))
    sents = [t.format(**f) for t in rng.sample(_PHISH_SENT, rng.randint(2, 3))]
    return _frame(rng, sents, rng.choice(["Urgent: {act} your {thing}", "Notice about your {thing}",
                                          "Action needed: {act} {thing}", "Re: your {thing}"]).format(**f))


def _legit(rng):
    f = dict(doc=rng.choice(_DOC), topic=rng.choice(_TOPIC), time=rng.choice(_TIME),
             url=_url(rng, _PATH_LEGIT))
    sents = [t.format(**f) for t in rng.sample(_LEGIT_SENT, rng.randint(2, 3))]
    return _frame(rng, sents, rng.choice(["Re: {topic}", "Notes from {topic}", "Schedule for {topic}",
                                          "Urgent: {topic}", "Urgent: your {doc}"]).format(**f))


def build_corpus(n_each=300, seed=1337):
    rng = random.Random(seed)  # nosec B311 - deterministic synthetic training data, not security-sensitive
    docs = [(_phish(rng), 1) for _ in range(n_each)] + [(_legit(rng), 0) for _ in range(n_each)]
    rng.shuffle(docs)
    return docs


# ------------------------------------------------------------- model
def tokenize(text):
    """Literal word tokens of the RAW text (lower-cased only). No normalization."""
    return set(_TOKEN.findall(text.lower()))


def _train(docs, epochs=3000, lr=1.0, l2=0.001, min_df=3):
    df = {}
    for text, _ in docs:
        for t in tokenize(text):
            df[t] = df.get(t, 0) + 1
    vocab = sorted(t for t, c in df.items() if c >= min_df)
    index = {t: i for i, t in enumerate(vocab)}
    X = np.zeros((len(docs), len(vocab)))
    y = np.array([lab for _, lab in docs], dtype=float)
    for r, (text, _) in enumerate(docs):
        for t in tokenize(text):
            if t in index:
                X[r, index[t]] = 1.0
    w, b = np.zeros(len(vocab)), 0.0
    for _ in range(epochs):                      # full-batch gradient descent
        p = 1 / (1 + np.exp(-(X @ w + b)))
        g = p - y
        w -= lr * (X.T @ g / len(y) + l2 * w)
        b -= lr * g.mean()
    return vocab, index, w, b


_DOCS = build_corpus()
VOCAB, _INDEX, _W, _B = _train(_DOCS)


def training_accuracy():
    """Accuracy of the trained model on its own corpus (sanity check, not a benchmark)."""
    ok = sum((score(t)[0] >= 0.5) == bool(lab) for t, lab in _DOCS)
    return ok / len(_DOCS)


def _sigmoid(z):
    return 1 / (1 + math.exp(-z))


def contributions(text):
    """{token: weight} for every in-vocabulary token present in `text` (the active features)."""
    return {t: float(_W[_INDEX[t]]) for t in tokenize(text) if t in _INDEX}


def score(text):
    """(confidence, active_features). Confidence = P(phishing) from the trained model."""
    feats = contributions(text)
    return _sigmoid(float(_B) + sum(feats.values())), feats


def verdict(text):
    conf, feats = score(text)
    return conf, feats, (conf >= THRESHOLD)


def explain_rows(text, baseline_text, limit=10):
    """Per-token rows [(token, present, weight, change_vs_baseline)] for the biggest movers."""
    cur, base = contributions(text), contributions(baseline_text)
    rows = []
    for t in set(cur) | set(base):
        change = cur.get(t, 0.0) - base.get(t, 0.0)
        rows.append((t, 1 if t in cur else 0, cur.get(t, base.get(t, 0.0)), change))
    rows.sort(key=lambda r: (-abs(r[3]), -abs(r[2]), r[0]))
    return rows[:limit]


# ------------------------------------------------------------- the attack surface
def base_phish_email():
    return ("From: security@finguard-bank.com\n"
            "Subject: Urgent: verify your account\n\n"
            "Dear customer, please verify your password at\n"
            "https://finguard-bank.example/portal within 24 hours.")


def apply_homoglyph(text):
    """Swap every 'e' in 'verify' for a real lookalike Cyrillic codepoint."""
    out = text
    while True:
        idx = out.lower().find("verify")
        if idx == -1:
            break
        pos = out.find("e", idx, idx + 6)
        if pos == -1:
            break
        out = out[:pos] + HOMOGLYPHS["e"] + out[pos + 1:]
    return out


def apply_zwsp(text):
    """Insert a real U+200B zero-width space inside the word 'password'."""
    return text.replace("password", "pass\u200bword")


def apply_hidden_html(text):
    """Wrap a real invisible <span> inside 'account' to break the literal match."""
    return text.replace("account", 'acc<span style="display:none">x</span>ount')


def apply_random_padding(text, n=50):
    words = ["the", "order", "please", "note", "system", "today", "reference", "kindly", "thanks", "team"]
    rng = random.Random(7)  # nosec B311 - deterministic filler text, not security-sensitive
    pad = " ".join(rng.choice(words) for _ in range(n))
    return text + "\n\n" + pad


def reference_confidences():
    """Confidence of the incident emails, used to derive the room's expected answers."""
    base = base_phish_email()
    return {
        "known": score(base)[0],
        "homoglyph": score(apply_homoglyph(base))[0],
        "zwsp": score(apply_zwsp(base))[0],
        "html": score(apply_hidden_html(base))[0],
        "disputed": score(apply_zwsp(apply_homoglyph(base)))[0],
    }


def answer_pattern(value):
    """Regex accepting `value` as the terminal prints it: 3 decimals, or rounded to 2 (trailing 0 optional)."""
    two = f"{value:.2f}".split(".")[1]
    three = f"{value:.3f}".split(".")[1]
    alts = {two, three}
    if two.endswith("0"):
        alts.add(two[0])
    return r"^0?\.(" + "|".join(sorted(re.escape(a) for a in alts)) + r")$"


# ------------------------------------------------------------- the fix: canonicalise BEFORE the classifier
_INVISIBLE = {"\u200b", "\u200c", "\u200d", "\u2060", "\ufeff"}          # zero-width / joiner / BOM
_CONFUSABLES = {v: k for k, v in HOMOGLYPHS.items()}                       # Cyrillic lookalike -> Latin
_HIDDEN_ELEMENT = re.compile(r"<(\w+)[^>]*display\s*:\s*none[^>]*>.*?</\1>", re.I | re.S)
_TAG = re.compile(r"<[^>]+>")


def normalize(text):
    """Canonical form the classifier should see: drop hidden HTML, NFKC, strip zero-width, fold lookalikes.

    Honest scope: the confusables map only covers the 7 lookalikes this lab's attacker uses; a
    production filter would use the full Unicode UTS #39 confusables table.
    """
    t = _HIDDEN_ELEMENT.sub("", text)
    t = _TAG.sub("", t)
    t = unicodedata.normalize("NFKC", t)
    t = "".join(c for c in t if c not in _INVISIBLE)
    return "".join(_CONFUSABLES.get(c, c) for c in t)


def verdict_normalized(text):
    """Same classifier, but fed the normalized text. Returns (confidence, blocked)."""
    conf, _, blocked = verdict(normalize(text))
    return conf, blocked


def false_positive_count():
    """How many of the corpus's legitimate emails the normalized filter blocks (the fix's cost)."""
    return sum(1 for text, lab in _DOCS if lab == 0 and verdict_normalized(text)[1])
