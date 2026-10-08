import os
import sys
import tempfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Isolated instance dir + DB so tests never touch real progress or the real secret key.
_TMP = tempfile.mkdtemp(prefix="labdemo-tests-")
os.environ["LABDEMO_INSTANCE"] = _TMP
os.environ["LABDEMO_DB"] = os.path.join(_TMP, "test.db")
os.environ["LABDEMO_SEQUENTIAL_UNLOCK"] = "0"   # the legacy suite walks labs in any order; test_unlock.py opts in

import app as appmod  # noqa: E402
import security  # noqa: E402


class Learner:
    """A browser-like test client that handles the CSRF token for us."""

    def __init__(self, client):
        self.c = client
        self.c.get("/")                      # establishes the session + CSRF token

    @property
    def token(self):
        with self.c.session_transaction() as s:
            return s["csrf"]

    @property
    def sid(self):
        with self.c.session_transaction() as s:
            return s.get("sid")

    def post_json(self, url, body):
        return self.c.post(url, json=body, headers={"X-CSRF-Token": self.token})

    def term(self, lab, cmd):
        r = self.post_json(f"/lab/{lab}/term", {"cmd": cmd})
        assert r.status_code == 200, (cmd, r.status_code, r.data[:200])
        return r.get_json()["output"]

    def answer(self, lab, qid, text):
        r = self.post_json(f"/lab/{lab}/answer", {"qid": qid, "answer": text})
        assert r.status_code in (200, 400), r.status_code
        return r.get_json()

    def post_form(self, url, data):
        return self.c.post(url, data=dict(data, csrf_token=self.token))

    def progress(self, lab):
        return appmod.STORE.load(self.sid, lab)


@pytest.fixture
def learner():
    security.limiter._hits.clear()
    appmod.app.config.update(TESTING=True)
    return Learner(appmod.app.test_client())


@pytest.fixture(autouse=True)
def _clear_limits():
    security.limiter._hits.clear()
    yield
