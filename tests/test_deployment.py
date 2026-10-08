"""Deployment-facing behaviour: /healthz, the container healthcheck, and the post-deploy smoke check."""
import os
import socket
import subprocess
import sys
import time
import http.client

import pytest

import app as appmod
from conftest import ROOT

sys.path.insert(0, os.path.join(ROOT, "scripts"))
import healthcheck  # noqa: E402
import smoke_check  # noqa: E402


# ---------------------------------------------------------------- /healthz
def test_healthz_ok_without_session_cookie_or_lock(learner):
    fresh = appmod.app.test_client()                 # a probe: no cookies, no prior session
    locks_before = len(appmod.STORE._locks)
    r = fresh.get("/healthz")
    assert r.status_code == 200 and r.get_json() == {"status": "ok"}
    assert "Set-Cookie" not in r.headers             # probes must not mint sessions
    assert len(appmod.STORE._locks) == locks_before  # ...or per-session locks
    assert r.headers["Cache-Control"] == "no-store"
    assert "Content-Security-Policy" in r.headers    # still goes through the normal header hook
    assert fresh.head("/healthz").status_code == 200


def test_healthz_503_when_progress_store_is_down(learner, monkeypatch):
    def boom():
        raise RuntimeError("db gone")
    monkeypatch.setattr(appmod.STORE, "ping", boom)
    r = appmod.app.test_client().get("/healthz")
    assert r.status_code == 503 and r.get_json() == {"status": "unavailable"}
    assert "db gone" not in r.get_data(as_text=True)  # no internals in the response


def test_healthz_is_get_only(learner):
    assert learner.c.post("/healthz", headers={"X-CSRF-Token": learner.token}).status_code == 405


# ---------------------------------------------------------------- container healthcheck helper
def test_healthcheck_target_uses_bind_port_and_first_allowed_host():
    assert healthcheck.target({}) == (8000, "localhost")
    env = {"LABDEMO_BIND": "0.0.0.0:9123", "LABDEMO_ALLOWED_HOSTS": " labs.example.com , other.example"}
    assert healthcheck.target(env) == (9123, "labs.example.com")
    assert healthcheck.target({"LABDEMO_ALLOWED_HOSTS": ".example.com"})[1] == "example.com"


# ---------------------------------------------------------------- smoke check against a real server process
def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _serve(tmp_path, **env):
    port = _free_port()
    full = dict(os.environ, LABDEMO_INSTANCE=str(tmp_path), LABDEMO_PORT=str(port), LABDEMO_SECURE_COOKIES="1")
    for k in ("LABDEMO_DB", "LABDEMO_TRUST_PROXY", "LABDEMO_ALLOWED_HOSTS", "LABDEMO_PROXY_HOPS"):
        full.pop(k, None)
    full.update(env)
    proc = subprocess.Popen([sys.executable, os.path.join(ROOT, "app.py")], env=full, cwd=ROOT,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):                               # wait until it accepts connections
        try:
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
            c.request("GET", "/healthz", headers={"Host": "labs.example.com"})
            c.getresponse().read()
            return proc, port
        except OSError:
            time.sleep(0.25)
    proc.kill()
    raise AssertionError("server did not start")


@pytest.fixture
def served(tmp_path):
    procs = []

    def start(**env):
        proc, port = _serve(tmp_path / f"i{len(procs)}", **env)
        procs.append(proc)
        return f"http://127.0.0.1:{port}"
    yield start
    for p in procs:
        p.terminate()
        p.wait(timeout=10)


def test_smoke_check_passes_for_the_documented_production_config(served):
    base = served(LABDEMO_TRUST_PROXY="1", LABDEMO_ALLOWED_HOSTS="labs.example.com")
    results = smoke_check.run(base, simulate_proxy="labs.example.com")
    assert [(n, ok) for n, ok, _ in results if ok is False] == [], results


def test_smoke_check_flags_missing_proxy_trust(served):
    base = served()                                   # secure cookies on, but LABDEMO_TRUST_PROXY unset
    results = {n: (ok, d) for n, ok, d in smoke_check.run(base, simulate_proxy="labs.example.com")}
    ok, detail = results["legitimate POST passes origin check"]
    assert ok is False and "LABDEMO_TRUST_PROXY" in detail


def test_smoke_check_flags_insecure_cookies(served):
    base = served(LABDEMO_TRUST_PROXY="1", LABDEMO_SECURE_COOKIES="0")
    results = {n: (ok, d) for n, ok, d in smoke_check.run(base, simulate_proxy="labs.example.com")}
    ok, detail = results["cookies / HSTS / CSP / banners"]
    assert ok is False and "Secure" in detail and "HSTS" in detail


def test_smoke_check_cli_exit_codes(served):
    good = served(LABDEMO_TRUST_PROXY="1")
    bad = served()
    run = lambda base: subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "smoke_check.py"), "--base", base,
                                       "--simulate-proxy", "labs.example.com"], capture_output=True, text=True)
    assert run(good).returncode == 0
    r = run(bad)
    assert r.returncode == 1 and "FAIL" in r.stdout


# ---------------------------------------------------------------- the real production server (gunicorn)
def test_gunicorn_serves_the_documented_production_config(tmp_path):
    pytest.importorskip("gunicorn")
    port = _free_port()
    env = dict(os.environ, LABDEMO_INSTANCE=str(tmp_path), LABDEMO_BIND=f"127.0.0.1:{port}",
               LABDEMO_SECURE_COOKIES="1", LABDEMO_TRUST_PROXY="1", LABDEMO_ALLOWED_HOSTS="labs.example.com")
    for k in ("LABDEMO_DB", "LABDEMO_PROXY_HOPS"):
        env.pop(k, None)
    proc = subprocess.Popen([sys.executable, "-m", "gunicorn", "-c", os.path.join(ROOT, "gunicorn.conf.py"), "app:app"],
                            env=env, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(80):
            try:
                c = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
                c.request("GET", "/healthz", headers={"Host": "labs.example.com"})
                c.getresponse().read()
                break
            except OSError:
                time.sleep(0.25)
        else:
            raise AssertionError("gunicorn did not start")
        results = smoke_check.run(f"http://127.0.0.1:{port}", simulate_proxy="labs.example.com")
        assert [(n, ok) for n, ok, _ in results if ok is False] == [], results
    finally:
        proc.terminate()
        proc.wait(timeout=10)  # docker stop SIGKILLs after 10s: shutdown must beat it
