"""
Regression tests for the lab-content fixes:
  1. Lab 1's detection threshold is stated consistently (engine == lab module == question text).
  2. Free-text answers are matched as whole words/phrases, never as loose substrings, so generic or
     accidental text can't pass ("ir" inside "their", "text" inside any sentence, "28000" for 8000...).
  3. Terminals in labs 6-10 never print the flag; only completing the room releases it.
  4. Every lab (1-10) has a graded `verify-fix` step that replays the exploit against the fixed system.
"""
import re
import sys

import pytest

import app as appmod
from storylines import storyline_for
from tests.walkthrough import solve_lab

sys.path.insert(0, "sandboxes1")
import lab1_engine as E1  # noqa: E402
from labs import lab1 as LAB1  # noqa: E402
import rooms  # noqa: E402

TEXT_QUESTIONS = {
    q["id"]: q
    for lab in [f"lab{i}" for i in range(1, 11)]
    for q in storyline_for(lab).all_questions(lab)
    if q["type"] == "text"
}


# ------------------------------------------------------------------ 1. Lab 1 threshold
def test_lab1_threshold_is_consistent_everywhere():
    assert LAB1.DETECTION_THRESHOLD == E1.THRESHOLD == 0.55
    q = TEXT_QUESTIONS["l1t3a"]["text"]
    assert f"{E1.THRESHOLD:.2f}" in q and "0.50" not in q


