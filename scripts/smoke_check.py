#!/usr/bin/env python3
"""Post-deploy smoke check for a labdemo instance. Stdlib only; exits non-zero on any failure.

Real deployment (run from anywhere that can reach it):
    python scripts/smoke_check.py --base https://labs.example.com
    python scripts/smoke_check.py --base https://staging.example --insecure     # self-signed cert

It verifies what only a real HTTPS front end can get wrong: TLS validity, http->https redirect,
Secure/HttpOnly/SameSite cookies, HSTS, CSP, no version banners, and -- most importantly -- that a
legitimate POST passes the app's same-origin check (i.e. the proxy forwards scheme and host and
LABDEMO_TRUST_PROXY / LABDEMO_PROXY_HOPS match) while a cross-origin POST, even with a spoofed
X-Forwarded-Host, is refused.

Proxy-free CI mode (talks to the app directly and *pretends* to be the proxy):
    python scripts/smoke_check.py --base http://127.0.0.1:8000 --simulate-proxy labs.example.com
"""
import argparse
import http.client
import json
import re
import ssl
import sys
from urllib.parse import urlsplit

TOKEN_RE = re.compile(r'<meta name="csrf-token" content="([^"]+)"')
VERSIONED = re.compile(r"\d+\.\d+")          # "gunicorn/23.0", "Werkzeug/3.1", "Python/3.12"
MIN_HSTS = 15552000                          # 180 days


class Client:
    """A minimal cookie-keeping HTTP client that never follows redirects."""

    def __init__(self, base, insecure=False, extra_headers=None, timeout=10):
        u = urlsplit(base)
        if u.scheme not in ("http", "https") or not u.hostname:
            raise ValueError(f"--base must be an http(s) URL, got {base!r}")
        self.scheme, self.host = u.scheme, u.hostname
        self.port = u.port or (443 if u.scheme == "https" else 80)
        self.insecure, self.timeout = insecure, timeout
        self.extra = dict(extra_headers or {})
        self.cookies, self.set_cookie_raw = {}, []

    def _conn(self):
        if self.scheme == "http":
            return http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)
        ctx = ssl.create_default_context()
        if self.insecure:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE      # nosec - explicit opt-in (--insecure) for self-signed staging certs
        return http.client.HTTPSConnection(self.host, self.port, timeout=self.timeout, context=ctx)

    def request(self, method, path, headers=None, json_body=None):
        hdrs = dict(self.extra)
        if self.cookies:
            hdrs["Cookie"] = "; ".join(f"{k}={v}" for k, v in self.cookies.items())
        hdrs.update(headers or {})
        body = None
        if json_body is not None:
            body = json.dumps(json_body).encode()
            hdrs["Content-Type"] = "application/json"
        conn = self._conn()
        try:
            conn.request(method, path, body=body, headers=hdrs)
            resp = conn.getresponse()
            data = resp.read(2_000_000)
            heads = resp.getheaders()
        finally:
            conn.close()
        for k, v in heads:
            if k.lower() == "set-cookie":
                self.set_cookie_raw.append(v)
                name, _, rest = v.partition("=")
                self.cookies[name] = rest.split(";", 1)[0]
        return resp.status, heads, data


def header(heads, name):
    vals = [v for k, v in heads if k.lower() == name.lower()]
    return vals[0] if vals else None


HINT_400 = (" (400 = Host rejected: LABDEMO_ALLOWED_HOSTS must list the public hostname, and the proxy must send it "
            "as Host / X-Forwarded-Host with LABDEMO_TRUST_PROXY=1)")


def check_health(c, ctx):
    status, _, body = c.request("GET", "/healthz")
    try:
        ok = status == 200 and json.loads(body).get("status") == "ok"
    except ValueError:
        ok = False
    return ok, f"GET /healthz -> {status}" + (HINT_400 if status == 400 else "")

def check_https_redirect(c, ctx):
    if ctx["simulated"]:
        return None, "skipped (simulated proxy)"
    if c.scheme != "https":
        return False, "base URL is not https; production must be served over HTTPS"
    if ctx["skip_redirect"]:
        return None, "skipped (--skip-redirect)"
    plain = Client(ctx["http_url"] or f"http://{c.host}", extra_headers=None)
    try:
        status, heads, _ = plain.request("GET", "/")
    except OSError as exc:
        return False, f"could not reach {plain.scheme}://{plain.host}:{plain.port}: {exc}"
    loc = header(heads, "Location") or ""
    return (status in (301, 302, 307, 308) and loc.startswith("https://")), f"GET http://... -> {status} {loc}"


