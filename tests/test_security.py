import os
import re
import time

import pytest

import app as appmod
import security
from storylines import storyline_for

LAB = "lab1"


# ---------------------------------------------------------------- secret key / cookies
def test_secret_key_not_hardcoded_and_persisted():
    src = open(os.path.join(appmod.BASE_DIR, "app.py"), encoding="utf-8").read()
    assert "storyline-labs-local-demo-secret" not in src
    key = appmod.app.config["SECRET_KEY"]
    assert isinstance(key, str) and len(key) >= 32
    assert security.load_secret_key(appmod.INSTANCE_DIR) == key          # stable across restarts
    mode = os.stat(os.path.join(appmod.INSTANCE_DIR, "secret_key")).st_mode & 0o777
    assert mode == 0o600


def test_env_secret_key_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("LABDEMO_SECRET_KEY", "x" * 40)
    assert security.load_secret_key(str(tmp_path)) == "x" * 40


def test_session_cookie_flags(learner):
    r = appmod.app.test_client().get("/")
    cookie = r.headers.get("Set-Cookie", "")
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie


# ---------------------------------------------------------------- CSRF
def test_post_without_csrf_token_rejected(learner):
    r = learner.c.post(f"/lab/{LAB}/term", json={"cmd": "help"})
    assert r.status_code == 400
    r = learner.c.post(f"/lab/{LAB}/term", json={"cmd": "help"}, headers={"X-CSRF-Token": "wrong"})
    assert r.status_code == 400
    assert learner.c.post(f"/lab/{LAB}/hypothesis", data={"choice": "x"}).status_code == 400


def test_post_with_token_ok(learner):
    assert learner.post_json(f"/lab/{LAB}/term", {"cmd": "help"}).status_code == 200


def test_cross_origin_post_rejected_even_with_token(learner):
    r = learner.c.post(f"/lab/{LAB}/term", json={"cmd": "help"},
                       headers={"X-CSRF-Token": learner.token, "Origin": "http://evil.example"})
    assert r.status_code == 403


@pytest.mark.parametrize("path", ["/reset-all", f"/reset/{LAB}"])
def test_resets_are_post_only(learner, path):
    assert learner.c.get(path).status_code == 405                      # was a GET => CSRF-able
    assert learner.c.post(path).status_code == 400                     # token required
    assert learner.post_form(path, {}).status_code == 302


def test_reset_actually_clears_progress(learner):
    learner.term(LAB, "artforge-gen")
    assert "generated_baseline" in learner.progress(LAB)["actions"]
    learner.post_form(f"/reset/{LAB}", {})
    assert learner.progress(LAB)["actions"] == []


# ---------------------------------------------------------------- headers / CSP / XSS
def test_security_headers(learner):
    r = learner.c.get(f"/lab/{LAB}/room")
    h = r.headers
    csp = h["Content-Security-Policy"]
    assert "script-src 'self'" in csp and "frame-ancestors 'none'" in csp
    assert "script-src 'self' 'unsafe-inline'" not in csp
    assert h["X-Content-Type-Options"] == "nosniff"
    assert h["X-Frame-Options"] == "DENY"
    assert h["Referrer-Policy"] == "same-origin"
    assert h["Cache-Control"] == "no-store"


@pytest.mark.parametrize("lab", [f"lab{i}" for i in range(1, 11)])
def test_no_inline_executable_scripts(learner, lab):
    html = learner.c.get(f"/lab/{lab}/room").get_data(as_text=True)
    for m in re.finditer(r"<script([^>]*)>", html):
        attrs = m.group(1)
        assert "src=" in attrs or 'type="application/json"' in attrs, f"inline script in {lab}: {m.group(0)}"
    assert not re.search(r"\son[a-z]+\s*=", html), "inline event handler found"


def test_user_input_is_escaped(learner):
    payload = "<script>alert(1)</script>"
    learner.post_form(f"/lab/{LAB}/hypothesis", {"choice": payload})
    learner.post_form(f"/lab/{LAB}/report", {"report_text": payload})
    for page in ("hypothesis", "report"):
        html = learner.c.get(f"/lab/{LAB}/{page}").get_data(as_text=True)
        assert payload not in html


def test_room_data_block_cannot_break_out():
    from flask import render_template_string
    with appmod.app.test_request_context():
        out = render_template_string('{{ {"x": "</script><script>alert(1)</script>"} | tojson }}')
    assert "</script>" not in out


# ---------------------------------------------------------------- input handling
@pytest.mark.parametrize("body", [[], "str", None, 5, {"cmd": ["x"]}, {"cmd": {"a": 1}}])
def test_terminal_survives_weird_json(learner, body):
    r = learner.post_json(f"/lab/{LAB}/term", body)
    assert r.status_code == 200


