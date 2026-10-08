# -*- coding: utf-8 -*-
"""
Security hardening for the labs app.

  * Secret key  : from LABDEMO_SECRET_KEY, else generated once and kept in
                  instance/secret_key (0600). Never hard-coded in source.
  * Cookies     : HttpOnly, SameSite=Lax, optional Secure (LABDEMO_SECURE_COOKIES=1).
  * CSRF        : every POST needs the session token (header or form field) and a
                  same-origin Origin/Referer if the browser sent one.
  * Headers     : strict CSP (no inline/external scripts), nosniff, no framing,
                  no-store on dynamic pages, no referrer leakage.
  * Rate limits : sliding window per session AND per client IP, so the terminal,
                  answer checker and forms can't be hammered or brute-forced.
  * Errors      : generic JSON/text responses; no stack traces or internals.
  * Proxy/Host  : LABDEMO_TRUST_PROXY=1 enables ProxyFix (client IP, scheme, host) for exactly
                  LABDEMO_PROXY_HOPS proxies (default 1; 2 for CDN -> proxy -> app);
                  LABDEMO_ALLOWED_HOSTS=a.example,b.example pins the accepted Host header.
"""
import hmac
import os
import secrets
import threading
import time
from collections import OrderedDict, deque
from urllib.parse import urlparse

from flask import jsonify, make_response, request, session

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
MAX_PROXY_HOPS = 5

# (max requests, window seconds) per endpoint, per session. IP limits are 3x.
LIMITS = {
    "term": (60, 60),
    "answer": (30, 60),
    "hint": (20, 60),
    "default_post": (40, 60),
    "any": (600, 60),        # every non-static request, per IP
}

CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; "
       "img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; "
       "base-uri 'none'; form-action 'self'; frame-ancestors 'none'")


# ------------------------------------------------------------------ secret key
MIN_KEY_LEN = 32


