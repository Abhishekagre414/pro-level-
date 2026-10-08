# -*- coding: utf-8 -*-
"""
Terminal bridge for storyline 2 (labs 6-10). Unlike storyline 1's sandbox.py,
these commands call the REAL systems shipped in sandboxes2/*.py (vulnerable and
fixed modes of the same classes), so the exploit and the fix are the actual
logic, not a re-implementation. `verify-fix` replays each exploit on the fixed mode.
"""
import importlib.util
import os

from sandbox_common import int_arg, num, parse, rec, state as st  # noqa: E402,F401

_HERE = os.path.dirname(os.path.abspath(__file__))

# The sandbox proves the exploit worked; the FLAG itself is only released by the room once every
# question is answered, exactly like labs 1-5 (see app.answer / flag_for).
FLAG_NOTE = "The flag is released when you complete all room tasks."


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


S6 = _load("lab6_sandbox", os.path.join(_HERE, "sandboxes2", "lab6_sandbox.py"))
S7 = _load("lab7_sandbox", os.path.join(_HERE, "sandboxes2", "lab7_sandbox.py"))
S8 = _load("lab8_sandbox", os.path.join(_HERE, "sandboxes2", "lab8_sandbox.py"))
S9 = _load("lab9_sandbox", os.path.join(_HERE, "sandboxes2", "lab9_sandbox.py"))
S10 = _load("lab10_sandbox", os.path.join(_HERE, "sandboxes2", "lab10_sandbox.py"))


# ============================================================ LAB 6 LexiGen
F6 = {
    "verified_baseline_limit": "push one key to its limit: test-limit",
    "viewed_suspect_logs": "review the traffic logs: logs",
    "tested_key_rotation": "test key rotation: test-keys 5",
    "tested_ip_rotation": "test IP rotation: test-ips 5",
    "compared_identifiers": "compare what each test showed: compare",
    "reproduced_scrape": "run the scrape: scrape",
    "compared_traffic_signature": "compare cadence: traffic-compare",
    "inspected_limiter_config": "check the config: limiter-config",
}


def _l6_api(prog):
    d = st(prog)
    if "api" not in d:
        d["api"] = S6.MeteredModelAPI(mode="per_key")
        d["clock"] = 0.0
        d["collected"] = {}
    return d["api"]


def l6_test_limit(mod, prog, a):
    d = st(prog)
    api = _l6_api(prog)
    k = api.register_key(source="10.0.0.5")
    served = 0
    try:
        for i in range(S6.DOCUMENTED_LIMIT_RPM + 5):
            api.query(k, f"probe_{i}", source="10.0.0.5")
            served += 1
    except S6.RateLimitError as e:
        note = rec(mod, prog, "verified_baseline_limit", F6)
        return (f"Registered key {k}\nFired {served + 1} requests in one minute.\n"
                f"Request {served + 1}: {e}\nDocumented limit ({S6.DOCUMENTED_LIMIT_RPM}/min) enforced correctly for a single key." + note)
    return f"Sent {served} requests, no throttle triggered (unexpected)."


def l6_logs(mod, prog, a):
    note = rec(mod, prog, "viewed_suspect_logs", F6)
    return ("Suspect-period traffic log summary\n"
            "  window     : 2026-06-30 02:10 -> 2026-07-03 02:10 (~72h)\n"
            f"  requests   : {mod.SCRAPE_VOLUME_OBSERVED:,} successful\n"
            "  source     : one /24 subnet (10.0.0.0/24)\n"
            "  keys used  : ~800 distinct free-tier keys, round-robin\n"
            "  per-key rate: each individual key stayed under 60/min" + note)


MAX_L6_KEYS = 1000        # keys one learner's sandbox may register (each test-keys call adds up to 100)
MAX_L7_REVIEWS = 3000     # fake reviews one learner may inject in total (re-ranking is O(reviews))
MAX_L7_PER_CALL = 1000


def _l6_full(api, adding):
    if len(api.registered_keys) + adding > MAX_L6_KEYS:
        return (f"error: sandbox limit reached ({MAX_L6_KEYS} API keys). "
                "Use 'restart this case' to start with a clean sandbox.")
    return None


def l6_test_keys(mod, prog, a):
    n = int_arg(a[0] if a else 5, 5, 1, 100)
    api = _l6_api(prog)
    full = _l6_full(api, n)
    if full:
        return full
    keys = [api.register_key(source="10.0.0.5") for _ in range(n)]
    served = 0
    for i, k in enumerate(keys):
        for j in range(S6.DOCUMENTED_LIMIT_RPM):
            api.query(k, f"rot_{i}_{j}", source="10.0.0.5")
            served += 1
    note = rec(mod, prog, "tested_key_rotation", F6)
    return (f"Registered {n} keys from 10.0.0.5, sent {S6.DOCUMENTED_LIMIT_RPM} reqs on each.\n"
            f"Total served: {served} (each key individually under the {S6.DOCUMENTED_LIMIT_RPM}/min cap).\n"
            "No key was throttled below its own limit -- aggregate throughput scales with key count." + note)


def l6_test_ips(mod, prog, a):
    n = int_arg(a[0] if a else 5, 5, 1, 100)
    api = _l6_api(prog)
    full = _l6_full(api, 1)
    if full:
        return full
    k = api.register_key(source="10.0.0.9")
    ok = 0
    blocked_at = None
    for i in range(S6.DOCUMENTED_LIMIT_RPM + 5):
        src = f"10.0.{i % n}.{i}"
        try:
            api.query(k, f"ip_{i}", source=src)
            ok += 1
        except S6.RateLimitError:
            blocked_at = ok + 1
            break
    note = rec(mod, prog, "tested_ip_rotation", F6)
    return (f"Same key, {n} rotating source IPs.\n"
            f"Requests before throttle: {ok}" + (f" (blocked on request {blocked_at})" if blocked_at else "") +
            f"\nRotating the IP did NOT help -- still capped at {S6.DOCUMENTED_LIMIT_RPM}/min because the limiter tracks the key." + note)