@pytest.mark.parametrize("body", [[], "str", None, {"qid": ["t1"]}, {"qid": {"a": 1}, "answer": 5}, {"qid": "t1" * 50}])
def test_answer_survives_weird_json(learner, body):
    r = learner.post_json(f"/lab/{LAB}/answer", body)
    assert r.status_code == 400 and r.get_json()["ok"] is False


def test_oversized_body_rejected(learner):
    r = learner.c.post(f"/lab/{LAB}/term", data="x" * (70 * 1024),
                       headers={"X-CSRF-Token": learner.token, "Content-Type": "application/json"})
    assert r.status_code == 413


def test_unknown_or_traversal_lab_ids_never_import(learner):
    for bad in ("nope", "..%2fapp", "lab1;ls", "app", "sandbox", "LAB1"):
        r = learner.c.get(f"/lab/{bad}/room")
        assert r.status_code in (302, 404)
        assert learner.post_json(f"/lab/{bad}/term", {"cmd": "help"}).status_code == 404


def test_long_and_malformed_commands(learner):
    assert "too long" in learner.term(LAB, "a" * 1000)
    assert "too many" in learner.term(LAB, "ls " + "x " * 40)
    assert "unbalanced" in learner.term(LAB, "ls 'oops")
    assert learner.term(LAB, "\x00\x01 \u202e") is not None
    assert "not found" in learner.term(LAB, "$(rm -rf /)")


# Hostile numeric arguments must never raise, hang, or allocate without bound.
FUZZ = {
    "lab1": ["artforge-gen", "transform baseline.png --noise nan", "transform baseline.png --crop inf",
             "transform baseline.png --compress -5", "transform baseline.png --crop 100", "transform baseline.png --crop 1e999",
             "transform baseline.png --compress 99999999999999999999"],
    "lab2": ["compare-updates --round nan", "compare-updates --round 1e999", "inspect-update node9", "inspect-update ../etc"],
    "lab4": ["pad nan", "pad -9999", "pad \u00b2", "pad 99999999999999999999999", "pad " + "9" * 5000, "chat " + "A" * 200],
    "lab5": ["make-clone --noise nan", "make-clone --noise 1e308", "make-clone --noise -3"],
    "lab6": ["test-keys 99999999", "test-keys nan", "test-ips 99999999", "scrape --minutes 1e12", "scrape --minutes -4"],
    "lab7": ["inject 999999999 99999999", "inject nan nan", "inject -5"],
    "lab8": ["repeat 1e12", "repeat nan", "repeat -1"],
    "lab9": ["test-photo --dpi nan --gloss inf", "spoof --dpi 1e999 --gloss -9", "spoof --dpi 99999999"],
}


@pytest.mark.parametrize("lab", sorted(FUZZ))
def test_hostile_numeric_arguments_are_contained(learner, lab):
    start = time.time()
    for cmd in FUZZ[lab]:
        r = learner.post_json(f"/lab/{lab}/term", {"cmd": cmd})
        assert r.status_code == 200, (cmd, r.status_code)
        assert "Traceback" not in r.get_json()["output"]
    assert time.time() - start < 20, f"{lab}: hostile arguments took too long"


def test_transform_store_is_bounded(learner):
    learner.term("lab1", "artforge-gen")
    last = ""
    for _ in range(30):
        last = learner.term("lab1", "transform baseline.png --compress 90")
        if "store is full" in last:
            break
    assert "store is full" in last


# ---------------------------------------------------------------- rate limiting
def test_terminal_is_rate_limited(learner):
    codes = [learner.post_json(f"/lab/{LAB}/term", {"cmd": "help"}).status_code for _ in range(70)]
    assert 429 in codes and codes[0] == 200


def test_answer_endpoint_rate_limited_against_brute_force(learner):
    q = next(q for q in storyline_for("lab4").all_questions("lab4") if q["type"] == "text")
    codes = [learner.post_json("/lab/lab4/answer", {"qid": q["id"], "answer": f"guess{i}"}).status_code for i in range(40)]
    assert 429 in codes


def test_rate_limiter_window_expires():
    rl = security.RateLimiter()
    assert all(rl.allow("k", 3, 10, now=t) for t in (0, 1, 2))
    assert not rl.allow("k", 3, 10, now=3)
    assert rl.allow("k", 3, 10, now=20)


def test_per_ip_limit_applies_to_all_pages_even_without_a_session(monkeypatch):
    monkeypatch.setitem(security.LIMITS, "any", (5, 60))
    security.limiter._hits.clear()
    codes = [appmod.app.test_client().get("/").status_code for _ in range(8)]   # fresh cookie-less clients
    assert codes[:5] == [200] * 5 and 429 in codes[5:]
