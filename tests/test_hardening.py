"""Regression tests for the findings of the October 2026 security review.

Each test is named after the finding it locks in."""
import logging
import os
import re
import stat
import threading

import flask
import pytest

import app as appmod
import security
from store import ProgressStore
from storylines import storyline_for
from walkthrough import solve_lab

LAB = "lab1"


def _mini_app(monkeypatch, tmp_path, **env):
    """A tiny Flask app wired with init_security() under specific environment variables."""
    for k in ("LABDEMO_TRUST_PROXY", "LABDEMO_PROXY_HOPS", "LABDEMO_ALLOWED_HOSTS", "LABDEMO_SECURE_COOKIES",
              "LABDEMO_SECRET_KEY"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    a = flask.Flask("mini")
    security.init_security(a, str(tmp_path))

    @a.route("/info")
    def info():
        r = flask.request
        return {"scheme": r.scheme, "host": r.host, "ip": r.remote_addr}
    return a


# ---------------------------------------------------------------- F1 resource exhaustion
def test_lab1_artforge_gen_is_capped(learner):
    outs = [learner.term("lab1", "artforge-gen") for _ in range(30)]
    imgs = learner.progress("lab1")["sandbox"]["images"]
    assert len(imgs) == 25
    assert "store is full" in outs[-1]


def test_lab1_cap_is_shared_with_transform(learner):
    for _ in range(25):
        learner.term("lab1", "artforge-gen")
    assert "store is full" in learner.term("lab1", "transform baseline.png --noise 5")


def test_lab6_key_registration_is_capped(learner):
    outs = [learner.term("lab6", "test-keys 100") for _ in range(12)]
    api = learner.progress("lab6")["sandbox"]["api"]
    assert len(api.registered_keys) <= 1000
    assert "sandbox limit reached" in outs[-1]
    assert "sandbox limit reached" in learner.term("lab6", "test-ips 5")


def test_lab7_inject_is_capped_per_call_and_in_total(learner):
    out = learner.term("lab7", "inject 5000 48")
    assert "Injected 1000 fake" in out                       # clamped per call
    for _ in range(2):
        learner.term("lab7", "inject 1000 48")
    assert "sandbox limit reached" in learner.term("lab7", "inject 1000 48")
    _, target, _ = (lambda d: (d["sellers"], d["target"], d["ranker"]))(learner.progress("lab7")["sandbox"])
    assert len(target.reviews) <= 3000 + 200               # + the market's own organic reviews


def test_lab7_default_walkthrough_still_works(learner):
    assert "RANKING POISONED" in learner.term("lab7", "inject")


def test_lab8_unknown_record_is_validated_not_crashed(learner, caplog):
    with caplog.at_level(logging.ERROR, logger="labdemo.sandbox"):
        out = learner.term("lab8", "query nope-1 99999999999999999999")
    assert "unknown record" in out and "failed" not in out
    assert not [r for r in caplog.records if r.exc_info], "no traceback should be logged for bad user input"
    assert "mean_query" in learner.term("lab8", "query")    # default subgroup still works


# ---------------------------------------------------------------- F2 non-ASCII CSRF token
@pytest.mark.parametrize("bad", ["é", "日本語", "\u00ff" * 40, "\u0000"])
def test_non_ascii_csrf_token_gets_400_not_500(learner, bad):
    r = learner.c.post(f"/lab/{LAB}/hypothesis", data={"csrf_token": bad})
    assert r.status_code == 400
    r = learner.c.post(f"/lab/{LAB}/term", json={"cmd": "help"}, headers={"X-CSRF-Token": bad})
    assert r.status_code == 400


# ---------------------------------------------------------------- F3 limiter flood
def test_rate_limiter_flood_does_not_reset_active_counters():
    rl = security.RateLimiter(max_keys=500)
    for _ in range(5):
        assert rl.allow(("victim",), 5, 60, now=100.0)
    assert not rl.allow(("victim",), 5, 60, now=100.0)
    for i in range(5000):                                    # junk keys, interleaved with real traffic
        rl.allow(("junk", i), 1, 60, now=100.0)
        if i % 50 == 0:
            rl.allow(("victim",), 5, 60, now=100.0)          # the victim is still being limited (and touched)
    assert not rl.allow(("victim",), 5, 60, now=100.5)
    assert len(rl._hits) <= 500


def test_rate_limiter_window_still_expires():
    rl = security.RateLimiter()
    for _ in range(3):
        rl.allow(("k",), 3, 10, now=0.0)
    assert not rl.allow(("k",), 3, 10, now=5.0)
    assert rl.allow(("k",), 3, 10, now=11.0)


# ---------------------------------------------------------------- F4/F5 secret key
@pytest.mark.parametrize("weak", ["abc", "x" * 31])
def test_weak_env_secret_key_refused(monkeypatch, tmp_path, weak):
    monkeypatch.setenv("LABDEMO_SECRET_KEY", weak)
    with pytest.raises(RuntimeError, match="too short"):
        security.load_secret_key(str(tmp_path))


def test_existing_loose_key_file_is_tightened(monkeypatch, tmp_path):
    monkeypatch.delenv("LABDEMO_SECRET_KEY", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    p = tmp_path / "secret_key"
    p.write_text("b" * 64)
    os.chmod(p, 0o644)
    assert security.load_secret_key(str(tmp_path)) == "b" * 64
    assert stat.S_IMODE(os.stat(p).st_mode) == 0o600


def test_short_key_file_is_replaced_with_0600(monkeypatch, tmp_path):
    monkeypatch.delenv("LABDEMO_SECRET_KEY", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    p = tmp_path / "secret_key"
    p.write_text("short")
    os.chmod(p, 0o666)
    key = security.load_secret_key(str(tmp_path))
    assert len(key) == 64 and stat.S_IMODE(os.stat(p).st_mode) == 0o600


# ---------------------------------------------------------------- F6 origin scheme / proxy / host
def test_http_origin_rejected_on_https_site(learner):
    r = learner.c.post(f"/lab/{LAB}/term", json={"cmd": "help"}, base_url="https://localhost",
                       headers={"X-CSRF-Token": learner.token, "Origin": "http://localhost"})
    assert r.status_code == 403


def test_matching_scheme_and_host_accepted(learner):
    r = learner.c.post(f"/lab/{LAB}/term", json={"cmd": "help"}, base_url="https://localhost",
                       headers={"X-CSRF-Token": learner.token, "Origin": "https://localhost"})
    assert r.status_code == 200


def test_proxyfix_is_opt_in(monkeypatch, tmp_path):
    off = _mini_app(monkeypatch, tmp_path).test_client().get(
        "/info", headers={"X-Forwarded-For": "1.2.3.4", "X-Forwarded-Proto": "https", "X-Forwarded-Host": "evil.test"})
    assert off.get_json()["host"] != "evil.test" and off.get_json()["scheme"] == "http"   # spoofable headers ignored
    on = _mini_app(monkeypatch, tmp_path, LABDEMO_TRUST_PROXY="1").test_client().get(
        "/info", headers={"X-Forwarded-For": "1.2.3.4", "X-Forwarded-Proto": "https", "X-Forwarded-Host": "app.example.com"})
    assert on.get_json() == {"scheme": "https", "host": "app.example.com", "ip": "1.2.3.4"}


def test_proxy_hops_default_is_one_and_two_hops_skips_the_outer_proxy(monkeypatch, tmp_path):
    xff = {"X-Forwarded-For": "9.9.9.9, 10.0.0.2"}        # client, then the first proxy's view of its peer
    one = _mini_app(monkeypatch, tmp_path, LABDEMO_TRUST_PROXY="1").test_client().get("/info", headers=xff)
    two = _mini_app(monkeypatch, tmp_path, LABDEMO_TRUST_PROXY="1", LABDEMO_PROXY_HOPS="2").test_client().get(
        "/info", headers=xff)
    assert one.get_json()["ip"] == "10.0.0.2"             # trusts only the last hop
    assert two.get_json()["ip"] == "9.9.9.9"              # CDN -> proxy -> app


@pytest.mark.parametrize("bad", ["0", "-1", "6", "two", "1.5"])
def test_nonsense_proxy_hops_refused_at_startup(monkeypatch, tmp_path, bad):
    with pytest.raises(RuntimeError, match="LABDEMO_PROXY_HOPS"):
        _mini_app(monkeypatch, tmp_path, LABDEMO_TRUST_PROXY="1", LABDEMO_PROXY_HOPS=bad)


def test_proxy_hops_ignored_unless_proxy_trusted(monkeypatch, tmp_path):
    a = _mini_app(monkeypatch, tmp_path, LABDEMO_PROXY_HOPS="9")     # would be invalid, but proxy trust is off
    assert a.test_client().get("/info").status_code == 200


def test_behind_proxy_legit_post_passes_origin_check(monkeypatch, tmp_path):
    a = _mini_app(monkeypatch, tmp_path, LABDEMO_TRUST_PROXY="1")

    @a.route("/p", methods=["POST"])
    def p():
        return {"ok": True}
    c = a.test_client()
    with c.session_transaction() as s:
        s["csrf"] = "t" * 40
    h = {"X-CSRF-Token": "t" * 40, "X-Forwarded-Proto": "https", "X-Forwarded-Host": "app.example.com"}
    assert c.post("/p", headers=dict(h, Origin="https://app.example.com")).status_code == 200
    assert c.post("/p", headers=dict(h, Origin="https://evil.example")).status_code == 403


def test_allowed_hosts_pins_host_header(monkeypatch, tmp_path):
    c = _mini_app(monkeypatch, tmp_path, LABDEMO_ALLOWED_HOSTS="app.example.com").test_client()
    assert c.get("/info", headers={"Host": "app.example.com"}).status_code == 200
    assert c.get("/info", headers={"Host": "evil.example"}).status_code in (400, 404)


# ---------------------------------------------------------------- F7 locked evidence not in page source
def _room_data(page):
    import json
    return json.loads(re.search(r'<script id="room-data"[^>]*>(.*?)</script>', page, re.S).group(1))


def test_locked_evidence_text_not_sent_to_browser(learner):
    mod = appmod.load_lab(LAB)
    page = learner.c.get(f"/lab/{LAB}/room").get_data(as_text=True)
    data = _room_data(page)
    assert data["evidence"] == {} and set(data["evidenceIds"]) == set(mod.EVIDENCE_CATALOG)
    for ev in mod.EVIDENCE_CATALOG.values():
        assert ev["description"] not in page and ev["title"] not in page
        assert "required_actions" not in page


def test_unlocked_evidence_text_arrives_via_terminal_response(learner):
    mod = appmod.load_lab(LAB)
    learner.term(LAB, "artforge-gen")
    r = learner.post_json(f"/lab/{LAB}/term", {"cmd": "wm-verify baseline.png"}).get_json()
    assert r["unlocked"], "generating + verifying the baseline should unlock evidence"
    for k in r["unlocked"]:
        assert r["evidence"][k]["title"] == mod.EVIDENCE_CATALOG[k]["title"]
    assert set(r["evidence"]) == set(r["unlocked"])
    data = _room_data(learner.c.get(f"/lab/{LAB}/room").get_data(as_text=True))
    assert set(data["evidence"]) == set(r["unlocked"])


# ---------------------------------------------------------------- F8 flags
def test_static_flags_by_default(learner, monkeypatch):
    monkeypatch.delenv("LABDEMO_PER_USER_FLAGS", raising=False)
    res = solve_lab(learner, "lab1", appmod.load_lab("lab1"))
    assert res["flag"] == storyline_for("lab1").static_flag("lab1")


def test_per_user_flags_are_unique_and_verifiable(learner, monkeypatch):
    from conftest import Learner
    monkeypatch.setenv("LABDEMO_PER_USER_FLAGS", "1")
    other = Learner(appmod.app.test_client())
    f1 = solve_lab(learner, "lab1", appmod.load_lab("lab1"))["flag"]
    f2 = solve_lab(other, "lab1", appmod.load_lab("lab1"))["flag"]
    static = storyline_for("lab1").static_flag("lab1")
    assert f1 != f2 and f1 != static
    assert f1 == appmod.expected_flag(appmod.app.config["SECRET_KEY"], learner.sid, "lab1", static)
    assert f1.startswith(static[:-1]) and f1.endswith("}")
    # the outcome page shows the same per-user flag
    assert f1 in learner.c.get("/lab/lab1/outcome").get_data(as_text=True)


# ---------------------------------------------------------------- F9 headers / CSP / inline styles
def test_csp_has_no_unsafe_inline_anywhere(learner):
    csp = learner.c.get("/").headers["Content-Security-Policy"]
    assert "unsafe-inline" not in csp and "style-src 'self';" in csp


@pytest.mark.parametrize("path", ["/", "/lab/lab1", "/lab/lab1/hypothesis", "/lab/lab1/room", "/lab/lab1/knowledge",
                                  "/lab/lab1/evidence", "/lab/lab1/report", "/lab/lab1/outcome"])
def test_pages_use_no_inline_style_or_script(learner, path):
    html = learner.c.get(path).get_data(as_text=True)
    assert not re.search(r"<[^>]+\sstyle\s*=", html, re.I)
    assert not re.search(r"<style\b", html, re.I)
    assert not re.search(r"\son\w+\s*=", html, re.I)
    for body in re.findall(r"<script(?![^>]*\bsrc=)(?![^>]*application/json)[^>]*>(.+?)</script>", html, re.S):
        raise AssertionError("inline script found: " + body[:60])


def test_outcome_bars_and_accents_use_data_attributes(learner):
    html = learner.c.get("/lab/lab1/outcome").get_data(as_text=True)
    assert "data-pct=" in html and "data-accent=" in html
    assert "ui.js" in html and os.path.exists(os.path.join(appmod.BASE_DIR, "static", "ui.js"))


def test_hsts_only_when_secure_cookies(monkeypatch, tmp_path):
    app_off = _mini_app(monkeypatch, tmp_path)
    app_on = _mini_app(monkeypatch, tmp_path, LABDEMO_SECURE_COOKIES="1")
    off, on = app_off.test_client().get("/info"), app_on.test_client().get("/info")
    assert app_on.config["SESSION_COOKIE_SECURE"] is True and app_off.config["SESSION_COOKIE_SECURE"] is False
    assert "Strict-Transport-Security" not in off.headers
    assert "max-age=" in on.headers["Strict-Transport-Security"]
    assert on.headers["Cross-Origin-Resource-Policy"] == "same-origin"


def test_dev_server_banner_is_not_version_revealing():
    src = open(os.path.join(appmod.BASE_DIR, "app.py"), encoding="utf-8").read()
    assert "version_string" in src and "request_handler=_QuietHandler" in src
    assert 'gunicorn.SERVER = "labdemo"' in open(os.path.join(appmod.BASE_DIR, "gunicorn.conf.py")).read()


# ---------------------------------------------------------------- F10 session-lock eviction
def test_session_lock_eviction_never_drops_a_held_lock():
    st = ProgressStore(":memory:")
    held = st.session_lock("a" * 32)
    held.acquire()
    done = []

    def other():                                            # another thread holds the lock while the table overflows
        for i in range(6000):
            st.session_lock(f"{i:032x}")
        done.append(st.session_lock("a" * 32))
    t = threading.Thread(target=other)
    t.start(); t.join()
    assert done[0] is held, "a lock that is held must survive eviction (else one session could run in parallel)"
    assert len(st._locks) < 6000
    held.release()


# ---------------------------------------------------------------- previously uncovered routes
def test_report_evidence_outcome_and_reset_all_routes(learner):
    r = learner.post_form(f"/lab/{LAB}/report", {"report_text": "watermark compression noise transform"})
    assert r.status_code == 200
    mod = appmod.load_lab(LAB)
    chain = {s: mod.ATTACK_CHAIN_LINKS[s]["correct"] for s in mod.ATTACK_CHAIN_SLOT_ORDER}
    assert learner.post_form(f"/lab/{LAB}/evidence", chain).status_code == 200
    assert "chain_correct" in learner.progress(LAB)["actions"]
    assert learner.c.get(f"/lab/{LAB}/outcome").status_code == 200
    r = learner.post_form("/reset-all", {})
    assert r.status_code == 302
    assert learner.c.get("/").status_code == 200
