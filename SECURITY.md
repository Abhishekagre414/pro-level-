# Security review — findings and fixes (2 Oct 2026)

Method: existing suite, bandit, pip-audit, ~100 targeted attack checks (CSRF, headers, XSS, traversal, gating,
malformed input, cookies, rate limits), 12,600 fuzzed terminal inputs, concurrency stress, live-server run.

| # | Severity | Finding | Fix | Regression test |
|---|---|---|---|---|
| 1 | Medium | Unbounded per-session memory/CPU (Lab 1 `artforge-gen` 0.5 MB/image; Lab 6 key store; Lab 7 `inject` re-ranked all reviews every call) | Caps: 25 images, 1000 keys, 3000 reviews (1000/call) | `test_lab1_*`, `test_lab6_*`, `test_lab7_*` |
| 2 | Medium | Outdated Pillow 12.1.1 (6 advisories, fixed in 12.3.0) allowed by `Pillow>=10`; `click` 8.3.1 advisory | `Pillow>=12.3.0`, `click>=8.3.3`, exact `requirements.lock`, `pip-audit` clean | (CI on every change + weekly schedule: `pip-audit -r requirements-prod.txt`) |
| 3 | Low | Non-ASCII CSRF token → HTTP 500 (`hmac.compare_digest` TypeError) | Compare as UTF-8 bytes | `test_non_ascii_csrf_token_gets_400_not_500` |
| 4 | Low | Rate limiter `clear()` at 20k keys reset every counter | Bounded LRU; active counters survive floods | `test_rate_limiter_flood_*` |
| 5 | Low | `LABDEMO_SECRET_KEY=abc` accepted | Refuse keys < 32 chars | `test_weak_env_secret_key_refused` |
| 6 | Low | Existing key file kept loose permissions / short key reused | `fchmod`/`chmod` 0600, short key regenerated | `test_*key_file*` |
| 7 | Low | Origin check ignored scheme; default proxy setups 403'd every POST | Scheme+host compared; opt-in `LABDEMO_TRUST_PROXY`, `LABDEMO_ALLOWED_HOSTS` | `test_*origin*`, `test_proxyfix_*`, `test_allowed_hosts_*` |
| 8 | Low | Locked evidence (title, text, required actions) shipped in page source | Server sends only unlocked evidence; JS merges it from terminal responses | `test_locked_evidence_*`, `test_unlocked_evidence_*` |
| 9 | Low | Lab 8 `query <bad id>` → KeyError + logged traceback per request (log flooding) | Validate record names | `test_lab8_unknown_record_*` |
| 10 | Low | Session-lock table `clear()` could let one session run requests in parallel | Evict only unheld locks | `test_session_lock_eviction_*` |
| 11 | Info | CSP allowed `'unsafe-inline'` styles | Inline styles removed (`data-*` + `ui.js`, `hidden`); CSP `style-src 'self'` | `test_csp_*`, `test_pages_use_no_inline_*` |
| 12 | Info | Static identical flags in source | Opt-in per-user HMAC flags (`LABDEMO_PER_USER_FLAGS=1`) | `test_per_user_flags_*` |
| 13 | Info | Server banner, no HSTS/CORP, unpinned deps, pytest in runtime reqs | Quiet banner, `gunicorn.conf.py`, HSTS (secure mode), CORP, ranges + lock, dev deps split | `test_hsts_*`, `test_dev_server_banner_*` |
| 14 | Info | bandit: 1 High + 5 Low | All false positives (simulation fixtures); annotated `# nosec <id> - reason` (comments only) | bandit clean |

Follow-up (3 Oct 2026): Labs 6-10 terminals no longer print the flag (it is released only by completing the room, as in Labs 1-5), and free-text answer patterns were converted from substring to whole-word matching (`tests/test_content_fixes.py`).

Follow-up (3 Oct 2026, 2): Labs 1-5 now also have a graded `verify-fix` step (C2PA-style manifest, trimmed-mean replay, normalize-first filter, system-prompt re-injection, enforced liveness). Like Labs 6-10 it is gated on reproducing the exploit, never prints a flag, and every number comes from the lab's own engine.

Residual / by design: flags are static unless `LABDEMO_PER_USER_FLAGS=1`; the limiter is per-process (run one worker);
the rate limiter evicts the least-recently-used key under >20k distinct-key pressure (an idle counter is forgotten,
active ones are not); `LABDEMO_TRUST_PROXY=1` must only be used behind a proxy that overwrites `X-Forwarded-*`.
