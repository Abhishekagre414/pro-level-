import json
import threading

import app as appmod
from store import MAX_TEXT, ProgressStore


def test_progress_survives_restart(tmp_path):
    path = str(tmp_path / "p.db")
    s1 = ProgressStore(path)
    p = s1.load("a" * 32, "lab1")
    p["actions"].append("generated_baseline")
    p["answers"]["q1"] = True
    p["sandbox"]["images"] = object()                 # live state is intentionally not persisted
    assert s1.save("a" * 32, "lab1", p)
    s1.close()

    s2 = ProgressStore(path)                           # "server restart"
    q = s2.load("a" * 32, "lab1")
    assert q["actions"] == ["generated_baseline"] and q["answers"] == {"q1": True}
    assert q["sandbox"] == {}


def test_unchanged_progress_is_not_rewritten():
    s = ProgressStore(":memory:")
    p = s.load("b" * 32, "lab2")
    snap = s.snapshot(p)
    assert s.save("b" * 32, "lab2", p, before=snap) is False
    p["actions"].append("x")
    assert s.save("b" * 32, "lab2", p, before=snap) is True


def test_sessions_are_isolated():
    s = ProgressStore(":memory:")
    a, b = s.load("a" * 32, "lab1"), s.load("b" * 32, "lab1")
    a["actions"].append("only_a")
    s.save("a" * 32, "lab1", a)
    assert s.load("b" * 32, "lab1")["actions"] == []
    assert b["sandbox"] is not a["sandbox"]


def test_corrupt_row_does_not_crash(tmp_path):
    path = str(tmp_path / "p.db")
    s = ProgressStore(path)
    s._conn.execute("INSERT INTO progress VALUES (?,?,?,?)", ("c" * 32, "lab1", "{not json", 9e12))
    assert s.load("c" * 32, "lab1")["actions"] == []


def test_stored_text_is_capped():
    s = ProgressStore(":memory:")
    p = s.load("d" * 32, "lab1")
    p["report"] = "x" * (MAX_TEXT * 5)
    s.save("d" * 32, "lab1", p)
    assert len(json.loads(s.snapshot(s.load("d" * 32, "lab1")))["report"]) <= MAX_TEXT


def test_old_sessions_are_purged():
    s = ProgressStore(":memory:")
    s._conn.execute("INSERT INTO progress VALUES (?,?,?,?)", ("e" * 32, "lab1", "{}", 1.0))
    s.purge()
    assert s._conn.execute("SELECT COUNT(*) FROM progress").fetchone()[0] == 0


def test_sandbox_cache_is_bounded(monkeypatch):
    import store
    monkeypatch.setattr(store, "SANDBOX_CACHE_MAX", 5)
    s = ProgressStore(":memory:")
    for i in range(20):
        s.load(f"{i:032x}", "lab1")
    assert len(s._sandboxes) <= 5


def test_reset_lab_and_all():
    s = ProgressStore(":memory:")
    for lab in ("lab1", "lab2"):
        p = s.load("f" * 32, lab)
        p["actions"].append("x")
        s.save("f" * 32, lab, p)
    s.reset_lab("f" * 32, "lab1")
    assert s.load("f" * 32, "lab1")["actions"] == [] and s.load("f" * 32, "lab2")["actions"] == ["x"]
    s.reset_all("f" * 32)
    assert s.load("f" * 32, "lab2")["actions"] == []


def test_app_progress_survives_store_restart(learner):
    learner.term("lab1", "artforge-gen")
    sid, old = learner.sid, appmod.STORE
    appmod.STORE = ProgressStore(old.path)             # simulate a process restart
    try:
        assert "generated_baseline" in appmod.STORE.load(sid, "lab1")["actions"]
    finally:
        appmod.STORE.close()
        appmod.STORE = old


def test_concurrent_learners_do_not_corrupt_each_other():
    errors, results = [], {}

    def run(i):
        try:
            from conftest import Learner
            L = Learner(appmod.app.test_client())
            L.term("lab4", "pad 100")
            L.term("lab4", 'chat "hi"')
            results[i] = L.progress("lab4")["sandbox"]["chat"]["tokens"]
        except Exception as e:                            # pragma: no cover
            errors.append(e)
    threads = [threading.Thread(target=run, args=(i,)) for i in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert not errors and len(set(results.values())) == 1
