#!/usr/bin/env python3
"""Container HEALTHCHECK: exit 0 iff the app answers /healthz with {"status": "ok"}.

Stdlib only (the image has no curl). It talks to the app directly on loopback, so it must
send a Host header the app accepts: when LABDEMO_ALLOWED_HOSTS is set, the first entry is used.
"""
import http.client
import json
import os
import sys


def target(env=None):
    """Return (port, host_header) for the local probe."""
    env = os.environ if env is None else env
    bind = env.get("LABDEMO_BIND", "127.0.0.1:8000")
    port = int(bind.rsplit(":", 1)[-1])
    hosts = [h.strip() for h in env.get("LABDEMO_ALLOWED_HOSTS", "").split(",") if h.strip()]
    # ".example.com" is a valid allow-list pattern but not a valid Host header; probe the apex instead
    return port, (hosts[0].lstrip(".") if hosts else "localhost")


def probe(port, host_header, timeout=4):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    try:
        conn.request("GET", "/healthz", headers={"Host": host_header})
        resp = conn.getresponse()
        body = resp.read(4096)
        return resp.status == 200 and json.loads(body).get("status") == "ok"
    finally:
        conn.close()


def main():
    try:
        port, host = target()
        ok = probe(port, host)
    except (OSError, ValueError, http.client.HTTPException):
        ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
