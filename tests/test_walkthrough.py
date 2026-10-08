import pytest

import app as appmod
from storylines import storyline_for
from walkthrough import solve_lab

LABS = [f"lab{i}" for i in range(1, 11)]


@pytest.mark.parametrize("lab", LABS)
def test_every_room_can_be_completed_and_flag_captured(learner, lab):
    mod = appmod.load_lab(lab)
    res = solve_lab(learner, lab, mod)
    assert res["room_done"] is True
    assert res["flag"], f"{lab}: no flag returned after completing all questions"
    assert res["flag"] == storyline_for(lab).static_flag(lab)


@pytest.mark.parametrize("lab", LABS)
def test_flag_is_locked_until_hands_on_steps_are_done(learner, lab):
    story = storyline_for(lab)
    q = next(q for q in story.all_questions(lab) if q["type"] == "text" and q.get("requires"))
    res = learner.answer(lab, q["id"], "anything")
    assert res["ok"] is False and res.get("flag") is None
    page = learner.c.get(f"/lab/{lab}/room").get_data(as_text=True)
    assert story.static_flag(lab) not in page
