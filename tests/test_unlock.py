"""Cases open one after another inside each storyline; the developer credit is shown."""
import pytest

import app as appmod
import security
from walkthrough import solve_lab


def complete_lab(learner, lab):
    """Do every part of a lab the way a learner would: briefing -> ... -> Case Closed."""
    security.limiter._hits.clear()
    mod, c = appmod.load_lab(lab), learner.c
    c.get(f"/lab/{lab}")
    learner.post_form(f"/lab/{lab}/hypothesis", {"choice": mod.HYPOTHESIS["best_supported"]})
    solve_lab(learner, lab, mod)
    learner.post_form(f"/lab/{lab}/knowledge", {f"q{i}": q["correct"] for i, q in enumerate(mod.KNOWLEDGE_CHECKS)})
    learner.post_form(f"/lab/{lab}/evidence", {k: mod.ATTACK_CHAIN_LINKS[k]["correct"] for k in mod.ATTACK_CHAIN_SLOT_ORDER})
    learner.post_form(f"/lab/{lab}/report", {"report_text": "Draft report."})
    return c.get(f"/lab/{lab}/outcome").data.decode()


@pytest.fixture(autouse=True)
def _sequential(monkeypatch):
    monkeypatch.setenv("LABDEMO_SEQUENTIAL_UNLOCK", "1")


def test_only_the_first_case_of_each_storyline_is_open_at_the_start(learner):
    c = learner.c
    assert c.get("/lab/lab1").status_code == 200 and c.get("/lab/lab6").status_code == 200
    for locked in ("lab2", "lab5", "lab7", "lab10"):
        r = c.get(f"/lab/{locked}")
        assert r.status_code == 302 and r.headers["Location"].endswith("/"), locked
        assert c.get(f"/lab/{locked}/room").status_code == 302


def test_locked_lab_api_is_refused_not_just_hidden(learner):
    r = learner.c.post("/lab/lab2/term", json={"cmd": "help"}, headers={"X-CSRF-Token": learner.token})
    assert r.status_code == 403 and r.get_json()["error"] == "locked"


def test_dashboard_shows_locked_cases_and_sidebar_lock(learner):
    html = learner.c.get("/").data.decode()
    assert html.count('class="case-card locked"') == 8
    assert "Finish case 01" in html and "Finish case 06" in html
    assert html.count('class="case-link locked"') == 8


def test_completing_every_part_opens_the_next_case_only(learner):
    complete_lab(learner, "lab1")
    c = learner.c
    assert c.get("/lab/lab2").status_code == 200          # opened
    assert c.get("/lab/lab3").status_code == 302          # still locked
    assert c.get("/lab/lab7").status_code == 302          # other storyline is independent
    html = c.get("/").data.decode()
    assert html.count('class="case-card locked"') == 7
    assert "Completed &middot; +100 pts" in html and "1 / 5 labs completed &middot; 100 points" in html
    assert "Your points: <b>100 / 1000</b>" in html


def test_capturing_only_the_flag_does_not_complete_the_lab(learner):
    solve_lab(learner, "lab1", appmod.load_lab("lab1"))
    assert learner.c.get("/lab/lab2").status_code == 302          # still locked: other parts not done
    outcome = learner.c.get("/lab/lab1/outcome").data.decode()
    assert "Complete every part to earn 100 points" in outcome and "complete-modal" not in outcome
    assert "Knowledge Check</a>" in outcome                        # the checklist links to what is missing


def test_completion_popup_has_dashboard_and_next_lab_buttons(learner):
    outcome = complete_lab(learner, "lab1")
    modal = outcome.split('id="complete-modal"')[1].split("</div>\n</div>")[0]
    assert "Lab completed successfully!" in modal and "+100 points" in modal and "Abhishek A" in modal
    assert 'href="/"' in modal and "Go to Dashboard" in modal
    assert 'href="/lab/lab2"' in modal and "Next Lab" in modal
    assert "Lab completed</b>" in outcome                          # banner stays after the pop-up is closed


