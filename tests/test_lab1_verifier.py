import pytest

import sandbox

E1 = sandbox.E1


@pytest.fixture
def lab1(learner):
    learner.term("lab1", "artforge-gen")
    return learner


@pytest.mark.parametrize("conf,text,expect,absent", [
    (0.75, "Af-MIC-54?1", "NOT VERIFIED", "result      : WATERMARK DETECTED"),   # the reported bug
    (0.99, E1.LICENSE_ID, "result      : WATERMARK DETECTED", "NOT"),
    (0.99, "AF-LIC-4472", "NOT VERIFIED", "result      : WATERMARK DETECTED"),   # wrong but clean-looking ID
    (0.40, None, "NOT DETECTED", "VERIFIED (payload"),
    (0.55, E1.LICENSE_ID, "result      : WATERMARK DETECTED", "NOT"),          # boundary is inclusive
])
def test_detection_requires_confidence_and_exact_id(lab1, monkeypatch, conf, text, expect, absent):
    monkeypatch.setattr(sandbox.E1, "verify_watermark", lambda arr: (conf, text))
    out = lab1.term("lab1", "wm-verify baseline.png")
    assert expect in out and absent not in out


def test_corrupt_payload_counts_as_reproducing_the_disputed_result(lab1, monkeypatch):
    lab1.term("lab1", "wm-verify baseline.png")
    lab1.term("lab1", "view disputed_batch/img_014.png")
    lab1.term("lab1", "wm-verify disputed_batch/img_014.png")
    lab1.term("lab1", "wm-compare baseline.png disputed_batch/img_014.png")
    lab1.term("lab1", "transform baseline.png --compress 30")
    monkeypatch.setattr(sandbox.E1, "verify_watermark", lambda arr: (0.75, "Af-MIC-54?1"))
    lab1.term("lab1", "wm-verify t1.png")
    assert "reproduced_disputed_result" in lab1.progress("lab1")["actions"]
