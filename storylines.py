# -*- coding: utf-8 -*-
"""
One registry for both storylines.

Storyline 1 (labs 1-5, `rooms.py` + `sandbox.py`) and storyline 2 (labs 6-10,
`rooms2.py` + `sandbox2.py`) are different *content* with the same *shape*:
a table of rooms (tasks, questions, flag) and a table of terminal commands.
This module is the only place that knows which lab belongs to which
storyline, so `app.py` just asks `storyline_for(lab_id)` instead of
branching on a hard-coded set of lab ids.

Adding a storyline = add its rooms/sandbox modules and append one entry to
STORYLINES. Import-time checks fail fast if the two tables disagree.
"""
from dataclasses import dataclass

import rooms
import rooms2
import sandbox
import sandbox2
from rooms_common import all_questions as _all_questions
from sandbox_common import execute as _execute


@dataclass(frozen=True)
class Storyline:
    name: str
    rooms: dict      # lab_id -> {"flag": str, "tasks": [...]}
    labs: dict       # lab_id -> {"prompt": str, "help": str, "cmds": {name: handler}}
    whoami: str      # what `whoami` prints in this storyline's terminals

    def __post_init__(self):
        if set(self.rooms) != set(self.labs):
            raise ValueError(f"{self.name}: rooms and sandbox labs disagree: "
                             f"{sorted(set(self.rooms) ^ set(self.labs))}")

    @property
    def lab_ids(self):
        return tuple(self.rooms)

    def static_flag(self, lab_id):
        return self.rooms[lab_id]["flag"]

    def prompt(self, lab_id):
        return self.labs[lab_id]["prompt"]

    def all_questions(self, lab_id):
        return _all_questions(self.rooms, lab_id)

    def execute(self, lab_id, mod, prog, line):
        return _execute(self.labs, self.whoami, lab_id, mod, prog, line)


STORYLINES = (
    Storyline("storyline-1", rooms.ROOMS, sandbox.LABS, sandbox.WHOAMI),
    Storyline("storyline-2", rooms2.ROOMS, sandbox2.LABS, sandbox2.WHOAMI),
)

LAB_ORDER = tuple(lab_id for s in STORYLINES for lab_id in s.lab_ids)

_BY_LAB = {}
for _s in STORYLINES:
    for _lab in _s.lab_ids:
        if _lab in _BY_LAB:
            raise ValueError(f"{_lab} is claimed by two storylines")
        _BY_LAB[_lab] = _s


def storyline_for(lab_id):
    """The Storyline that owns `lab_id` (KeyError for an unknown lab)."""
    return _BY_LAB[lab_id]
