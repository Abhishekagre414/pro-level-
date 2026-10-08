# -*- coding: utf-8 -*-
"""Builders shared by rooms.py (labs 1-5) and rooms2.py (labs 6-10); see storylines.py."""


def Q(qid, text, patterns, requires, hint, pts=10):
    """A free-text question graded by regex `patterns` once `requires` actions exist."""
    return {"id": qid, "text": text, "patterns": patterns, "requires": requires, "hint": hint,
            "points": pts, "type": "text"}


def C(qid, source, requires, pts=10):
    """A multiple-choice question whose options come from the lab module (`source`)."""
    return {"id": qid, "type": "choice", "source": source, "requires": requires, "points": pts}


def A(requires, pts=10):
    """The analyst-interpretation multiple-choice question (one per lab in storyline 1)."""
    return C("analyst", "analyst", requires, pts)


def T(tid, title, story, steps, questions):
    return {"id": tid, "title": title, "story": story, "steps": steps, "questions": questions}


def all_questions(rooms, lab_id):
    return [q for t in rooms[lab_id]["tasks"] for q in t["questions"]]