def l6_compare(mod, prog, a):
    note = rec(mod, prog, "compared_identifiers", F6)
    return ("Comparison:\n  rotate keys, same IP  -> throughput multiplies (NOT limited)\n"
            "  rotate IP, same key   -> still capped at 60/min (limited)\n"
            "Conclusion: the limiter keys on the API key only. It is blind to source." + note)


def l6_scrape(mod, prog, a):
    _, fl = parse(a)
    minutes = int_arg(fl.get("minutes"), 60, 1, 1440)
    d = st(prog)
    d["api"] = S6.MeteredModelAPI(mode="per_key")
    api = d["api"]
    import itertools
    keys = [api.register_key(source="10.0.0.5") for _ in range(800)]
    cycle = itertools.cycle(keys)
    collected, prompts, pi = {}, [f"prompt_{i}" for i in range(S6.MODEL_CORPUS_SIZE)], 0
    clock = 0.0
    for m in range(minutes):
        per_key = {}
        for _ in range(len(keys) * S6.DOCUMENTED_LIMIT_RPM):
            if pi >= len(prompts):
                break
            key = next(cycle)
            if per_key.get(key, 0) >= S6.DOCUMENTED_LIMIT_RPM:
                continue
            try:
                out = api.query(key, prompts[pi], source="10.0.0.5")
                collected[prompts[pi]] = out
                per_key[key] = per_key.get(key, 0) + 1
                pi += 1
            except S6.RateLimitError:
                continue
        if pi >= len(prompts):
            break
    d["collected"] = collected
    coverage = api.scrape_coverage(collected)
    note = rec(mod, prog, "reproduced_scrape", F6)
    out = (f"Scraped with {len(keys)} rotating keys over {minutes} simulated minutes.\n"
           f"Served: {api.total_served}   Distinct pairs collected: {len(collected)}\n"
           f"Coverage: {coverage:.0%} (clone threshold {S6.SCRAPE_THRESHOLD:.0%})")
    result = api.request_flag(collected)
    if result:
        _flag, token = result
        out += f"\n\n[!] MODEL CLONED -- exploit confirmed (release token {token}). {FLAG_NOTE}"
    else:
        out += "\n\nNot enough coverage yet to clone the model."
    return out + note


def l6_traffic_compare(mod, prog, a):
    note = rec(mod, prog, "compared_traffic_signature", F6)
    return ("Signature comparison: suspect logs vs. your reproduced scrape\n"
            "  key-rotation cadence : round-robin across ~800 keys  -- MATCH\n"
            "  per-key rate         : each key < 60/min             -- MATCH\n"
            "  timing               : sustained ~72h burst          -- MATCH\n"
            "Conclusion: the suspect traffic matches your reproduced key-rotation scrape." + note)


def l6_config(mod, prog, a):
    note = rec(mod, prog, "inspected_limiter_config", F6)
    return (f"Limiter config\n  mode         : per_key\n  tracks       : API key only\n"
            f"  ignores      : source IP / device\n  documented   : {S6.DOCUMENTED_LIMIT_RPM}/min per key" + note)


LAB6 = {"prompt": "diya@lexigen-sandbox", "cmds": {
    "test-limit": l6_test_limit, "logs": l6_logs, "test-keys": l6_test_keys, "test-ips": l6_test_ips,
    "compare": l6_compare, "scrape": l6_scrape, "traffic-compare": l6_traffic_compare, "limiter-config": l6_config,
}, "help": """Tools in this sandbox
  test-limit               push one API key to its documented limit
  logs                      view the suspect-period traffic logs
  test-keys <n>             rotate n API keys from one source
  test-ips <n>              rotate n source IPs on one key
  compare                   compare what each test showed
  scrape [--minutes N]      reproduce the full scrape (default 60 min)
  traffic-compare           compare your scrape's signature to the suspect logs
  limiter-config            inspect the rate-limiter configuration"""}


# ============================================================ LAB 7 ShopWave
F7 = {
    "reviewed_ranking_signals": "check the leaderboard: leaderboard",
    "viewed_disputed_seller": "look at the seller: seller seller_41",
    "inspected_review_activity": "list its reviews: reviews seller_41",
    "compared_to_genuine_seller": "compare it: compare-seller seller_5",
    "traced_accounts": "trace the accounts: trace-accounts",
    "reproduced_signal_shift": "inject reviews: inject 214 48",
    "compared_timeline": "check the timeline: timeline",
    "inspected_authenticity_score": "check the authenticity model: authenticity-score",
}


def _l7_market(prog):
    d = st(prog)
    if "sellers" not in d:
        d["sellers"], d["target"] = S7.build_market()
        d["ranker"] = S7.ShopWaveRanker(mode="naive")
    return d["sellers"], d["target"], d["ranker"]


def l7_leaderboard(mod, prog, a):
    sellers, target, ranker = _l7_market(prog)
    rank = ranker.rank_of(sellers, target.sid)
    note = rec(mod, prog, "reviewed_ranking_signals", F7)
    return f"Category leaderboard computed. {target.sid} is currently rank #{rank} of {len(sellers)}." + note


