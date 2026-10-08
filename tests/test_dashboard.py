"""The dashboard shows two storylines with five labs each."""
import re

import app as appmod
from storylines import STORYLINES


def test_each_storyline_has_five_labs():
    assert len(STORYLINES) == 2
    assert [len(s.lab_ids) for s in STORYLINES] == [5, 5]


def test_dashboard_renders_two_sections_of_five_cards():
    html = appmod.app.test_client().get("/").data.decode()
    sections = html.split('<section class="storyline"')[1:]
    assert len(sections) == 2
    for section, story in zip(sections, STORYLINES):
        assert section.count('class="case-card"') == 5
        for lab_id in story.lab_ids:
            assert f"/lab/{lab_id}" in section
    assert "The MIRAGE Thread" in sections[0] and "Red Herring Rejected" in sections[1]


def test_sidebar_is_grouped_by_storyline_on_every_page():
    client = appmod.app.test_client()
    for path in ("/", "/lab/lab1", "/lab/lab6"):
        assert len(re.findall(r'class="case-group"', client.get(path).data.decode())) == 2


def test_completed_badge_and_points_counter_start_at_zero():
    html = appmod.app.test_client().get("/").data.decode()
    assert "0 / 5 labs completed" in html and "Your points: <b>0 / 1000</b>" in html and "Completed" not in html


def test_every_lab_step_uses_the_dark_room_design_but_the_dashboard_does_not():
    client = appmod.app.test_client()
    assert "lab-dark" not in client.get("/").data.decode()
    for step in ("", "/hypothesis", "/room", "/knowledge", "/evidence", "/report", "/outcome"):
        html = client.get(f"/lab/lab1{step}").data.decode()
        assert 'class="content lab-dark"' in html or 'class="content lab-dark' in html, step


def test_room_has_briefing_start_lab_timer_and_navigation():
    html = appmod.app.test_client().get("/lab/lab1/room").data.decode()
    # the briefing is its own page (first step); it is not repeated on the room
    assert 'id="task-briefing"' not in html and "Initial Alert" not in html
    # start lab + timer + navigation card
    assert 'id="lab-toggle"' in html and 'id="lab-time"' in html and 'class="labnav-steps"' in html
    assert html.count('class="labnav-pill') == 7
    # terminal is locked until the lab is started; the old top stepper is replaced by the card
    assert 'id="term-in"' in html and "disabled" in html.split('id="term-in"')[1][:120]
    assert 'class="progress-steps' not in html
    # navigation is plain links: nothing is locked
    assert "is-locked" not in html and 'aria-disabled' not in html
    assert "/lab/lab1/knowledge" in html                 # reachable from the pills
    # the Back / Next buttons duplicated the pills, so they are gone
    assert 'labnav-buttons' not in html and 'id="nav-next"' not in html


def test_other_steps_show_the_same_navigation_pills_as_links():
    client = appmod.app.test_client()
    client.get("/lab/lab1/room")                      # reaching the room finishes Briefing + Hypothesis
    html = client.get("/lab/lab1/hypothesis").data.decode()
    assert 'class="progress-steps labnav-steps"' in html and html.count('class="labnav-pill') == 7
    assert html.count("<a class=\"labnav-pill") == 7        # every step is a link


def test_opening_a_lab_starts_at_the_case_briefing():
    client = appmod.app.test_client()
    home = client.get("/").data.decode()
    assert 'href="/lab/lab1"' in home and '/lab/lab1/room"' not in home
    side = client.get("/lab/lab6/room").data.decode()
    assert 'href="/lab/lab2"' in side                  # sidebar links open the briefing too
    assert "Initial Alert" in client.get("/lab/lab1").data.decode()


def test_start_lab_panel_sits_on_the_task_side_and_each_control_appears_once():
    html = appmod.app.test_client().get("/lab/lab1/room").data.decode()
    left = html.split('<section class="tasks">')[1].split('<aside class="side">')[0]
    right = html.split('<aside class="side">')[1]
    assert 'id="labbar"' in left and 'id="lab-toggle"' in left and 'class="labnav-steps"' in left
    assert 'id="labbar"' not in right and 'class="attackbox"' in right
    assert html.count('id="lab-toggle"') == 1 and html.count('class="labnav-steps"') == 1
    assert html.count('class="labnav-pill') == 7                 # one pill per step, no second set of buttons