# ------------------------------------------------------------------ 2. answer patterns
# (accepted examples, rejected examples) per question
CASES = {'l1t1c': (['provenance', 'Origin', 'its origin'], ['originally', 'prove', 'x']),
 'l1t2b': (['watermark', 'the watermark signal'], ['watermarking tool']),
 'l1t3a': (['compress and noise', 'noise and compression', 'JPEG compression and noise'],
           ['compress', 'noise', 'compressor']),
 'l1t4a': (['mirage-kit', 'Mirage kit', 'miragekit'], ['mirage', 'mirage-agg']),
 'l1t4b': (['post', 'post-processing', 'postprocessing', 'post_process'],
           ['postgres', 'compost', 'generation']),
 'l2t1a': (['patient data', 'patients', 'medical records'], ['impatient', 'gradient']),
 'l2t1b': (['gradients', 'model updates', 'gradient'], ['upgrade', 'patient data']),
 'l2t2a': (['6', 'round 6', 'round6', 'in round 6'], ['60', 'round 60', '16', 'round']),
 'l2t4a': (['label flipping', 'label-flip', 'label_flip', 'labelflip'],
           ['label', 'flip', 'unlabel flippant']),
 'l2t4b': (['mirage-agg-3.1'], ['mirage', 'mirage-agg', 'mirage-agg-3.10']),
 'l2t5a': (['trimmed mean', 'trimmed-mean', 'median', 'robust aggregation'], ['robust', 'mean', 'fedavg']),
 'l3t1b': (['phishing', 'phish'], ['fish', 'phisher king']),
 'l3t2b': (['Cyrillic', 'cyrillic letters'], ['greek', 'latin']),
 'l3t3a': (['homoglyph and zwsp', 'zero-width and homoglyphs', 'homoglyph + zero width space'],
           ['homoglyph', 'homoglyph and html', 'zwsp', 'html and zwsp']),
 'l3t4a': (['verify', "'verify'", '"verify"'], ['verified', 'verify account now', 'urgent']),
 'l3t5a': (['normalize', 'normalization', 'unicode normalisation', 'NFKC'], ['normal']),
 'l4t1a': (['API keys', 'internal api key', 'staff api keys', 'secret key'],
           ['internal', 'staff', 'secret', 'keys']),
 'l4t2b': (['a very long message',
            'a huge pasted text',
            'filler',
            'the user pasted a large block of text',
            'context flooding'],
           ['text', 'long', 'large', 'novel', 'a text']),
 'l4t3b': (['system prompt', 'the instructions', 'safety rules', 'rules'],
           ['system', 'prompts', 'construction']),
 'l4t4a': (['8040', '8,040', '8000', '8k', '~8,000 tokens', 'about 8000'],
           ['18,000', '80,000', '28000', '8', '80400']),
 'l4t4b': (['MIRAGE-FLOOD-v2', 'mirage flood', 'MIRAGE-FLOOD'], ['mirage', 'flood']),
 'l4t5a': (['system prompt', 'system instructions', 'security rules', 'instructions'],
           ['system', 'rules', 'text']),
 'l5t1b': (['accepted', 'accept', 'it was accepted as genuine', 'authenticated'],
           ['not accepted', 'rejected', 'unacceptable', 'fake']),
 'l5t2a': (['breath', 'breathing', 'room noise', 'reverb', 'noise floor'],
           ['room', 'a room', 'bathroom', 'breadth']),
 'l5t4b': (['liveness'], ['live', 'deliveness']),
 'l5t5a': (['liveness detection', 'multi-factor', 'MFA', '2FA', 'second factor', 'multi factor auth'],
           ['multi', 'factor', 'more security']),
 'l6t1b': (['api key', 'API-key', 'apikey', 'api keys'], ['key', 'therapy keyboard']),
 'l6t2a': (['ip', 'source ip', 'IP address', 'client IP'],
           ['source', 'tip', 'description', 'equipment', 'script']),
 'l6t2b': (['429', 'http 429', '429 too many requests'], ['4290', '1429', '42']),
 'l6t3a': (['1200', '1,200', '1100', '~1,150', 'about 1200'], ['21500', '12000', '11', '1300', 'a1200']),
 'l6t4a': (['cadence', 'round-robin', 'round robin', 'key rotation', 'rotating keys'],
           ['signature', 'rotation', 'keys']),
 'l6t4b': (['800', '~800', 'about 800 keys'], ['8000', '1800', '80']),
 'l6t5a': (['ip', 'IP address', 'subnet', 'device fingerprint', 'behavioral', 'behaviour'],
           ['tip', 'description', 'equipment', 'source', 'key']),
 'l7t1b': (['reviews', 'review count', 'star rating', 'ratings'], ['preview', "reviewer's mood"]),
 'l7t2a': (['ip', 'ip address', 'IPs', 'an IP'], ['tip', 'ship', 'description']),
 'l7t4a': (['verified purchase', 'verified-purchase', 'purchase flag'],
           ['purchase', 'verified', 'unverified']),
 'l7t5a': (['cohort', 'ip', 'ip clustering', 'review velocity', 'device'],
           ['tip', 'description', 'equipment', 'time']),
 'l8t2a': (['40000', '40,000', '40k', 'about 40,000 queries'], ['140,000', '400000', '4000', '40']),
 'l8t3b': (['averaged', 'the averaged estimate', 'average'], ['single', 'coverage']),
 'l8t4a': (['cumulative', 'total', 'a cumulative cap'], ['per-query', 'cum']),
 'l8t5a': (['privacy budget', 'epsilon', 'the budget', 'cumulative epsilon'], ['bud', 'eps']),
 'l9t2a': (['video', 'replay', 'video replay'], ['print', 'photo', 'videos of cats']),
 'l9t2b': (['dpi', 'resolution', 'print resolution', 'DPI'], ['gloss', 'opinion', 'resolutions are fun']),
 'l9t4a': (['infrared', 'IR', 'depth and infrared', 'nir'], ['their', 'first', 'fair']),
 'l9t5a': (['depth', '3D', '3d depth', 'depth sensing', 'multimodal', 'multi-modal'],
           ['depths of the sea', '2d', 'modal']),
 'l10t1a': (['dispatch', 'dispatched', 'at dispatch'], ['dispatcher', 'delivery']),
 'l10t4a': (['delivery', 'delivered', 'confirmed delivery'], ['deliverable', 'dispatch']),
 'l10t5a': (['delivery', 'delivered'], ['deliverable', 'dispatch'])}


def _ok(qid, text):
    return any(re.search(p, text.lower()) for p in TEXT_QUESTIONS[qid]["patterns"])


@pytest.mark.parametrize("qid", sorted(CASES))
def test_pattern_accepts_good_and_rejects_loose_answers(qid):
    good, bad = CASES[qid]
    for text in good:
        assert _ok(qid, text), f"{qid}: should accept {text!r}"
    for text in bad:
        assert not _ok(qid, text), f"{qid}: should reject {text!r}"


GENERIC_JUNK = ["", "idk", "text", "long", "large", "system", "room", "purchase", "multi", "source",
                "description of their first tip", "equipment script", "the quick brown fox",
                "post office", "patient care", "answer"]