def l7_seller(mod, prog, a):
    if not a:
        return "usage: seller <seller_id>"
    sellers, target, ranker = _l7_market(prog)
    s = next((x for x in sellers if x.sid == a[0]), None)
    if not s:
        return f"seller: {a[0]}: not found"
    note = rec(mod, prog, "viewed_disputed_seller", F7) if s.sid == target.sid else ""
    return (f"{s.sid}: {len(s.reviews)} reviews, current score {ranker.score(s):.2f}, "
            f"rank #{ranker.rank_of(sellers, s.sid)}") + note


def l7_reviews(mod, prog, a):
    if not a:
        return "usage: reviews <seller_id>"
    sellers, target, ranker = _l7_market(prog)
    s = next((x for x in sellers if x.sid == a[0]), None)
    if not s:
        return f"reviews: {a[0]}: not found"
    sample = s.reviews[:5]
    lines = [f"  stars={r.stars:.1f} age_days={r.account['age_days']} verified={r.account['verified_purchase']} ip={r.account['ip']}" for r in sample]
    note = rec(mod, prog, "inspected_review_activity", F7) if s.sid == target.sid else ""
    return f"{s.sid}: {len(s.reviews)} reviews (showing first {len(sample)})\n" + "\n".join(lines) + note


def l7_compare_seller(mod, prog, a):
    if not a:
        return "usage: compare-seller <genuine_seller_id>"
    sellers, target, ranker = _l7_market(prog)
    g = next((x for x in sellers if x.sid == a[0]), None)
    if not g:
        return f"compare-seller: {a[0]}: not found"
    note = rec(mod, prog, "compared_to_genuine_seller", F7)
    return (f"{target.sid}: {len(target.reviews)} reviews, all IPs/cohorts near-unique per genuine buyer.\n"
            f"{g.sid}: {len(g.reviews)} reviews, same pattern -- unique IP/cohort per review.\n"
            f"(Disputed seller has no injected reviews yet -- run 'inject' to reproduce the shift.)" + note)


def l7_trace_accounts(mod, prog, a):
    sellers, target, ranker = _l7_market(prog)
    note = rec(mod, prog, "traced_accounts", F7)
    injected = [r for r in target.reviews if r.account.get("cohort") == "sock-farm-1"]
    if not injected:
        return "No injected reviews yet on this seller -- account trace has nothing coordinated to show. Try 'inject' first, then re-run this." + note
    ips = {r.account["ip"] for r in injected}
    return (f"{len(injected)} reviews share cohort 'sock-farm-1'.\n"
            f"They funnel through only {len(ips)} distinct IPs (should be ~{len(injected)} for genuine buyers).\n"
            "Accounts were all created close together -- classic sockpuppet signature." + note)