def check_page_security(c, ctx):
    status, heads, body = c.request("GET", "/lab/lab1/room")
    problems = []
    if status != 200:
        return False, f"GET /lab/lab1/room -> {status}" + (HINT_400 if status == 400 else "")
    ctx["token"] = (TOKEN_RE.search(body.decode("utf-8", "replace")) or [None, None])[1]
    cookie = next((v for v in c.set_cookie_raw if v.startswith("session=")), "")
    if not cookie:
        problems.append("no session cookie issued")
    for attr in ("Secure", "HttpOnly", "SameSite=Lax"):
        if cookie and not re.search(rf"(;|^)\s*{re.escape(attr)}(;|$)", cookie, re.I):
            problems.append(f"cookie lacks {attr}")
    hsts = header(heads, "Strict-Transport-Security") or ""
    m = re.search(r"max-age=(\d+)", hsts)
    if not m or int(m.group(1)) < MIN_HSTS:
        problems.append("HSTS missing or max-age < 180 days (set LABDEMO_SECURE_COOKIES=1)")
    csp = header(heads, "Content-Security-Policy") or ""
    if not csp or "unsafe-inline" in csp or "unsafe-eval" in csp:
        problems.append("CSP missing or allows unsafe-inline/unsafe-eval")
    if (header(heads, "X-Content-Type-Options") or "").lower() != "nosniff":
        problems.append("X-Content-Type-Options: nosniff missing")
    if "frame-ancestors 'none'" not in csp and (header(heads, "X-Frame-Options") or "").upper() != "DENY":
        problems.append("framing not blocked")
    for banner in ("Server", "X-Powered-By"):
        val = header(heads, banner)
        if val and VERSIONED.search(val):
            problems.append(f"{banner} leaks a version: {val}")
    if not ctx["token"]:
        problems.append("no CSRF token in page")
    return not problems, "; ".join(problems) or "cookie flags, HSTS, CSP, banners OK"


def check_same_origin_post(c, ctx):
    if not ctx.get("token"):
        return False, "no CSRF token (previous check failed)"
    status, _, body = c.request("POST", "/lab/lab1/term", json_body={"cmd": "help"},
                                headers={"X-CSRF-Token": ctx["token"], "Origin": ctx["origin"]})
    if status == 403:
        return False, ("403 on a legitimate POST: the app does not see the public scheme/host. Check the proxy sends "
                       "X-Forwarded-Proto/Host and the app has LABDEMO_TRUST_PROXY=1 and the right LABDEMO_PROXY_HOPS")
    try:
        ok = status == 200 and "output" in json.loads(body)
    except ValueError:
        ok = False
    return ok, f"POST /lab/lab1/term (Origin {ctx['origin']}) -> {status}"


def check_rejections(c, ctx):
    token = ctx.get("token") or "x"
    s_missing, _, _ = c.request("POST", "/lab/lab1/term", json_body={"cmd": "help"}, headers={"Origin": ctx["origin"]})
    hdrs = {"X-CSRF-Token": token, "Origin": "https://evil.example"}
    if not ctx["simulated"]:
        hdrs["X-Forwarded-Host"] = "evil.example"      # a spoof a correct proxy overwrites with the real host
    s_cross, _, _ = c.request("POST", "/lab/lab1/term", json_body={"cmd": "help"}, headers=hdrs)
    # 403 = same-origin check refused it; 400 = host pinning refused a spoof that reached the app. 2xx = broken.
    ok = s_missing == 400 and s_cross in (400, 403)
    return ok, f"no token -> {s_missing} (want 400); cross-origin POST -> {s_cross} (want 403, or 400 if host-pinned)"


CHECKS = [("health endpoint", check_health), ("http -> https redirect", check_https_redirect),
          ("cookies / HSTS / CSP / banners", check_page_security),
          ("legitimate POST passes origin check", check_same_origin_post),
          ("CSRF + cross-origin POSTs refused", check_rejections)]


def run(base, insecure=False, simulate_proxy=None, http_url=None, skip_redirect=False):
    extra, origin = {}, None
    if simulate_proxy:
        extra = {"X-Forwarded-Proto": "https", "X-Forwarded-Host": simulate_proxy, "X-Forwarded-For": "203.0.113.9"}
        origin = f"https://{simulate_proxy}"
    c = Client(base, insecure=insecure, extra_headers=extra)
    ctx = {"simulated": bool(simulate_proxy), "http_url": http_url, "skip_redirect": skip_redirect,
           "origin": origin or f"{c.scheme}://{urlsplit(base).netloc}"}
    results = []
    for name, fn in CHECKS:
        try:
            ok, detail = fn(c, ctx)
        except (OSError, http.client.HTTPException) as exc:
            ok, detail = False, f"{type(exc).__name__}: {exc}"
        results.append((name, ok, detail))
    return results


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--base", required=True, help="public URL, e.g. https://labs.example.com")
    ap.add_argument("--insecure", action="store_true", help="accept a self-signed certificate (staging only)")
    ap.add_argument("--simulate-proxy", metavar="HOST", help="talk to the app directly, adding X-Forwarded-* for HOST")
    ap.add_argument("--http-url", help="URL of the plain-HTTP listener if not on port 80")
    ap.add_argument("--skip-redirect", action="store_true", help="don't test the http->https redirect")
    args = ap.parse_args(argv)
    results = run(args.base, args.insecure, args.simulate_proxy, args.http_url, args.skip_redirect)
    failed = False
    for name, ok, detail in results:
        mark = "SKIP" if ok is None else ("PASS" if ok else "FAIL")
        failed |= ok is False
        print(f"{mark}  {name}: {detail}")
    print("\nFAILED" if failed else "\nall checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