def test_no_free_text_question_accepts_generic_junk():
    # a handful of questions are legitimately satisfied by one common word (their own answer);
    # none of those words is in the junk list above.
    for qid, q in TEXT_QUESTIONS.items():
        for junk in GENERIC_JUNK:
            if junk in ("post office",) and qid == "l1t4b":
                continue                       # "post" is the real answer there; whole word is allowed
            if junk == "patient care" and qid == "l2t1a":
                continue                       # contains the real answer "patient"
            if junk == "system" and qid == "l5t1b":
                continue
            assert not _ok(qid, junk), f"{qid} accepts junk {junk!r}"


def test_numeric_answers_are_anchored():
    for qid, bad in {"l4t4a": "18,000", "l8t2a": "140,000", "l6t3a": "21500", "l6t4b": "8000",
                     "l2t2a": "round 60", "l6t2b": "4290"}.items():
        assert not _ok(qid, bad), (qid, bad)


# ------------------------------------------------------------------ 3. flags are never printed
@pytest.mark.parametrize("lab", ["lab6", "lab7", "lab8", "lab9", "lab10"])
def test_terminal_never_prints_flag_labs_6_to_10(learner, lab, monkeypatch):
    seen = []
    real_term = learner.term

    def spy(l, cmd):
        out = real_term(l, cmd)
        seen.append(out)
        return out
    monkeypatch.setattr(learner, "term", spy)
    flag = storyline_for(lab).static_flag(lab)
    res = solve_lab(learner, lab, appmod.load_lab(lab))
    blob = "\n".join(seen)
    assert "HACKAI{" not in blob and flag not in blob
    assert "exploit confirmed" in blob                    # the proof of exploit is still shown
    assert res["flag"] == flag                            # ...and the room still releases the flag


# ------------------------------------------------------------------ 4. verify-fix (remediation)
EXPLOIT_FIRST = {"lab1": "reproduced_disputed_result", "lab2": "reconstructed_attack", "lab3": "tested_html",
                 "lab4": "reproduced_leak", "lab5": "identified_misconfig",
                 "lab6": "reproduced_scrape", "lab7": "reproduced_signal_shift",
                 "lab8": "reproduced_reidentification", "lab9": "reproduced_spoof",
                 "lab10": "reproduced_exploit"}
EXPECT = {"lab1": ["2 attacked, credentials still attached", "MISMATCH", "tampering with credentials attached is now provable"],
          "lab2": ["trimmed mean, poisoned", "84.1%", "no longer breaks the rare-condition model"],
          "lab3": ["0.778 ALLOW ->   0.933 BLOCK", "0 of 300", "random padding (50 words)           0.763 ALLOW ->   0.763 ALLOW"],
          "lab4": ["0.934   refuses", "0.842 at 14,060", "no longer overrides the rules"],
          "lab5": ["disputed call         : similarity 95%  liveness 14%  REJECTED", "noise 0.03 ", "noise >= 0.03"],
          "lab6": ["keys registered            : 25 of 800", "distinct outputs collected : 300", "coverage                   : 25%"],
          "lab7": ["discarded as inauthentic : 215 of 309", "rank: #42 -> #42"],
          "lab8": ["queries served before the block : 5", "recovered target value          : 155.2"],
          "lab9": ["depth            : 0.08", "granted          : False", "live face still admitted: True"],
          "lab10": ["honest policy : reward=0.70", "gaming policy : reward=0.29"]}
ANSWER = {"lab1": ("l1t5b", "mismatch"), "lab2": ("l2t5b", "84"), "lab3": ("l3t5b", "random padding"),
          "lab4": ("l4t5b", "0.842"), "lab5": ("l5t5b", "0.03"),
          "lab6": ("l6t5b", "300"), "lab7": ("l7t5b", "215"), "lab8": ("l8t5b", "155.2"),
          "lab9": ("l9t5b", "0.08"), "lab10": ("l10t5b", "0.70")}


@pytest.mark.parametrize("lab", sorted(EXPLOIT_FIRST))
def test_verify_fix_requires_the_exploit_first(learner, lab):
    out = learner.term(lab, "verify-fix")
    assert "exploit works first" in out
    assert "verified_fix" not in learner.progress(lab)["actions"]