def test_next_lab_from_the_end_of_storyline_one_is_the_first_lab_of_storyline_two(learner):
    for lab in ("lab1", "lab2", "lab3", "lab4"):
        complete_lab(learner, lab)
    outcome = complete_lab(learner, "lab5")
    assert 'href="/lab/lab6"' in outcome.split('id="complete-modal"')[1]


def test_last_lab_pop_up_has_no_next_button(learner):
    for lab in ("lab6", "lab7", "lab8", "lab9"):
        complete_lab(learner, lab)
    modal = complete_lab(learner, "lab10").split('id="complete-modal"')[1]
    assert "Go to Dashboard" in modal and "Next Lab" not in modal


def test_unfinished_outcome_does_not_offer_the_next_lab(learner):
    outcome = learner.c.get("/lab/lab1/outcome").data.decode()
    assert "Next Lab" not in outcome and "to unlock the next one" in outcome


def test_reset_starts_the_lab_again_but_keeps_points_and_the_unlocked_next_lab(learner):
    complete_lab(learner, "lab1")
    r = learner.post_form("/reset/lab1", {})
    assert r.status_code == 302 and r.headers["Location"].endswith("/lab/lab1")      # starts again at the briefing
    c = learner.c
    assert "Your points: <b>100 / 1000</b>" in c.get("/").data.decode()             # earned points are kept
    assert c.get("/lab/lab2").status_code == 200                                    # next lab stays unlocked
    room = c.get("/lab/lab1/room").data.decode()
    assert 'task-t1" ' in room and 'class="task done"' not in room                  # but the run itself is fresh
    assert 'id="flag-box" hidden' in room


def test_a_lab_can_be_played_many_times_and_points_are_only_awarded_once(learner):
    complete_lab(learner, "lab1")
    for _ in range(2):
        learner.post_form("/reset/lab1", {})
        outcome = complete_lab(learner, "lab1")
        assert "Lab completed successfully!" in outcome            # the pop-up appears for each finished run
    assert "Your points: <b>100 / 1000</b>" in learner.c.get("/").data.decode()   # never 200 or 300


def test_replay_in_progress_has_no_popup_and_explains_points(learner):
    complete_lab(learner, "lab1")
    learner.post_form("/reset/lab1", {})
    outcome = learner.c.get("/lab/lab1/outcome").data.decode()
    assert "complete-modal" not in outcome and "Already completed" in outcome
    assert "replaying doesn" in outcome and "Next Lab" in outcome  # next lab is still offered


def test_room_has_a_reset_lab_button_with_confirmation(learner):
    html = learner.c.get("/lab/lab1/room").data.decode()
    left = html.split('<section class="tasks">')[1].split('<aside class="side">')[0]
    assert "Reset Lab" in left and 'action="/reset/lab1"' in left and 'data-confirm="Reset this lab' in left
    assert 'data-run="0"' in left
    learner.post_form("/reset/lab1", {})
    assert 'data-run="1"' in learner.c.get("/lab/lab1/room").data.decode()   # the browser timer restarts


def test_reset_all_still_clears_everything(learner):
    complete_lab(learner, "lab1")
    learner.post_form("/reset-all", {})
    html = learner.c.get("/").data.decode()
    assert "Your points: <b>0 / 1000</b>" in html and html.count('class="case-card locked"') == 8


def test_room_shows_task_points_out_of_100(learner):
    html = learner.c.get("/lab/lab1/room").data.decode()
    assert '<span id="pts">0</span>/100 <small>task points</small>' in html


def test_developer_credit_everywhere(learner):
    assert "Lab developer: <b>Abhishek A</b>" in learner.c.get("/").data.decode()
    for path in ("/lab/lab1", "/lab/lab1/room", "/lab/lab1/outcome"):
        html = learner.c.get(path).data.decode()
        assert "Lab developer: Abhishek A" in html and "Abhishek A" in html.split("dev-side")[1]
    assert "Lab developer</span>Abhishek A" in learner.c.get("/lab/lab1").data.decode()   # briefing facts


def test_unlock_can_be_switched_off(monkeypatch, learner):
    monkeypatch.setenv("LABDEMO_SEQUENTIAL_UNLOCK", "0")
    assert learner.c.get("/lab/lab5").status_code == 200
