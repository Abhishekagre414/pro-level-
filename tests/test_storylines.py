"""The storyline registry is the single source of truth for which lab lives where."""
import pytest

import app as appmod
from storylines import LAB_ORDER, STORYLINES, Storyline, storyline_for

LABS = [f"lab{i}" for i in range(1, 11)]


def test_registry_covers_every_lab_exactly_once_in_order():
    assert list(LAB_ORDER) == LABS
    assert set(LAB_ORDER) == set(appmod.LAB_META)
    assert sum(len(s.lab_ids) for s in STORYLINES) == len(LAB_ORDER)


def test_unknown_lab_is_a_keyerror():
    with pytest.raises(KeyError):
        storyline_for("lab99")


def test_mismatched_rooms_and_sandbox_are_rejected():
    with pytest.raises(ValueError, match="disagree"):
        Storyline("bad", {"lab1": {}}, {"lab2": {}}, "x")


def test_flags_are_unique_across_labs():
    flags = [storyline_for(lab).static_flag(lab) for lab in LABS]
    assert len(set(flags)) == len(flags)


@pytest.mark.parametrize("lab", LABS)
def test_question_ids_unique_and_choice_sources_resolve(lab):
    mod = appmod.load_lab(lab)
    qs = storyline_for(lab).all_questions(lab)
    ids = [q["id"] for q in qs]
    assert len(ids) == len(set(ids)), f"{lab}: duplicate question ids"
    for q in qs:
        assert q["points"] > 0
        if q["type"] == "choice":
            src = q["source"]
            assert src in ("analyst", "decision2"), (lab, q["id"], src)
            obj = mod.ANALYST_INTERPRETATION if src == "analyst" else getattr(mod, "DECISION_POINT_2", None)
            assert obj and obj["correct"] in obj["options"], (lab, q["id"])
        else:
            assert q["patterns"], (lab, q["id"])


@pytest.mark.parametrize("lab,persona", [("lab1", "priya"), ("lab5", "priya"), ("lab6", "diya"), ("lab10", "diya")])
def test_whoami_comes_from_the_owning_storyline(lab, persona):
    mod = appmod.load_lab(lab)
    out = storyline_for(lab).execute(lab, mod, {"actions": [], "sandbox": {}}, "whoami")
    assert out.startswith(persona)
