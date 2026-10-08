> **Update:** Labs 1-5 now run on real engines too (see "Storyline 1" below) —
> not scripted lookup tables. Labs 6-10 were already real (your own sandbox code).

# AI Security Storyline Labs — hands-on rooms (TryHackMe / HackTheBox style)

Each case is a "room": the learner runs real commands in a sandbox terminal,
finds values in the tool output, types them as answers, unlocks evidence,
and captures a flag. Questions can't be answered until the matching
hands-on steps were actually run (they unlock from the lab's real ACTIONS).

## Run
```bash
cd labdemo
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## Flow per case
Briefing -> Hypothesis -> **Sandbox Room** (terminal + 5 tasks + flag) ->
Knowledge Check -> Evidence Mode (attack chain) -> Final Report -> Case Closed

## Storyline 1 (labs 1-5) — now real engines, not lookup tables
Each lab's mechanics live in `sandboxes1/labN_engine.py` and are wired into
`sandbox.py`. Every number the terminal prints is computed, not scripted:

- **Lab 1 ArtForge** — a real DCT watermark (`sandboxes1/lab1_engine.py`):
  the license ID is actually embedded into mid-frequency 8x8-block DCT
  coefficients via QIM, redundantly repeated and majority-vote decoded.
  `transform` runs a REAL JPEG encode/decode round-trip, real Gaussian pixel
  noise, and real crop+resize — not formulas. Detector threshold is 0.55
  (a real bit-detector reading at the 50% chance floor once destroyed, so
  "better than 50%" isn't a safe detection bar; 55% is) **and the decoded license ID
  must match exactly** -- a degraded image can still score above 0.55 with a garbled
  payload, and that is reported as `NOT VERIFIED`, not `DETECTED`.
  Tools: `artforge-gen`, `wm-verify`, `view`, `wm-compare`, `transform`, `verify-fix`
- **Lab 2 MedSync** — real federated learning (`lab2_engine.py`): an actual
  logistic-regression model trained with real gradient descent across 5
  simulated hospital nodes, aggregated with real FedAvg. Node 3's label-flip
  + gradient-boost attack genuinely collapses rare-condition recall after
  aggregation, and real trimmed-mean aggregation genuinely recovers it.
  Tools: `fl-architecture`, `accuracy-log`, `compare-updates`,
  `inspect-update`, `simulate-attack`, `aggregate`, `verify-fix`
- **Lab 3 FinGuard** — a real trained classifier (`lab3_engine.py`): a logistic
  regression over bag-of-words, trained at import with numpy gradient descent on a
  deterministic synthetic mail corpus (600 emails; the weights are learned, not typed in).
  Tokenization is a literal regex over raw text, so `mutate` applies REAL Unicode homoglyph
  substitution, zero-width-space insertion and hidden-HTML wrapping and the learned
  features genuinely disappear. Honest scope: the corpus is synthetic and the model is linear;
  each character trick alone (homoglyph, zero-width, hidden HTML) stays blocked and only homoglyph+zwsp slips under 0.80, while `--random50` padding alone also slips under (0.763) because it dilutes the signal rather than hiding it -- `verify-fix` shows normalization does not fix that (margin is
  thin and guarded by `tests/test_content_consistency.py`).
  Tools: `filter-scan [--explain]`, `mutate`, `diff`, `cat`, `verify-fix`
- **Lab 4 NovaRetail** — a real attention computation (`lab4_engine.py`): softmax over every
  context position with a recency penalty and an instruction bonus; "system-prompt attention"
  is the mass landing on the 60 system-prompt tokens. The bonus is calibrated once so the mass
  crosses the 0.15 floor at ~8,000 tokens. The incident transcript and `context-trace` are
  generated from the same function. It models one mechanism; it is not an LLM.
  Tools: `chat`, `pad`, `context`, `context-trace`, `extract-payload`, `verify-fix [--every N]`
- **Lab 5 VaultLine** — real signal processing (`lab5_engine.py`): clips are
  real synthesized waveforms (harmonic stack = identity/timbre, optional
  noise = breath/room texture). Similarity is real FFT-magnitude cosine
  similarity; liveness is a real noise-floor energy measurement above the
  harmonic range. `make-clone --noise N` lets you synthesize your own clone
  attempt and watch the real similarity/liveness trade-off.
  Tools: `auth-log`, `voiceid-verify`, `spectral-analysis`, `voiceid-config`, `make-clone`, `verify-fix`

Dependencies: `numpy`, `scipy`, `Pillow` (all in requirements.txt).

Free-text answers are graded by whole-word/phrase patterns (never loose substrings) and numeric answers are anchored; `tests/test_content_fixes.py` locks that in.

Type `help` in any terminal. Use the Hint button (costs score, uses your HINTS).

## Configuration (environment variables)
| Variable | Default | Purpose |
|---|---|---|
| `LABDEMO_SECRET_KEY` | generated once into `instance/secret_key` (0600) | Flask session signing key. Set this explicitly in production. |
| `LABDEMO_SECRET_KEY` length | >= 32 chars | Shorter keys are refused at startup. Generate: `python -c 'import secrets; print(secrets.token_hex(32))'` |
| `LABDEMO_SECURE_COOKIES` | off | Set to `1` when served over HTTPS: cookies become `Secure` **and** HSTS is sent. |
| `LABDEMO_TRUST_PROXY` | off | Set to `1` behind a reverse proxy that **overwrites** `X-Forwarded-For/Proto/Host` (enables `ProxyFix`: real client IP for rate limits, correct scheme/host for the CSRF origin check). Never enable it when exposed directly. |
| `LABDEMO_PROXY_HOPS` | `1` | How many trusted proxies are in front (1 = one proxy; 2 = CDN -> proxy -> app). Only read when `LABDEMO_TRUST_PROXY=1`; values outside 1-5 are refused at startup. Too low = every client looks like the proxy; too high = clients can spoof their IP. |
| `LABDEMO_ALLOWED_HOSTS` | any | Comma-separated Host allow-list, e.g. `labs.example.com`. Other Host headers get a 400. |
| `LABDEMO_PER_USER_FLAGS` | off | `1` = every learner gets a unique flag (`AF{...}` + HMAC suffix, see `expected_flag()` in `app.py`), so copied flags are detectable. |
| `LABDEMO_DB` | `instance/progress.db` | SQLite progress file. |
| `LABDEMO_INSTANCE` | `./instance` | Where the DB and secret key live. |
| `LABDEMO_HOST` / `LABDEMO_PORT` | `127.0.0.1` / `5000` | Bind address of the dev server (`python app.py`). Keep it on localhost unless you add HTTPS. |
| `LABDEMO_BIND` | `127.0.0.1:8000` | Bind address of gunicorn (`gunicorn.conf.py`). The Docker image sets `0.0.0.0:8000`. |
| `LABDEMO_ACCESS_LOG` | off | `1` = gunicorn access log to stdout (the proxy normally already logs). |

## Security model
- **CSRF**: every POST needs the session's token (forms carry a hidden field, the terminal JS sends `X-CSRF-Token`) and a same-origin `Origin`/`Referer`. Reset actions are POST-only.
- **Headers**: strict CSP (`script-src 'self'; style-src 'self'` -- no inline scripts **or styles**), `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`, CORP/COOP, `no-store` on dynamic pages, HSTS when `LABDEMO_SECURE_COOKIES=1`. The dev server and `gunicorn.conf.py` do not advertise server/Python versions.
- **CSRF origin check**: Origin/Referer must match scheme **and** host. Behind a proxy set `LABDEMO_TRUST_PROXY=1` (otherwise the check fails closed with a 403).
- **Resource limits**: per-sandbox caps (25 Lab 1 images, 1000 Lab 6 keys, 3000 Lab 7 reviews, 1000 per `inject`), a bounded LRU rate limiter that a key flood cannot reset, and an eviction scheme for session locks that never drops a held lock.
- **Evidence**: the browser only receives text for evidence the learner has unlocked.
- **Rate limits**: per session and per IP on the terminal, answer checker (also slows answer brute-forcing), hints and forms.
- **Input handling**: all numeric terminal arguments are clamped (NaN/inf rejected), commands are length/argument-limited, request bodies capped at 64 KB, stored text capped, per-session image/clip stores bounded. Nothing is ever passed to a shell, `eval` or `exec`; the terminal is a lookup into fixed command tables.
- **Flags**: the room page and `/answer` only reveal the flag after the room is completed server-side, in every lab. The Labs 6-10 terminals prove the exploit worked (`[!] ... exploit confirmed`) but never print the flag; it is released only by completing all room tasks, exactly like Labs 1-5.

## Production deployment
HTTPS is terminated by a reverse proxy; the app trusts the proxy's `X-Forwarded-*` headers (`LABDEMO_TRUST_PROXY=1`).
Two ready-made setups, both documented step by step in **[DEPLOYMENT.md](DEPLOYMENT.md)**:

- **Docker Compose + Caddy** (automatic Let's Encrypt): `cp .env.example .env`, edit, `docker compose up -d --build`.
- **Bare host + nginx** (`deploy/nginx.conf`) running `gunicorn -c gunicorn.conf.py app:app`.

Then prove it works end to end from outside:
```bash
python scripts/smoke_check.py --base https://labs.example.com
```
Use **one worker process** (threads are fine): the live terminal sandbox cache and the rate limiter are in-process,
so this app scales up (more threads/CPU), not out (more replicas).

## Tests
```bash
pip install -r requirements-dev.txt
python -m pytest tests -q
bandit -r . -x ./tests -q        # clean (intentional-simulation false positives carry `# nosec` + reason)
pip-audit -r requirements-prod.txt   # everything that ships in the image
```
CI (`.github/workflows/ci.yml`) runs all of this on every push/PR (Python 3.11-3.13), builds the Docker image and
smoke-checks the running container; `.github/workflows/audit.yml` re-runs `pip-audit` every Monday so new advisories
against pinned versions surface without a code change. Dependabot proposes updates weekly.

The suite solves every one of the 10 rooms end to end through the real HTTP routes (terminal commands -> answers -> flag),
checks that flags stay locked until the hands-on steps are done, and covers CSRF, headers, XSS escaping, rate limits,
hostile input, persistence across restarts, the Lab 1 exact-ID verifier rule, `/healthz`, proxy-hop handling, the storyline
registry, content consistency (every numeric answer a room expects is read off the real terminal output, all 10 labs), and `scripts/smoke_check.py` against real server processes (correct config passes; each misconfiguration fails).

## Demo tip
Live-demo Lab 1 (compress + noise breaks the watermark), then Lab 4
(pad 8500 tokens, then ask for the key). Answers are in rooms.py.

## Storyline 2 (labs 6-10) — hardened edition
These five (LexiGen, ShopWave, PopHealth, GateKey, AutoPilot) run the real sandbox classes in
`sandboxes2/` (their detection/limiter logic is unchanged; later hardening only added resource caps and
`nosec` annotations) and wrap them in terminal commands. Each also has a second decision point: reject a
red herring your colleague raises, scored separately.

**Exploit, then fix.** Task 5 of every room (Labs 1-10) ends with `verify-fix`: it replays the *same* attack
against a fixed version of the system and prints real numbers, so the learner proves the defence works (and sees
its cost or its limit) instead of only naming it. It is gated on having reproduced the exploit first, records a
`verified_fix` action (counted in the Investigation score), never prints a flag, and each room has one graded
question answered from its output.

| Lab | `verify-fix` replays... | What the learner reads off |
|---|---|---|
| 1 ArtForge | your compress+noise attack vs watermark **and** a signed C2PA-style manifest (real SHA-256 hard binding + HMAC signature) | four cases: metadata stripped / attacked with credentials / attacked and stripped / the disputed image. The manifest reports `MISMATCH` for pixel edits; stripped credentials defeat both layers (so "no credentials" = unverified) |
| 2 MedSync | the 6 poisoned rounds vs FedAvg and trimmed mean, with and without the attack | rare-condition accuracy per aggregator, and the cost: one honest update is always dropped |
| 3 FinGuard | five evasions vs normalize-before-classify (hidden-HTML strip, NFKC, zero-width removal, confusables fold) | confidence before/after, false positives on the 300 legitimate emails (0), and what normalization does *not* fix (random padding stays `ALLOW`) |
| 4 NovaRetail | the incident vs the system prompt re-injected every N tokens (`--every N`) | attention at the leak turn, worst-case attention over a 16,000-token context, token cost; too-large `--every` (8,000+) fails |
| 5 VaultLine | the clone vs an enforced liveness gate, then an attacker who adds a noise floor | the incident call is rejected, but a clone with noise >= 0.03 passes: liveness alone is a speed bump, add a second factor |
| 6 LexiGen | the 800-key scrape vs the layered limiter | keys registered, distinct outputs collected, coverage |
| 7 ShopWave | the 214 fake reviews vs the behavioral model | reviews discarded (incl. 1 genuine casualty), rank unchanged |
| 8 PopHealth | the averaging attack vs an enforced epsilon budget | queries served before the block, recovered value vs truth |
| 9 GateKey | the printed-photo spoof vs the depth-aware terminal | face/liveness/depth/IR scores, live face still admitted |
| 10 AutoPilot | both policies vs the delivery-credited reward | honest vs gaming reward, true on-time, complaints |

Honest scope for Labs 1-5: the fixes are real computations on the lab's own engines, but they are *models* of the
defence (e.g. a 7-entry confusables map instead of the full Unicode UTS #39 table; a sandbox HMAC key instead of
X.509 certificates; an attention model, not an LLM).

## Files
- `storylines.py` — the single registry that says which lab belongs to which storyline and wires its rooms + terminal together (`storyline_for(lab_id)`); `app.py` has no per-storyline branching
- `sandbox.py` / `rooms.py` — storyline 1 (labs 1-5) terminal tools (backed by `sandboxes1/` engines) + tasks
- `sandbox2.py` / `rooms2.py` — storyline 2 (labs 6-10) bridge to the real sandboxes + tasks
- `sandboxes2/labN_sandbox.py` — the storyline-2 sandbox code (original vulnerable/fixed logic; hardened only with resource caps)
- `labs/labN.py` — the content modules, labs 1-10 (Lab 1's detection threshold aligned to the engine; `verified_fix` action added to every lab)
- Progress is stored in SQLite (`instance/progress.db`) and survives restarts. The live terminal
  sandbox (generated images, simulator state) is in-memory and is rebuilt when you re-run the tools.
- `sandbox_common.py` / `rooms_common.py` — helpers shared by both storylines (command parsing/execution; the `Q`/`C`/`A`/`T` question builders).
- `Dockerfile`, `docker-compose.yml`, `deploy/Caddyfile`, `deploy/nginx.conf`, `.env.example`, `requirements-prod.txt` — deployment; `scripts/healthcheck.py` (container probe) and `scripts/smoke_check.py` (post-deploy verification); `.github/` — CI, weekly audit, Dependabot.
- `SECURITY.md` — findings from the security review and how each was fixed (with the regression test that locks it in)
- `requirements.lock` — exact dependency versions the suite was run against
- `store.py` — durable progress store · `security.py` — CSRF, headers/CSP, rate limits, secret key.