@pytest.mark.parametrize("lab", sorted(EXPLOIT_FIRST))
def test_verify_fix_proves_the_fix_with_real_numbers(learner, lab):
    from tests.walkthrough import command_for
    action = EXPLOIT_FIRST[lab]
    mod = appmod.load_lab(lab)
    from tests.walkthrough import topo_actions
    for a in topo_actions(mod, {action}):
        if a in ("analyst_interpretation_correct", "red_herring_rejected"):
            continue
        cmd = command_for(lab, a)
        for _ in range(4):
            if a in learner.progress(lab)["actions"]:
                break
            cmd(learner, lab) if callable(cmd) else learner.term(lab, cmd)
    out = learner.term(lab, "verify-fix")
    for fragment in EXPECT[lab]:
        assert fragment in out, (lab, fragment, out)
    assert "NOT enough" not in out and "HACKAI{" not in out
    assert "verified_fix" in learner.progress(lab)["actions"]


@pytest.mark.parametrize("lab", sorted(ANSWER))
def test_remediation_question_is_gated_on_verify_fix(learner, lab):
    qid, ans = ANSWER[lab]
    res = learner.answer(lab, qid, ans)
    assert res.get("correct") is False and "hands-on" in res["message"]


def test_every_lab_help_lists_verify_fix(learner):
    for lab in EXPLOIT_FIRST:
        assert "verify-fix" in learner.term(lab, "help")


# ------------------------------------------------------------------ 5. the fixes themselves (labs 1-5 engines)
import sys  # noqa: E402
sys.path.insert(0, "sandboxes1")
import lab1_engine as E1  # noqa: E402
import lab3_engine as E3  # noqa: E402
import lab4_engine as E4  # noqa: E402


def test_lab1_manifest_distinguishes_absent_valid_mismatch_forged():
    img = E1.embed_watermark(E1.generate_clean_image(seed=5))
    mf = E1.sign_manifest(img)
    assert E1.check_manifest(img, mf)[0] == "valid"
    assert E1.check_manifest(E1.jpeg_compress(img, 30), mf)[0] == "mismatch"
    assert E1.check_manifest(img, None)[0] == "absent"
    assert E1.check_manifest(img, dict(mf, claim="generated-by=someone-else"))[0] == "forged"
    assert E1.check_manifest(img, dict(mf, pixel_sha256="0" * 64))[0] == "forged"      # hash edit breaks the signature


def test_lab3_normalize_restores_every_character_trick_but_not_padding():
    base = E3.base_phish_email()
    known = E3.score(base)[0]
    for mutate in (E3.apply_homoglyph, E3.apply_zwsp, E3.apply_hidden_html,
                   lambda t: E3.apply_zwsp(E3.apply_homoglyph(t)),
                   lambda t: E3.apply_hidden_html(E3.apply_zwsp(E3.apply_homoglyph(t)))):
        conf, blocked = E3.verdict_normalized(mutate(base))
        assert blocked and abs(conf - known) < 1e-9
    assert E3.verdict_normalized(E3.apply_random_padding(base))[1] is False        # honest limit of the fix
    assert E3.false_positive_count() == 0


def test_lab4_reinjection_is_judged_by_its_worst_moment():
    assert E4.worst_case_attention(2000)[0] > E4.ATTN_FLOOR + 0.5
    assert E4.worst_case_attention(8000)[0] < E4.ATTN_FLOOR + 0.01                   # too rare: floor is reached
    assert E4.worst_case_attention(12000)[0] < E4.ATTN_FLOOR                         # far too rare: still exploitable
    plain = E4.attention_on_system_prompt(8180)
    assert plain < E4.ATTN_FLOOR <= E4.attention_with_reinjection(8180, 2000)[0]


def test_lab4_verify_fix_flags_a_too_rare_interval(learner):
    from tests.walkthrough import command_for, topo_actions
    mod = appmod.load_lab("lab4")
    for a in topo_actions(mod, {"reproduced_leak"}):
        cmd = command_for("lab4", a)
        cmd(learner, "lab4") if callable(cmd) else learner.term("lab4", cmd)
    out = learner.term("lab4", "verify-fix --every 12000")
    assert "NOT enough" in out and "BELOW" in out


def test_lab5_liveness_gate_stops_the_incident_but_not_an_adapted_clone(learner):
    out = learner.term("lab5", "verify-fix")
    assert "exploit works first" in out
    from tests.walkthrough import command_for, topo_actions
    for a in topo_actions(appmod.load_lab("lab5"), {"identified_misconfig"}):
        learner.term("lab5", command_for("lab5", a))
    out = learner.term("lab5", "verify-fix")
    assert "genuine CEO reference : similarity 100%  liveness 88%  ACCEPTED" in out
    assert "noise 0.02    similarity   98%   liveness   35%   REJECTED" in out
    assert "noise 0.03    similarity   99%   liveness   52%   ACCEPTED" in out