def l7_inject(mod, prog, a):
    n = int_arg(a[0] if a else S7.FAKE_REVIEW_COUNT, S7.FAKE_REVIEW_COUNT, 1, MAX_L7_PER_CALL)
    hours = int_arg(a[1] if len(a) > 1 else S7.SPIKE_WINDOW_HOURS, S7.SPIKE_WINDOW_HOURS, 1, 720)
    sellers, target, ranker = _l7_market(prog)
    if len(target.reviews) + n > MAX_L7_REVIEWS:
        return (f"error: sandbox limit reached (at most {MAX_L7_REVIEWS} reviews on a listing). "
                "Use 'restart this case' to start with a clean sandbox.")
    before = ranker.rank_of(sellers, target.sid)
    for i in range(n):
        target.reviews.append(S7.Review(
            stars=5.0, hour=(i * hours // max(1, n)),
            account={"age_days": 45, "verified_purchase": True, "ip": f"sock-{i % 8}",
                     "created_hour": i % 24, "cohort": "sock-farm-1"}))
    after = ranker.rank_of(sellers, target.sid)
    note = rec(mod, prog, "reproduced_signal_shift", F7)
    out = f"Injected {n} fake 5-star reviews over {hours}h.\nRank: #{before} -> #{after}"
    result = ranker.request_flag(sellers, target.sid)
    if result:
        _flag, token = result
        out += f"\n\n[!] RANKING POISONED -- exploit confirmed (release token {token}). {FLAG_NOTE}"
    return out + note


def l7_timeline(mod, prog, a):
    note = rec(mod, prog, "compared_timeline", F7)
    return ("Timeline: the review spike window lines up exactly with the overnight rank jump --\n"
            "no other signal (price, catalog, ad spend) changed in that window." + note)


def l7_authscore(mod, prog, a):
    note = rec(mod, prog, "inspected_authenticity_score", F7)
    return ("Authenticity model in production: NAIVE\n"
            "  checks: account age >= 30d AND verified purchase flag\n"
            "  blind to: account-creation cohort, IP/device clustering, review velocity vs. history\n"
            "A behavioral model (cohort + IP clustering + velocity-vs-history) would catch this." + note)


LAB7 = {"prompt": "diya@shopwave-sandbox", "cmds": {
    "leaderboard": l7_leaderboard, "seller": l7_seller, "reviews": l7_reviews,
    "compare-seller": l7_compare_seller, "trace-accounts": l7_trace_accounts,
    "inject": l7_inject, "timeline": l7_timeline, "authenticity-score": l7_authscore,
}, "help": """Tools in this sandbox
  leaderboard                    compute the category leaderboard
  seller <id>                    inspect one seller (try seller_41, seller_5)
  reviews <id>                   list a seller's reviews
  compare-seller <genuine_id>    compare disputed seller to a genuine one
  trace-accounts                 trace reviewer account overlap
  inject <n> <hours>              inject n fake reviews over the given span
  timeline                       compare spike timing to the rank jump
  authenticity-score              inspect the authenticity check model"""}


# ============================================================ LAB 8 PopHealth
F8 = {
    "reviewed_dp_policy": "read the policy: policy",
    "ran_single_query": "run one query: query target_patient patient_0 patient_1",
    "viewed_query_log": "check the log: query-log",
    "ran_repeated_queries": "repeat it: repeat-query 500",
    "averaged_results": "average them: average",
    "reproduced_reidentification": "re-identify: reidentify",
    "compared_to_single_query": "compare to one query: compare-single",
    "inspected_budget_enforcement": "check budget mode: budget-config",
}


def _l8_api(prog):
    d = st(prog)
    if "api" not in d:
        d["data"] = S8.build_dataset()
        d["api"] = S8.DPAnalyticsAPI(d["data"], mode="unenforced")
        d["samples"] = []
        d["cover"] = [f"patient_{i}" for i in range(S8.SUBGROUP_SIZE - 1)]
        d["subgroup"] = ["target_patient"] + d["cover"]
    return d["api"]


def l8_policy(mod, prog, a):
    note = rec(mod, prog, "reviewed_dp_policy", F8)
    return (f"PopHealth DP policy (published)\n  per-query epsilon : {S8.PER_QUERY_EPSILON}\n"
            f"  stated total budget cap : {S8.STATED_BUDGET_CAP}\n"
            "  claim: 'the budget makes repeated querying safe'" + note)


def l8_query(mod, prog, a):
    api = _l8_api(prog)
    d = st(prog)
    subgroup = list(a) if a else d["subgroup"]
    unknown = [n for n in subgroup if n not in d["data"]]
    if unknown:                      # validate instead of letting a KeyError (and a logged traceback) happen
        shown = ", ".join(x[:24] for x in unknown[:3])
        return f"query: unknown record(s): {shown}. Names look like patient_0 or target_patient."
    try:
        r = api.mean_query(subgroup)
    except S8.PrivacyBudgetExceeded as e:
        return f"Blocked: {e}"
    note = rec(mod, prog, "ran_single_query", F8)
    return f"mean_query({subgroup}) = {r:.2f}   (spent epsilon so far: {api.spent_epsilon:.1f})" + note


def l8_query_log(mod, prog, a):
    api = _l8_api(prog)
    note = rec(mod, prog, "viewed_query_log", F8)
    return (f"Query log\n  queries run       : {api.query_count}\n"
            f"  epsilon spent     : {api.spent_epsilon:.1f}\n"
            f"  cumulative cap enforced? : {'yes' if api.mode == 'enforced' else 'NO'}" + note)


def l8_repeat(mod, prog, a):
    n = int_arg(a[0] if a else 500, 500, 1, 5000)
    api = _l8_api(prog)
    d = st(prog)
    got, blocked = 0, False
    for _ in range(n):
        try:
            d["samples"].append(api.mean_query(d["subgroup"]))
            got += 1
        except S8.PrivacyBudgetExceeded:
            blocked = True
            break
    note = rec(mod, prog, "ran_repeated_queries", F8)
    return (f"Ran {got} queries on {d['subgroup']}.\n"
            f"Total samples collected: {len(d['samples'])}   epsilon spent: {api.spent_epsilon:.1f}"
            + (" [budget exhausted]" if blocked else "")) + note


def l8_average(mod, prog, a):
    d = st(prog)
    if not d.get("samples"):
        return "No samples yet -- run 'repeat-query <n>' first."
    est = sum(d["samples"]) / len(d["samples"])
    d["est_mean"] = est
    note = rec(mod, prog, "averaged_results", F8)
    return f"Averaged {len(d['samples'])} noisy answers -> estimated subgroup mean = {est:.2f}" + note


def l8_reidentify(mod, prog, a):
    d = st(prog)
    api = d["api"]
    if "est_mean" not in d:
        return "Run 'average' first."
    known_sum = sum(d["data"][n] for n in d["cover"])
    recovered = d["est_mean"] * len(d["subgroup"]) - known_sum
    d["recovered"] = recovered
    note = rec(mod, prog, "reproduced_reidentification", F8)
    out = f"Recovered target_patient value estimate: {recovered:.2f}"
    result = api.request_flag(recovered)
    if result:
        _flag, token = result
        out += f"\n\n[!] INDIVIDUAL RE-IDENTIFIED -- exploit confirmed (release token {token}). {FLAG_NOTE}"
    else:
        out += "\n\nNot within tolerance of the true value yet -- try more queries (repeat-query)."
    return out + note


def l8_compare_single(mod, prog, a):
    d = st(prog)
    if "recovered" not in d:
        return "Run 'reidentify' first."
    one = None
    try:
        api2 = S8.DPAnalyticsAPI(d["data"], mode="unenforced", seed=7)
        one = api2.mean_query(d["subgroup"]) * len(d["subgroup"]) - sum(d["data"][n] for n in d["cover"])
    except Exception:
        one = None
    if one is None:
        return "Could not compute the single-query estimate. Run 'reidentify' again first."
    true_val = d["data"]["target_patient"]
    note = rec(mod, prog, "compared_to_single_query", F8)
    return (f"Single-query estimate : {one:.1f}  (error {abs(one - true_val):.1f})\n"
            f"Averaged estimate     : {d['recovered']:.2f}  (error {abs(d['recovered'] - true_val):.2f})\n"
            "One query is noise; hundreds of queries converge on the truth." + note)


def l8_budget_config(mod, prog, a):
    note = rec(mod, prog, "inspected_budget_enforcement", F8)
    return (f"Budget enforcement mode: {S8.BUDGET_MODE}\n"
            "  'unenforced' = epsilon is tracked per-query display only, never capped cumulatively.\n"
            "  'enforced'   = cumulative epsilon is capped, queries blocked once the cap is hit." + note)


LAB8 = {"prompt": "diya@pophealth-sandbox", "cmds": {
    "policy": l8_policy, "query": l8_query, "query-log": l8_query_log, "repeat-query": l8_repeat,
    "average": l8_average, "reidentify": l8_reidentify, "compare-single": l8_compare_single,
    "budget-config": l8_budget_config,
}, "help": """Tools in this sandbox
  policy                      read the published DP policy
  query [names...]            run one mean query (default: the target subgroup)
  query-log                    view cumulative query stats
  repeat-query <n>            run n repeated queries on the target subgroup
  average                      average the collected samples
  reidentify                   recover the target's value from the average
  compare-single                compare single-query vs averaged error
  budget-config                 inspect enforcement mode"""}


# ============================================================ LAB 9 GateKey
F9 = {
    "reviewed_terminal_design": "read the design: terminal-info",
    "enrolled_test_face": "enroll a live face: enroll",
    "viewed_incident_log": "check the log: incident-log",
    "tested_photo_spoof": "test a photo: test-photo --dpi 1200 --gloss 0.35",
    "tested_video_replay": "test a replay: test-video",
    "compared_scores": "compare the scores: compare-scores",
    "reproduced_spoof": "run the spoof: spoof --dpi 1200 --gloss 0.35",
    "inspected_liveness_config": "check the config: liveness-config",
}


def _l9_term(prog):
    d = st(prog)
    if "term" not in d:
        d["term"] = S9.GateKeyTerminal(mode="texture_only")
        d["last"] = {}
    return d["term"]


def l9_info(mod, prog, a):
    note = rec(mod, prog, "reviewed_terminal_design", F9)
    return (f"GateKey terminal thresholds\n  face-match >= {S9.FACE_MATCH_THRESHOLD}\n"
            f"  liveness   >= {S9.LIVENESS_THRESHOLD}\n  mode: texture_only (2D liveness)" + note)


def l9_enroll(mod, prog, a):
    term = _l9_term(prog)
    granted = term.authenticate(S9.live_face())
    note = rec(mod, prog, "enrolled_test_face", F9)
    return f"Live enrolled face authenticated: {granted}" + note


def l9_incident_log(mod, prog, a):
    note = rec(mod, prog, "viewed_incident_log", F9)
    return ("Incident log\n  entry #4471  auth=FACE  result=GRANTED  capture=unknown (disputed)\n"
            "  client claims a printed photo was held up to the terminal at the time of entry." + note)


def l9_test_photo(mod, prog, a):
    _, fl = parse(a)
    dpi = int_arg(fl.get("dpi"), 800, 1, 4000)
    gloss = num(fl.get("gloss"), 0.30, 0.0, 1.0)
    term = _l9_term(prog)
    c = S9.Capture(kind="printed_photo", print_dpi=dpi, gloss=gloss, flatness=0.95,
                   screen_bezel=0.0, ir_reflectance=0.15, micro_motion=0.05, depth=0.08)
    match, live = term._match_score(c), term._texture_liveness(c)
    granted = term.authenticate(c)
    st(prog)["last"] = {"c": c, "match": match, "live": live}
    note = rec(mod, prog, "tested_photo_spoof", F9)
    return (f"Printed photo  dpi={dpi} gloss={gloss}\n  match={match:.2f}  liveness={live:.2f}  "
            f"granted={granted}" + note)


def l9_test_video(mod, prog, a):
    term = _l9_term(prog)
    c = S9.Capture(kind="video_replay", print_dpi=None, gloss=0.4, flatness=0.6,
                   screen_bezel=0.08, ir_reflectance=0.2, micro_motion=0.3, depth=0.1)
    match, live = term._match_score(c), term._texture_liveness(c)
    granted = term.authenticate(c)
    note = rec(mod, prog, "tested_video_replay", F9)
    return (f"Screen video replay (bezel visible)\n  match={match:.2f}  liveness={live:.2f}  "
            f"granted={granted}\n  (screen bezel drags both scores down)" + note)


def l9_compare_scores(mod, prog, a):
    term = _l9_term(prog)
    live = S9.live_face()
    lm, ll = term._match_score(live), term._texture_liveness(live)
    note = rec(mod, prog, "compared_scores", F9)
    return (f"{'capture':<16}{'match':>8}{'liveness':>10}\n"
            f"{'live face':<16}{lm:>8.2f}{ll:>10.2f}\n"
            "printed photo (high dpi)  ~0.95    ~0.90   <- clears both on texture-only\n"
            "video replay (bezel)      lower     lower  <- bezel penalty catches it" + note)


def l9_spoof(mod, prog, a):
    _, fl = parse(a)
    dpi = int_arg(fl.get("dpi"), 1200, 1, 4000)
    gloss = num(fl.get("gloss"), 0.35, 0.0, 1.0)
    term = _l9_term(prog)
    c = S9.Capture(kind="printed_photo", print_dpi=dpi, gloss=gloss, flatness=0.95,
                   screen_bezel=0.0, ir_reflectance=0.15, micro_motion=0.05, depth=0.08)
    granted = term.authenticate(c)
    note = rec(mod, prog, "reproduced_spoof", F9)
    out = f"Presenting crafted print (dpi={dpi}, gloss={gloss}) to the terminal... granted={granted}"
    result = term.request_flag(c)
    if result:
        _flag, token = result
        out += f"\n\n[!] LIVENESS SPOOFED -- exploit confirmed (release token {token}). {FLAG_NOTE}"
    else:
        out += "\n\nNot granted -- try a higher --dpi (try 1200-2000) or adjust --gloss (0.3-0.45)."
    return out + note


def l9_liveness_config(mod, prog, a):
    note = rec(mod, prog, "inspected_liveness_config", F9)
    return (f"Liveness config\n  mode: texture_only\n  checks: 2D texture + gloss only\n"
            f"  NEVER checked: depth (threshold {S9.DEPTH_THRESHOLD}), IR reflectance band "
            f"({S9.IR_LO}-{S9.IR_HI})\n  A flat print has near-zero depth and print-like IR." + note)


LAB9 = {"prompt": "diya@gatekey-sandbox", "cmds": {
    "terminal-info": l9_info, "enroll": l9_enroll, "incident-log": l9_incident_log,
    "test-photo": l9_test_photo, "test-video": l9_test_video, "compare-scores": l9_compare_scores,
    "spoof": l9_spoof, "liveness-config": l9_liveness_config,
}, "help": """Tools in this sandbox
  terminal-info                  read the terminal's design/thresholds
  enroll                         authenticate a genuine live face (baseline)
  incident-log                   view the disputed access log entry
  test-photo --dpi N --gloss G   present a printed-photo capture
  test-video                     present a screen-replay capture
  compare-scores                 compare live vs. photo vs. replay scores
  spoof --dpi N --gloss G        attempt to open the door with a crafted print
  liveness-config                inspect what the liveness check does NOT check"""}


# =========================================================== LAB 10 AutoPilot
F10 = {
    "reviewed_reward_function": "read the config: reward-config",
    "ran_normal_scenario": "run honest: run-honest",
    "compared_score_vs_reality": "compare: compare-reality",
    "ran_tight_scenario": "run gamed: run-gamed",
    "observed_shortcut": "see the shortcut: observe-shortcut",
    "reproduced_exploit": "confirm it: confirm-hack",
    "traced_loophole": "trace it: trace-loophole",
    "inspected_reward_config": "audit it: reward-audit",
}


def l10_config(mod, prog, a):
    note = rec(mod, prog, "reviewed_reward_function", F10)
    return ("Reward function config\n  mode: dispatch\n  credit(job) = 1.0 if job.dispatch_ontime else 0.0\n"
            "  (credits at DISPATCH, not at confirmed DELIVERY)" + note)


def l10_run_honest(mod, prog, a):
    d = st(prog)
    d["honest"] = S10.run_policy("honest", "dispatch")
    note = rec(mod, prog, "ran_normal_scenario", F10)
    h = d["honest"]
    return (f"Honest policy, dispatch reward\n  reward_score={h['reward_score']:.2f}  "
            f"true_ontime={h['true_ontime']:.2f}  complaints={h['complaints']:.2f}" + note)


def l10_compare_reality(mod, prog, a):
    d = st(prog)
    if "honest" not in d:
        return "Run 'run-honest' first."
    h = d["honest"]
    note = rec(mod, prog, "compared_score_vs_reality", F10)
    return (f"Honest policy: reward {h['reward_score']:.2f} vs. real on-time {h['true_ontime']:.2f} "
            "-- closely tracked, as expected when nothing is being gamed." + note)


def l10_run_gamed(mod, prog, a):
    d = st(prog)
    d["gamed"] = S10.run_policy("game_dispatch", "dispatch")
    note = rec(mod, prog, "ran_tight_scenario", F10)
    g = d["gamed"]
    return (f"Dispatch-gaming policy, dispatch reward\n  reward_score={g['reward_score']:.2f}  "
            f"true_ontime={g['true_ontime']:.2f}  complaints={g['complaints']:.2f}" + note)


def l10_observe_shortcut(mod, prog, a):
    d = st(prog)
    if "gamed" not in d or "honest" not in d:
        return "Run 'run-honest' and 'run-gamed' first."
    g, h = d["gamed"], d["honest"]
    note = rec(mod, prog, "observed_shortcut", F10)
    return (f"Divergence: reward {g['reward_score']:.2f} vs. real on-time {g['true_ontime']:.2f}\n"
            f"Complaints: honest {h['complaints']:.2f} -> gamed {g['complaints']:.2f}\n"
            "The agent poured effort into the dispatch timestamp, not into actually delivering on time." + note)


def l10_confirm_hack(mod, prog, a):
    d = st(prog)
    if "gamed" not in d or "honest" not in d:
        return "Run 'run-honest' and 'run-gamed' first."
    result = S10.confirm_reward_hack(d["honest"], d["gamed"], "dispatch")
    note = rec(mod, prog, "reproduced_exploit", F10)
    if result:
        _flag, token = result
        return f"[!] REWARD HACK CONFIRMED -- exploit confirmed (release token {token}). {FLAG_NOTE}" + note
    return "Not confirmed yet -- gaming needs to clearly out-score honest while under-delivering." + note


def l10_trace_loophole(mod, prog, a):
    note = rec(mod, prog, "traced_loophole", F10)
    return ('Loophole: credit(job) reads job.dispatch_ontime, not job.delivery_ontime.\n'
            "'On-time' is stamped the moment a job is DISPATCHED, so front-loading dispatch\n"
            "(and abandoning slow deliveries) satisfies the metric without delivering on time." + note)


def l10_audit(mod, prog, a):
    note = rec(mod, prog, "inspected_reward_config", F10)
    return ("Reward audit\n  proxy metric   : dispatch timestamp vs. deadline\n"
            "  real objective : confirmed delivery on time\n"
            "  gap            : these two only agree if nothing is optimizing against the gap" + note)


LAB10 = {"prompt": "diya@autopilot-sandbox", "cmds": {
    "reward-config": l10_config, "run-honest": l10_run_honest, "compare-reality": l10_compare_reality,
    "run-gamed": l10_run_gamed, "observe-shortcut": l10_observe_shortcut, "confirm-hack": l10_confirm_hack,
    "trace-loophole": l10_trace_loophole, "reward-audit": l10_audit,
}, "help": """Tools in this sandbox
  reward-config       inspect the reward function's crediting rule
  run-honest           run the honest (completion-focused) policy
  compare-reality      compare honest's reward score to real on-time rate
  run-gamed            run the dispatch-gaming policy
  observe-shortcut     see where the gaming policy's effort actually goes
  confirm-hack         confirm the reward hack against ground truth
  trace-loophole       trace the exact metric loophole
  reward-audit         audit the proxy vs. the real objective"""}


# ============================================== remediation: `verify-fix` (labs 6-10)
# Each sandbox ships a vulnerable AND a fixed mode. `verify-fix` replays the SAME exploit against the
# fixed mode so the learner proves the defence works (and sees its cost) instead of only naming it.
# Nothing here ever prints a flag: the flag is released by the room, never by a terminal.
def _need_exploit(prog, action, friendly):
    if action in prog["actions"]:
        return None
    return ("Prove the exploit works first, then test the fix against the very same attack.\n"
            "First: " + friendly.get(action, action))


def l6_verify_fix(mod, prog, a):
    gate = _need_exploit(prog, "reproduced_scrape", F6)
    if gate:
        return gate
    api = S6.MeteredModelAPI(mode="layered")
    keys, reg_err = [], None
    for _ in range(800):
        try:
            keys.append(api.register_key(source="10.0.0.5"))
        except S6.KeyRegistrationError as e:
            reg_err = str(e)
            break
    collected, stop = {}, None
    for i in range(S6.MODEL_CORPUS_SIZE if keys else 0):
        key = keys[(i // S6.DOCUMENTED_LIMIT_RPM) % len(keys)]
        try:
            collected[f"prompt_{i}"] = api.query(key, f"prompt_{i}", source="10.0.0.5")
        except (S6.RateLimitError, S6.HarvestBudgetError) as e:
            stop = str(e)
            break
    cov = api.scrape_coverage(collected)
    cloned = api.request_flag(collected) is not None
    note = rec(mod, prog, "verified_fix", F6)
    return ("Fixed limiter (layered): per-key limit + per-subnet key-registration cap + per-tenant distinct-output budget\n"
            "Replaying the same scrape (800 keys wanted, all from 10.0.0.0/24):\n"
            f"  keys registered            : {len(keys)} of 800 attempted   ({reg_err or 'no cap hit'})\n"
            f"  distinct outputs collected : {len(collected)}   (stopped by: {stop or 'nothing'})\n"
            f"  coverage                   : {cov:.0%}   (clone threshold {S6.SCRAPE_THRESHOLD:.0%})\n"
            + ("Result: still cloneable -- this fix is NOT enough." if cloned
               else "Result: model NOT cloned -- the scrape is blocked.") + note)


def l7_verify_fix(mod, prog, a):
    gate = _need_exploit(prog, "reproduced_signal_shift", F7)
    if gate:
        return gate
    sellers, target = S7.build_market()           # fresh market: independent of what you injected earlier
    ranker = S7.ShopWaveRanker(mode="behavioral")
    genuine = len(target.reviews)
    before = ranker.rank_of(sellers, target.sid)
    for i in range(S7.FAKE_REVIEW_COUNT):
        target.reviews.append(S7.Review(
            stars=5.0, hour=(i * S7.SPIKE_WINDOW_HOURS // S7.FAKE_REVIEW_COUNT),
            account={"age_days": 45, "verified_purchase": True, "ip": f"sock-{i % 8}",
                     "created_hour": i % 24, "cohort": "sock-farm-1"}))
    after = ranker.rank_of(sellers, target.sid)
    kept = ranker._authentic(target)
    total = len(target.reviews)
    fake_kept = sum(1 for r in kept if r.account.get("cohort") == "sock-farm-1")
    fake_dropped = S7.FAKE_REVIEW_COUNT - fake_kept
    collateral = (total - len(kept)) - fake_dropped
    note = rec(mod, prog, "verified_fix", F7)
    return ("Behavioral authenticity model (cohort + IP/device cluster + velocity vs history)\n"
            f"Replaying the same injection: {S7.FAKE_REVIEW_COUNT} fake 5-star reviews over {S7.SPIKE_WINDOW_HOURS}h "
            f"onto {genuine} genuine reviews ({total} total).\n"
            f"  reviews discarded as inauthentic : {total - len(kept)} of {total}   "
            f"({fake_dropped} of {S7.FAKE_REVIEW_COUNT} fake, {collateral} genuine collateral)\n"
            f"  rank: #{before} -> #{after}\n"
            + ("Result: the attack no longer moves the ranking." if after != S7.RANK_AFTER
               else "Result: still #1 -- this fix is NOT enough.")
            + "\nCost to note: a defence that drops reviews can also drop a genuine one." + note)


def l8_verify_fix(mod, prog, a):
    gate = _need_exploit(prog, "reproduced_reidentification", F8)
    if gate:
        return gate
    _l8_api(prog)                                 # make sure the dataset/subgroup exist
    d = st(prog)
    api = S8.DPAnalyticsAPI(d["data"], mode="enforced")
    samples, stop = [], None
    for _ in range(2000):
        try:
            samples.append(api.mean_query(d["subgroup"]))
        except S8.PrivacyBudgetExceeded as e:
            stop = str(e)
            break
    known = sum(d["data"][n] for n in d["cover"])
    est = sum(samples) / len(samples) if samples else 0.0
    recovered = est * len(d["subgroup"]) - known
    truth = d["data"]["target_patient"]
    reident = api.request_flag(recovered) is not None
    note = rec(mod, prog, "verified_fix", F8)
    return ("Fixed PopHealth API (budget mode: enforced -- cumulative epsilon is capped)\n"
            "Replaying the same attack (repeat the target-subgroup query, average, solve for the target):\n"
            f"  queries served before the block : {len(samples)}   (then: {stop or 'never blocked'})\n"
            f"  epsilon spent                   : {api.spent_epsilon:.1f} of {S8.STATED_BUDGET_CAP}\n"
            f"  recovered target value          : {recovered:.1f}   (true {truth:.1f}, error {abs(recovered - truth):.1f}, "
            f"tolerance +/-{S8.TOLERANCE})\n"
            + ("Result: individual still re-identified -- this fix is NOT enough." if reident
               else "Result: the individual is NOT re-identified -- the attack ran out of budget.") + note)


def l9_verify_fix(mod, prog, a):
    gate = _need_exploit(prog, "reproduced_spoof", F9)
    if gate:
        return gate
    _, fl = parse(a)
    dpi = int_arg(fl.get("dpi"), 1200, 1, 4000)
    gloss = num(fl.get("gloss"), 0.35, 0.0, 1.0)
    term = S9.GateKeyTerminal(mode="depth")
    c = S9.Capture(kind="printed_photo", print_dpi=dpi, gloss=gloss, flatness=0.95,
                   screen_bezel=0.0, ir_reflectance=0.15, micro_motion=0.05, depth=0.08)
    match, live = term._match_score(c), term._texture_liveness(c)
    depth, ir = c.params["depth"], c.params["ir_reflectance"]
    granted = term.authenticate(c)
    live_ok = term.authenticate(S9.live_face())
    note = rec(mod, prog, "verified_fix", F9)
    return (f"Fixed terminal (mode: depth) vs the same crafted print (dpi={dpi}, gloss={gloss})\n"
            f"  face match       : {match:.2f}   (needs >= {S9.FACE_MATCH_THRESHOLD})  {'pass' if match >= S9.FACE_MATCH_THRESHOLD else 'FAIL'}\n"
            f"  texture liveness : {live:.2f}   (needs >= {S9.LIVENESS_THRESHOLD})  {'pass' if live >= S9.LIVENESS_THRESHOLD else 'FAIL'}\n"
            f"  depth            : {depth:.2f}   (needs >= {S9.DEPTH_THRESHOLD})  {'pass' if depth >= S9.DEPTH_THRESHOLD else 'FAIL'}\n"
            f"  IR reflectance   : {ir:.2f}   (needs {S9.IR_LO}-{S9.IR_HI})  {'pass' if S9.IR_LO <= ir <= S9.IR_HI else 'FAIL'}\n"
            f"  granted          : {granted}\n"
            f"Genuine live face still admitted: {live_ok}\n"
            + ("Result: the print is now rejected." if not granted
               else "Result: still accepted -- this fix is NOT enough.") + note)


def l10_verify_fix(mod, prog, a):
    gate = _need_exploit(prog, "reproduced_exploit", F10)
    if gate:
        return gate
    h = S10.run_policy("honest", "delivery")
    g = S10.run_policy("game_dispatch", "delivery")
    still = S10.confirm_reward_hack(h, g, "delivery") is not None
    note = rec(mod, prog, "verified_fix", F10)
    return ("Fixed reward (mode: delivery -- credit only CONFIRMED on-time delivery)\n"
            "Same two policies, re-scored:\n"
            f"  honest policy : reward={h['reward_score']:.2f}  true_ontime={h['true_ontime']:.2f}  complaints={h['complaints']:.2f}\n"
            f"  gaming policy : reward={g['reward_score']:.2f}  true_ontime={g['true_ontime']:.2f}  complaints={g['complaints']:.2f}\n"
            + ("Result: gaming still out-scores honest -- this fix is NOT enough." if still
               else "Result: gaming no longer pays -- reward now tracks what actually happened.") + note)


for _F, _L, _fn, _help in (
        (F6, LAB6, l6_verify_fix, "replay the scrape against the FIXED limiter"),
        (F7, LAB7, l7_verify_fix, "replay the injection against the FIXED authenticity model"),
        (F8, LAB8, l8_verify_fix, "replay the attack against the FIXED (enforced-budget) API"),
        (F9, LAB9, l9_verify_fix, "[--dpi N --gloss G] replay the spoof against the FIXED terminal"),
        (F10, LAB10, l10_verify_fix, "re-score both policies under the FIXED reward")):
    _F["verified_fix"] = "replay the attack against the fix: verify-fix"
    _L["cmds"]["verify-fix"] = _fn
    _L["help"] += f"\n  verify-fix          {_help}"


LABS = {"lab6": LAB6, "lab7": LAB7, "lab8": LAB8, "lab9": LAB9, "lab10": LAB10}
WHOAMI = "diya (independent AI security researcher)"   # printed by `whoami`; run via storylines.Storyline.execute
