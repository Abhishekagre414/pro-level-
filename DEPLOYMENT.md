# Deploying behind HTTPS

The app never terminates TLS itself. A reverse proxy does, and the app is told to trust exactly that proxy.
**Not exercised here:** the Caddy and nginx configs, the Docker build and Let's Encrypt issuance were written but never
run against a real host or registry (the authoring sandbox had no network, Docker, Caddy or nginx). What *was* run: the app
behind a throwaway TLS-terminating proxy, verified with `scripts/smoke_check.py`. Treat the first real deploy as the test,
and let the smoke check be your judge.

## Option A - Docker Compose + Caddy (recommended)
Prereqs: a host with Docker, a DNS A/AAAA record for your hostname pointing at it, ports 80/443 open.

```bash
cp .env.example .env              # set LABDEMO_DOMAIN and (recommended) LABDEMO_SECRET_KEY
docker compose up -d --build
docker compose ps                 # app should become "healthy" before caddy starts
python scripts/smoke_check.py --base https://$LABDEMO_DOMAIN
```
What you get: Caddy gets/renews the certificate and redirects http -> https; the app is on a private network and is
**not** published; it runs as a non-root user with all capabilities dropped; progress (SQLite) and, if you did not set
`LABDEMO_SECRET_KEY`, the signing key live in the `labdemo-instance` volume. Keep the `caddy-data` volume too, or you will
re-request certificates and can hit Let's Encrypt rate limits.

Staging cert / self-signed? `smoke_check.py --base https://host --insecure`.

## Option B - bare host + nginx
```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-prod.txt
export LABDEMO_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')   # keep it in a root-only env file
export LABDEMO_SECURE_COOKIES=1 LABDEMO_TRUST_PROXY=1 LABDEMO_PROXY_HOPS=1 LABDEMO_ALLOWED_HOSTS=labs.example.com
gunicorn -c gunicorn.conf.py app:app          # binds 127.0.0.1:8000
```
Install `deploy/nginx.conf` (edit the hostname, obtain certs with certbot), then run the smoke check. Run gunicorn under
systemd or a supervisor of your choice so it restarts on failure.

## Settings that must agree with the proxy
| Situation | Setting |
|---|---|
| One proxy in front (Caddy/nginx) | `LABDEMO_TRUST_PROXY=1`, `LABDEMO_PROXY_HOPS=1` |
| CDN -> your proxy -> app | `LABDEMO_PROXY_HOPS=2` (the proxy must *append*, the CDN must overwrite) |
| App reachable directly by clients | **never** set `LABDEMO_TRUST_PROXY` - clients could forge their IP and Host |
| Always, in production | `LABDEMO_SECURE_COOKIES=1` (Secure cookies + HSTS), `LABDEMO_ALLOWED_HOSTS=<your hostname>` |

If `smoke_check.py` reports a **403 on the legitimate POST**, the app is not seeing the public scheme/host: the proxy is not
sending `X-Forwarded-Proto/Host`, or `LABDEMO_TRUST_PROXY`/`LABDEMO_PROXY_HOPS` is wrong. A **400 everywhere** means
`LABDEMO_ALLOWED_HOSTS` does not list the hostname the proxy forwards.

## Operations
- **Probe:** `GET /healthz` -> `200 {"status":"ok"}` (503 if the progress DB is unreadable). No cookie, no learner data.
- **Update:** `git pull && docker compose up -d --build` (gunicorn drains in-flight requests on SIGTERM; learners lose only
  their live terminal state, which is rebuilt by re-running commands - progress is in SQLite).
- **Backup:** copy the SQLite file with its online-backup API rather than `cp` (the DB is in WAL mode):
  `docker compose exec app python -c "import sqlite3; s=sqlite3.connect('/app/instance/progress.db'); s.backup(sqlite3.connect('/app/instance/backup.db'))"`
  then copy `backup.db` out of the volume. If you rely on the generated key file rather than `LABDEMO_SECRET_KEY`, back up
  `secret_key` too - losing it logs everyone out and invalidates per-user flags.
- **Dependencies:** `.github/workflows/audit.yml` runs `pip-audit` weekly and CI runs it on every change. When it fails:
  bump the vulnerable pin in `requirements.lock` (and the range in `requirements.txt` if needed), run the suite, redeploy.
- **Limits by design:** one process, one instance. The terminal sandbox cache and the rate limiter are in-process, so don't run
  replicas behind a load balancer; add threads/CPU instead.