def _write_key_file(path, key):
    """Write the key with 0600 from the first byte, and force 0600 even on a pre-existing file."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.fchmod(fd, 0o600)
    except (AttributeError, OSError):      # non-POSIX filesystems
        pass
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(key)


def load_secret_key(instance_dir):
    env = os.environ.get("LABDEMO_SECRET_KEY") or os.environ.get("SECRET_KEY")
    if env:
        if len(env) < MIN_KEY_LEN:
            raise RuntimeError(
                f"LABDEMO_SECRET_KEY is too short ({len(env)} chars); use at least {MIN_KEY_LEN}, "
                "e.g.  python -c 'import secrets; print(secrets.token_hex(32))'")
        return env
    os.makedirs(instance_dir, exist_ok=True)
    path = os.path.join(instance_dir, "secret_key")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            key = fh.read().strip()
        if len(key) >= MIN_KEY_LEN:
            try:
                os.chmod(path, 0o600)       # tighten a key file that was copied/restored with loose perms
            except OSError:
                pass
            return key
    except OSError:
        pass
    key = secrets.token_hex(32)
    _write_key_file(path, key)
    return key


def proxy_hops():
    """How many trusted proxies sit in front of the app (LABDEMO_PROXY_HOPS, default 1).

    Too low and every client looks like the proxy (shared rate limit, wrong scheme); too high and a
    client can spoof its own IP/host by prepending X-Forwarded-* values. So: refuse nonsense."""
    raw = (os.environ.get("LABDEMO_PROXY_HOPS") or "1").strip()
    try:
        hops = int(raw)
    except ValueError:
        hops = 0
    if not 1 <= hops <= MAX_PROXY_HOPS:
        raise RuntimeError(f"LABDEMO_PROXY_HOPS must be an integer from 1 to {MAX_PROXY_HOPS}, got {raw!r}")
    return hops


# ------------------------------------------------------------------ rate limiter
class RateLimiter:
    """Sliding-window limiter with bounded memory.

    Keys are kept in least-recently-used order. When the table is full, expired keys are
    dropped first, then the least recently used ones. A flood of junk keys can therefore
    never reset the counters of keys that are actively being rate-limited."""

    def __init__(self, max_keys=20000):
        self._hits = OrderedDict()          # key -> (deque of timestamps, window)
        self._lock = threading.Lock()
        self._max_keys = max_keys

    def _evict(self, now):
        while len(self._hits) > self._max_keys:
            key, (q, window) = next(iter(self._hits.items()))
            self._hits.pop(key)             # oldest-touched first (expired ones are always older)

    def allow(self, key, limit, window, now=None):
        now = time.monotonic() if now is None else now
        with self._lock:
            entry = self._hits.get(key)
            q = entry[0] if entry else deque()
            while q and now - q[0] > window:
                q.popleft()
            if len(q) >= limit:
                self._hits[key] = (q, window)
                self._hits.move_to_end(key)
                return False
            q.append(now)
            self._hits[key] = (q, window)
            self._hits.move_to_end(key)
            self._evict(now)
            return True


limiter = RateLimiter()


# ------------------------------------------------------------------ CSRF
def csrf_token():
    tok = session.get("csrf")
    if not tok:
        tok = secrets.token_urlsafe(32)
        session["csrf"] = tok
    return tok


def _same_origin():
    """If the browser sent Origin/Referer, scheme AND host must match our own."""
    src = request.headers.get("Origin") or request.headers.get("Referer")
    if not src:
        return True                      # non-browser client / privacy setting; token still required
    try:
        u = urlparse(src)
    except ValueError:
        return False
    return u.scheme == request.scheme and u.netloc == request.host


def _wants_json():
    return request.is_json or request.path.endswith(("/term", "/answer", "/hint"))


def _reject(status, message):
    if _wants_json():
        return make_response(jsonify(ok=False, error=message, message=message, output=message), status)
    return make_response(message, status, {"Content-Type": "text/plain; charset=utf-8"})


def _endpoint_key():
    ep = (request.endpoint or "").split(".")[-1]
    return ep if ep in ("term", "answer", "hint") else "default_post"


def init_security(app, instance_dir):
    app.config.update(
        SECRET_KEY=load_secret_key(instance_dir),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("LABDEMO_SECURE_COOKIES") == "1",
        PERMANENT_SESSION_LIFETIME=30 * 24 * 3600,
        MAX_CONTENT_LENGTH=64 * 1024,
    )
    app.jinja_env.globals["csrf_token"] = csrf_token
    secure = app.config["SESSION_COOKIE_SECURE"]

    if os.environ.get("LABDEMO_TRUST_PROXY") == "1":
        # Only enable this behind a proxy that overwrites X-Forwarded-For/Proto/Host itself.
        from werkzeug.middleware.proxy_fix import ProxyFix
        hops = proxy_hops()
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=hops, x_proto=hops, x_host=hops)
    hosts = [h.strip() for h in os.environ.get("LABDEMO_ALLOWED_HOSTS", "").split(",") if h.strip()]
    if hosts:
        app.config["TRUSTED_HOSTS"] = hosts

    @app.before_request
    def _guard():
        if request.endpoint == "static":
            return None
        sid = session.get("sid")
        ip = request.remote_addr or "?"
        if not limiter.allow(("ip-any", ip), *LIMITS["any"]):
            return _reject(429, "Too many requests -- slow down.")
        if request.method in UNSAFE_METHODS:
            lim = LIMITS[_endpoint_key()]
            if sid and not limiter.allow(("sid", sid, _endpoint_key()), *lim):
                return _reject(429, "Too many requests -- slow down.")
            if not limiter.allow(("ip", ip, _endpoint_key()), lim[0] * 3, lim[1]):
                return _reject(429, "Too many requests -- slow down.")
            sent = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token", "")
            expected = session.get("csrf", "")
            if not expected or not hmac.compare_digest(str(sent).encode("utf-8", "replace"),
                                                       expected.encode("utf-8")):
                return _reject(400, "Missing or invalid CSRF token. Reload the page and try again.")
            if not _same_origin():
                return _reject(403, "Cross-origin request blocked.")
        return None

    @app.after_request
    def _headers(resp):
        resp.headers["Content-Security-Policy"] = CSP
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "same-origin"
        resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        resp.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        resp.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        if secure:
            resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        if request.endpoint != "static":
            resp.headers["Cache-Control"] = "no-store"
        return resp

    for code, msg in ((400, "Bad request."), (404, "Not found."), (405, "Method not allowed."),
                      (413, "Request too large."), (429, "Too many requests."),
                      (500, "Something went wrong on our side.")):
        app.register_error_handler(code, lambda e, m=msg, c=code: _reject(c, m))
