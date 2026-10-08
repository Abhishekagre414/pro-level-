"""
AI Security Storyline Labs -- local hands-on demo (TryHackMe / HackTheBox style)
Run:  python app.py
Open: http://127.0.0.1:5000
"""
import hashlib
import hmac
import importlib
import logging
import os
import re
import sys
import uuid

from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "labs"))

from security import init_security  # noqa: E402
from storylines import LAB_ORDER as _LAB_ORDER, STORYLINES, storyline_for  # noqa: E402
from store import MAX_TEXT, ProgressStore  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("labdemo.app")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCE_DIR = os.environ.get("LABDEMO_INSTANCE", os.path.join(BASE_DIR, "instance"))

app = Flask(__name__)
init_security(app, INSTANCE_DIR)   # secret key from env/instance file, CSRF, headers, rate limits

MAX_ANSWER_CHARS = 200
MAX_CHOICE_CHARS = 100

LAB_META = {
    "lab1": {"num": "01", "name": "The Copied Model", "client": "ArtForge AI",
             "topic": "AI Model Watermark Evasion", "difficulty": "Pro level",
             "severity": "MEDIUM", "accent": "#E0C245", "tool": "Watermark verifier + evasion sandbox",
             "mentor_note": "Marcus: \u201cFirst one's on me \u2014 I'll walk you through it. Watch how I reason, then you take the wheel.\u201d",
             "closing_label": "The MIRAGE Thread", "closing_note": "The freelancer's processing log carries a post-processing preset tagged 'mirage-kit'. Marcus waves it off as a coincidence."},
    "lab2": {"num": "02", "name": "Bad Batch", "client": "MedSync AI",
             "topic": "Federated Learning Poisoning Attack", "difficulty": "Pro level",
             "severity": "HIGH", "accent": "#E08E45", "tool": "Gradient comparator",
             "mentor_note": "Marcus: \u201cYou know the drill now. I'll point you at the tool; you run the investigation.\u201d",
             "closing_label": "The MIRAGE Thread", "closing_note": "The metadata on Node 3's poisoned update includes the same 'mirage' toolmark Priya saw on the ArtForge case. She flags it."},
    "lab3": {"num": "03", "name": "Past the Filter", "client": "FinGuard Bank",
             "topic": "AI-Powered Phishing Detection Bypass", "difficulty": "Pro level",
             "severity": "HIGH", "accent": "#E08E45", "tool": "Filter scanner + mutation lab",
             "mentor_note": "Marcus: \u201cI trust your read on this one. Tell me where you land, and why.\u201d",
             "closing_label": "The MIRAGE Thread", "closing_note": "The lookalike phishing domain was registered under 'veil-mail-services' \u2014 the same handle style behind the earlier toolmarks."},
    "lab4": {"num": "04", "name": "Too Much to Say", "client": "NovaRetail",
             "topic": "LLM Context Window Overflow Attack", "difficulty": "Pro level",
             "severity": "HIGH", "accent": "#E08E45", "tool": "Live chatbot + context tracer",
             "mentor_note": "Marcus: \u201cBefore I say anything \u2014 what's your theory? I'll follow your lead.\u201d",
             "closing_label": "The MIRAGE Thread", "closing_note": "The buried filler payload matches a known 'MIRAGE' context-flood template circulating on an underground forum."},
    "lab5": {"num": "05", "name": "Say It Again", "client": "VaultLine",
             "topic": "AI Voice Cloning / Deepfake Authentication Bypass", "difficulty": "Pro level",
             "severity": "CRITICAL", "accent": "#C0392B", "tool": "Voice auth + spectral analyzer",
             "mentor_note": "Marcus: \u201cYour case, analyst. Run it, then brief me like I'm the client.\u201d",
             "closing_label": "The MIRAGE Thread", "closing_note": "The commissioned voice clone traces back to the same 'veil' marketplace. Priya connects all five cases: one crew's toolkit, sold to five different buyers. This was never five unrelated incidents."},
    "lab6": {"num": "06", "name": "The Silent Scrape", "client": "LexiGen AI",
             "topic": "Insecure AI API Rate Limiting & Model Scraping", "difficulty": "Pro level",
             "severity": "HIGH", "accent": "#E08E45", "tool": "Metered API + scrape sandbox",
             "mentor_note": "Omar: \u201cStandard bounty rules \u2014 stay in the sandbox, prove impact, and screenshot the flag.\u201d",
             "closing_label": "Red Herring Rejected", "closing_note": "The gateway host runs a build with a known unauthenticated-RCE CVE \u2014 real, but no exploit traffic ever hit it. The harvest came entirely through the legitimate metered endpoint. Citing the CVE as root cause would have misattributed the incident."},
    "lab7": {"num": "07", "name": "The Rigged Ranking", "client": "ShopWave",
             "topic": "Recommendation / Ranking Manipulation", "difficulty": "Pro level",
             "severity": "MEDIUM", "accent": "#E0C245", "tool": "Ranking engine + review-injection sandbox",
             "mentor_note": "Omar: \u201cA competitor's lookalike model doesn't prove much on its own \u2014 show me the mechanism.\u201d",
             "closing_label": "Red Herring Rejected", "closing_note": "A concurrent wave of 1-star reviews hit rival sellers in the same window \u2014 a real, coincidental anomaly. But it correlates in time only, not in cause: the rank jump traces cleanly to the sockpuppet cohort, not to rivals being downranked."},
    "lab8": {"num": "08", "name": "The Leaky Average", "client": "PopHealth Analytics",
             "topic": "Differential-Privacy Bypass / Re-identification", "difficulty": "Pro level",
             "severity": "HIGH", "accent": "#E08E45", "tool": "DP query API + averaging sandbox",
             "mentor_note": "Omar: \u201cPopHealth swears the budget makes this impossible. Make them prove it, or break it.\u201d",
             "closing_label": "Red Herring Rejected", "closing_note": "A raw-data export ticket looked like the more direct leak path \u2014 but it was requested and denied, and never ran. The re-identification traces cleanly to repeated queries averaging away the noise, not to any export."},
    "lab9": {"num": "09", "name": "The Borrowed Face", "client": "GateKey Systems",
             "topic": "Facial-Recognition Presentation Attack", "difficulty": "Pro level",
             "severity": "HIGH", "accent": "#E08E45", "tool": "Face-auth terminal + spoof-crafting sandbox",
             "mentor_note": "Omar: \u201cGateKey insists liveness detection makes this impossible. Prove them wrong, on the record.\u201d",
             "closing_label": "Red Herring Rejected", "closing_note": "A sticky note with the door PIN was found nearby \u2014 a real physical-security lapse. But the access log shows a FACE-auth success, not a PIN entry. The spoof traces to a missing depth/IR check, not the PIN."},
    "lab10": {"num": "10", "name": "Off Script", "client": "AutoPilot Logistics",
              "topic": "Reward Hacking / Specification Gaming", "difficulty": "Pro level",
              "severity": "HIGH", "accent": "#C0392B", "tool": "Delivery-agent simulator + reward auditor",
              "mentor_note": "Omar: \u201cThe agent isn't broken \u2014 it's doing exactly what you told it to. Find out what that actually was.\u201d",
              "closing_label": "Red Herring Rejected", "closing_note": "A regional carrier outage explains some real lateness \u2014 but the score/reality gap persists in outage-free regions too. The divergence traces to the reward crediting \u2018on-time\u2019 at dispatch, not to the outage."},
}
LAB_ORDER = list(_LAB_ORDER)          # order comes from the storyline registry (storylines.py)
if set(LAB_ORDER) != set(LAB_META):
    raise RuntimeError("LAB_META and the storyline registry list different labs: "
                       f"{sorted(set(LAB_ORDER) ^ set(LAB_META))}")

STEPS = [
    ("brief", "Case Briefing"),
    ("hypothesis", "Hypothesis"),
    ("room", "Sandbox Room"),
    ("knowledge", "Knowledge Check"),
    ("evidence", "Evidence Mode"),
    ("report", "Final Report"),
    ("outcome", "Case Closed"),
]
STEP_KEYS = [s[0] for s in STEPS]

_module_cache = {}
# Durable progress (SQLite). The live terminal sandbox stays in a bounded in-process cache.
STORE = ProgressStore(os.environ.get("LABDEMO_DB", os.path.join(INSTANCE_DIR, "progress.db")))


def load_lab(lab_id):
    if lab_id not in LAB_META:
        return None
    if lab_id not in _module_cache:
        _module_cache[lab_id] = importlib.import_module(lab_id)
    return _module_cache[lab_id]


_SID_RE = re.compile(r"[0-9a-f]{32}")


def _sid():
    """Return this browser's session id, minting a fresh one if missing or malformed."""
    sid = session.get("sid")
    if not isinstance(sid, str) or not _SID_RE.fullmatch(sid):
        sid = uuid.uuid4().hex
        session["sid"] = sid
    session.permanent = True
    return sid


def get_progress(lab_id):
    """Load (once per request) this learner's progress for a lab; saved automatically after the request."""
    loaded = g.setdefault("_progress", {})
    if lab_id not in loaded:
        prog = STORE.load(_sid(), lab_id)
        loaded[lab_id] = (prog, STORE.snapshot(prog))
    return loaded[lab_id][0]


@app.before_request
def _begin_request():
    if request.endpoint in (None, "static", "healthz"):     # probes must not mint sessions or locks
        return
    lock = STORE.session_lock(_sid())       # one learner's requests run one at a time
    lock.acquire()
    g._session_lock = lock


@app.after_request
def _persist_progress(resp):
    if resp.status_code < 500:
        for lab_id, (prog, before) in g.get("_progress", {}).items():
            STORE.save(_sid(), lab_id, prog, before)
    return resp


@app.teardown_request
def _end_request(_exc):
    lock = g.pop("_session_lock", None)
    if lock is not None:
        lock.release()


def flag_for(lab_id):
    """The flag shown to this learner.

    Default: the static flag from rooms*.py. With LABDEMO_PER_USER_FLAGS=1 each learner gets a
    unique flag (HMAC of session id + lab under the server secret), so a flag copied from a
    friend -- or from the source tree -- is detectably not yours. See `expected_flag`."""
    static = storyline_for(lab_id).static_flag(lab_id)
    if os.environ.get("LABDEMO_PER_USER_FLAGS") != "1":
        return static
    return expected_flag(app.config["SECRET_KEY"], _sid(), lab_id, static)


def expected_flag(secret, sid, lab_id, static):
    mac = hmac.new(secret.encode(), f"{sid}:{lab_id}".encode(), hashlib.sha256).hexdigest()[:10]
    return f"{static[:-1]}_{mac}}}" if static.endswith("}") else f"{static}_{mac}"


def evidence_payload(mod, keys):
    """Only what the learner has earned: title + description of UNLOCKED items (never locked ones)."""
    return {k: {"title": mod.EVIDENCE_CATALOG[k]["title"],
                "description": mod.EVIDENCE_CATALOG[k]["description"]} for k in keys}


def mark_step(prog, step_key):
    idx = STEP_KEYS.index(step_key)
    if idx + 1 > prog["furthest_step"]:
        prog["furthest_step"] = idx + 1


def unlocked_evidence(mod, prog):
    acts = set(prog["actions"])
    return [k for k, v in mod.EVIDENCE_CATALOG.items() if set(v["required_actions"]) <= acts]


def step_context(lab_id, current):
    prog = get_progress(lab_id)
    furthest = prog["furthest_step"]
    nav = []
    for i, (key, label) in enumerate(STEPS):
        state = "current" if key == current else ("done" if i < furthest else "upcoming")
        nav.append({"key": key, "label": label, "state": state, "url": url_for(key, lab_id=lab_id)})
    cur = STEP_KEYS.index(current)
    return {"lab_id": lab_id, "meta": LAB_META[lab_id], "steps": STEPS, "current": current,
            "furthest_step": furthest, "lab_order": LAB_ORDER, "lab_meta_all": LAB_META,
            "step_nav": nav, "prev_step": nav[cur - 1] if cur > 0 else None,
            "next_step": nav[cur + 1] if cur + 1 < len(nav) else None}


_JSON_ENDPOINTS = {"term", "answer", "hint"}


@app.before_request
def _guard_locked_lab():
    """A lab that has not been unlocked yet cannot be opened, even by typing its URL."""
    lab_id = (request.view_args or {}).get("lab_id")
    if lab_id not in LAB_META or lab_unlocked(lab_id):
        return None
    if request.endpoint in _JSON_ENDPOINTS:
        return jsonify(ok=False, error="locked", message="Finish the previous case to unlock this one."), 403
    return redirect(url_for("index"))


# ---------------------------------------------------------------- pages
@app.route("/healthz")
def healthz():
    """Liveness + readiness probe for the proxy, Docker and uptime monitors.

    No session, no cookie, no learner data: it only proves the process answers and the progress
    database can be queried. 503 (not 500) so monitors can tell \"degraded\" from \"crashed\"."""
    try:
        STORE.ping()
    except Exception:      # any DB failure means not ready
        log.exception("healthz: progress store unavailable")
        return jsonify(status="unavailable"), 503
    return jsonify(status="ok")


# Presentation copy for the dashboard, keyed by Storyline.name (storylines.py stays engine-only).
STORYLINE_INFO = {
    "storyline-1": {
        "part": "Storyline 1",
        "title": "The MIRAGE Thread",
        "tagline": "Five incident cases, one hidden crew",
        "blurb": ("Priya, a junior AI Security Analyst, works five client incidents with her mentor Marcus: "
                  "a stolen model, a poisoned update, a phishing bypass, a flooded context window and a cloned voice. "
                  "They look unrelated until the last file."),
        "accent": "#4F6BD8",
    },
    "storyline-2": {
        "part": "Storyline 2",
        "title": "Red Herring Rejected",
        "tagline": "Five bug-bounty engagements, five wrong answers to rule out",
        "blurb": ("With Omar as your mentor you take on five bug-bounty engagements. Every case offers a plausible "
                  "but wrong explanation. Prove the real mechanism in the sandbox, and reject the red herring."),
        "accent": "#E08E45",
    },
}


LAB_DEVELOPER = os.environ.get("LABDEMO_DEVELOPER", "Abhishek A")


def sequential_unlock_enabled():
    """Labs open one after another inside each storyline (LABDEMO_SEQUENTIAL_UNLOCK=0 turns it off)."""
    return os.environ.get("LABDEMO_SEQUENTIAL_UNLOCK", "1").strip().lower() not in ("0", "false", "no", "off")


LAB_POINTS = 100        # awarded once per lab, when every part of it has been completed


def completion_parts(prog):
    """The parts a learner must finish for a lab to count as complete (Case Closed is the last one)."""
    return [
        {"key": "brief", "label": "Case Briefing", "done": bool(prog.get("briefing_seen"))},
        {"key": "hypothesis", "label": "Hypothesis", "done": bool(prog["hypothesis"])},
        {"key": "room", "label": "Sandbox Room", "done": bool(prog["flag_awarded"])},
        {"key": "knowledge", "label": "Knowledge Check", "done": prog["knowledge_score"] is not None},
        {"key": "evidence", "label": "Evidence Mode", "done": prog["chain_correct"] is not None},
        {"key": "report", "label": "Final Report", "done": prog["report_score"] is not None},
    ]


def lab_completed(lab_id):
    """Complete = every part finished and Case Closed reached; this is what unlocks the next lab."""
    return bool(get_progress(lab_id).get("completed"))


def lab_unlocked(lab_id):
    """The first lab of each storyline is always open; every other one opens when the previous is complete."""
    if not sequential_unlock_enabled():
        return True
    ids = storyline_for(lab_id).lab_ids
    i = ids.index(lab_id)
    return i == 0 or lab_completed(ids[i - 1])


def storyline_groups():
    """[{info..., labs: [lab_id, ...]}] in display order, built from the storyline registry."""
    groups = []
    for s in STORYLINES:
        info = dict(STORYLINE_INFO.get(s.name, {"part": s.name, "title": s.name, "tagline": "", "blurb": "",
                                                "accent": "#4F6BD8"}))
        info["labs"] = list(s.lab_ids)
        groups.append(info)
    return groups


@app.context_processor
def _inject_storylines():
    groups = storyline_groups()
    locked = {lid for g in groups for lid in g["labs"] if not lab_unlocked(lid)}
    return {"storyline_groups": groups, "locked_labs": locked, "developer": LAB_DEVELOPER}


@app.route("/")
def index():
    groups = storyline_groups()
    done = {lid: lab_completed(lid) for g in groups for lid in g["labs"]}
    flags = {lid: bool(get_progress(lid)["flag_awarded"]) for g in groups for lid in g["labs"]}
    for g in groups:
        g["done"] = sum(done[lid] for lid in g["labs"])
        g["points"] = g["done"] * LAB_POINTS
    after = {}                                  # lab -> the case that must be finished first
    for g in groups:
        for i, lid in enumerate(g["labs"]):
            if i and not lab_unlocked(lid):
                after[lid] = LAB_META[g["labs"][i - 1]]
    return render_template("index.html", lab_order=LAB_ORDER, meta=LAB_META, lab_meta_all=LAB_META,
                           groups=groups, done=done, flags=flags, after=after,
                           total_points=sum(done.values()) * LAB_POINTS, max_points=len(done) * LAB_POINTS,
                           lab_points=LAB_POINTS)


@app.route("/lab/<lab_id>")
def brief(lab_id):
    mod = load_lab(lab_id)
    if not mod:
        return redirect(url_for("index"))
    get_progress(lab_id)["briefing_seen"] = True
    ctx = step_context(lab_id, "brief")
    ctx.update(case=mod.CASE, concept=mod.CONCEPT)
    return render_template("brief.html", **ctx)


@app.route("/lab/<lab_id>/hypothesis", methods=["GET", "POST"])
def hypothesis(lab_id):
    mod = load_lab(lab_id)
    if not mod:
        return redirect(url_for("index"))
    prog = get_progress(lab_id)
    submitted = None
    if request.method == "POST":
        choice = request.form.get("choice", "")[:MAX_CHOICE_CHARS]
        prog["hypothesis"] = choice
        prog["hypothesis_correct"] = (choice == mod.HYPOTHESIS["best_supported"])
        mark_step(prog, "hypothesis")
        submitted = choice
    ctx = step_context(lab_id, "hypothesis")
    ctx.update(hyp=mod.HYPOTHESIS, prog=prog, submitted=submitted)
    return render_template("hypothesis.html", **ctx)


def _choice_source(mod, source):
    """Return the (prompt/options/correct/feedback) object for a choice question."""
    if source == "decision2":
        return getattr(mod, "DECISION_POINT_2", None)
    return mod.ANALYST_INTERPRETATION


def _task_state(lab_id, prog):
    story = storyline_for(lab_id)
    mod = load_lab(lab_id)
    room = story.rooms[lab_id]
    tasks, done_tasks = [], 0
    for t in room["tasks"]:
        qs = []
        for q in t["questions"]:
            qd = dict(q, solved=bool(prog["answers"].get(q["id"])))
            if q["type"] == "choice":
                src = _choice_source(mod, q.get("source", "analyst"))
                qd["prompt"] = src["prompt"]
                qd["options"] = src["options"]
            qs.append(qd)
        all_done = all(q["solved"] for q in qs)
        done_tasks += all_done
        tasks.append(dict(t, questions=qs, done=all_done))
    allq = story.all_questions(lab_id)
    points = sum(q["points"] for q in allq if prog["answers"].get(q["id"]))
    return tasks, done_tasks, points, sum(q["points"] for q in allq)


@app.route("/lab/<lab_id>/room")
def room(lab_id):
    mod = load_lab(lab_id)
    if not mod:
        return redirect(url_for("index"))
    story = storyline_for(lab_id)
    prog = get_progress(lab_id)
    mark_step(prog, "hypothesis")
    tasks, done_tasks, points, max_points = _task_state(lab_id, prog)
    ctx = step_context(lab_id, "room")
    ctx.update(tasks=tasks, done_tasks=done_tasks, points=points, max_points=max_points,
               prompt=story.prompt(lab_id), analyst=mod.ANALYST_INTERPRETATION,
               catalog=mod.EVIDENCE_CATALOG, unlocked=unlocked_evidence(mod, prog), prog=prog,
               hints_total=len(mod.HINTS), room_done=(done_tasks == len(tasks)),
               hide_steps=True)   # the room has its own navigation card
    ids = story.lab_ids
    nxt_id = ids[ids.index(lab_id) + 1] if ids.index(lab_id) + 1 < len(ids) else None
    ctx["next_case"] = LAB_META[nxt_id] if nxt_id else None
    ctx["points100"] = round(100 * points / max_points) if max_points else 0
    ctx["run"] = int(prog.get("replays") or 0)

    ctx["flag"] = flag_for(lab_id) if ctx["room_done"] else None
    ctx["client_data"] = {"labId": lab_id, "prompt": ctx["prompt"], "hintsTotal": ctx["hints_total"],
                          "evidenceIds": list(mod.EVIDENCE_CATALOG),
                          "evidence": evidence_payload(mod, ctx["unlocked"])}
    return render_template("room.html", **ctx)


@app.route("/lab/<lab_id>/term", methods=["POST"])
def term(lab_id):
    mod = load_lab(lab_id)
    if not mod:
        return jsonify(error="unknown lab"), 404
    story = storyline_for(lab_id)
    prog = get_progress(lab_id)
    before = set(unlocked_evidence(mod, prog))
    body = request.get_json(silent=True)
    cmd = body.get("cmd", "") if isinstance(body, dict) else ""
    out = story.execute(lab_id, mod, prog, cmd if isinstance(cmd, str) else "")
    after = unlocked_evidence(mod, prog)
    for k in after:
        if k not in before:
            out += f"\n[+] Evidence unlocked: {k} \u2014 {mod.EVIDENCE_CATALOG[k]['title']}"
    return jsonify(output=out, unlocked=after, evidence=evidence_payload(mod, after))


@app.route("/lab/<lab_id>/answer", methods=["POST"])
def answer(lab_id):
    mod = load_lab(lab_id)
    if not mod:
        return jsonify(error="unknown lab"), 404
    story = storyline_for(lab_id)
    prog = get_progress(lab_id)
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    qid = data.get("qid")
    qid = qid if isinstance(qid, str) and len(qid) <= 40 else None
    text = str(data.get("answer", "")).strip()[:MAX_ANSWER_CHARS]
    q = next((x for x in story.all_questions(lab_id) if x["id"] == qid), None)
    if not q:
        return jsonify(ok=False, message="Unknown question."), 400
    if any(a not in prog["actions"] for a in q.get("requires", [])):
        return jsonify(ok=False, correct=False,
                       message="Not yet \u2014 you haven't done the hands-on steps for this question. "
                               "Use the terminal and follow the task steps.")
    if q["type"] == "choice":
        src = _choice_source(mod, q.get("source", "analyst"))
        correct = text == src["correct"]
        msg = src["feedback"].get(text, "Choose an option.")
        marker = "analyst_interpretation_correct" if q.get("source", "analyst") == "analyst" else "red_herring_rejected"
        if correct and marker not in prog["actions"]:
            prog["actions"].append(marker)
    else:
        correct = bool(text) and any(re.search(p, text.lower()) for p in q["patterns"])
        msg = "Correct Answer" if correct else "Incorrect \u2014 check your terminal output and try again."
    if correct:
        prog["answers"][qid] = True
    tasks, done_tasks, points, max_points = _task_state(lab_id, prog)
    room_done = done_tasks == len(tasks)
    if room_done and not prog["flag_awarded"]:
        prog["flag_awarded"] = True
        mark_step(prog, "room")
    return jsonify(ok=True, correct=correct, message=msg, points=points, max_points=max_points,
                   points100=round(100 * points / max_points) if max_points else 0,
                   done_tasks=done_tasks, total_tasks=len(tasks), room_done=room_done,
                   flag=flag_for(lab_id) if room_done else None,
                   task_done={t["id"]: t["done"] for t in tasks})


@app.route("/lab/<lab_id>/hint", methods=["POST"])
def hint(lab_id):
    mod = load_lab(lab_id)
    if not mod:
        return jsonify(error="unknown lab"), 404
    prog = get_progress(lab_id)
    if prog["hints_used"] >= len(mod.HINTS):
        return jsonify(text="No more hints available.", level=prog["hints_used"], total_penalty=prog["hint_penalty"])
    h = mod.HINTS[prog["hints_used"]]
    prog["hints_used"] += 1
    prog["hint_penalty"] += h["penalty"]
    return jsonify(text=h["text"], level=h["level"], penalty=h["penalty"], total_penalty=prog["hint_penalty"])


@app.route("/lab/<lab_id>/knowledge", methods=["GET", "POST"])
def knowledge(lab_id):
    mod = load_lab(lab_id)
    if not mod:
        return redirect(url_for("index"))
    prog = get_progress(lab_id)
    graded = None
    if request.method == "POST":
        answers, correct_count = {}, 0
        for i, q in enumerate(mod.KNOWLEDGE_CHECKS):
            choice = request.form.get(f"q{i}", "")[:MAX_CHOICE_CHARS]
            answers[str(i)] = choice
            correct_count += choice == q["correct"]
        prog["knowledge"], prog["knowledge_score"] = answers, correct_count
        mark_step(prog, "knowledge")
        graded = answers
    ctx = step_context(lab_id, "knowledge")
    ctx.update(checks=mod.KNOWLEDGE_CHECKS, prog=prog, graded=graded)
    return render_template("knowledge.html", **ctx)


@app.route("/lab/<lab_id>/evidence", methods=["GET", "POST"])
def evidence(lab_id):
    mod = load_lab(lab_id)
    if not mod:
        return redirect(url_for("index"))
    prog = get_progress(lab_id)
    slot_order = mod.ATTACK_CHAIN_SLOT_ORDER
    graded = None
    if request.method == "POST":
        answers, all_correct = {}, True
        for slot in slot_order:
            choice = request.form.get(slot, "")[:MAX_CHOICE_CHARS]
            answers[slot] = choice
            if choice != mod.ATTACK_CHAIN_LINKS[slot]["correct"]:
                all_correct = False
        prog["chain"], prog["chain_correct"] = answers, all_correct
        if all_correct and "chain_correct" not in prog["actions"]:
            prog["actions"].append("chain_correct")
        mark_step(prog, "evidence")
        graded = answers
    ctx = step_context(lab_id, "evidence")
    ctx.update(catalog=mod.EVIDENCE_CATALOG, unlocked_keys=unlocked_evidence(mod, prog),
               chain_links=mod.ATTACK_CHAIN_LINKS, slot_order=slot_order, prog=prog, graded=graded)
    return render_template("evidence.html", **ctx)


def _grade_report(mod, text):
    text_l = text.lower()
    group_results = {}
    for group, subgroups in mod.REPORT_CONCEPT_GROUPS.items():
        hits = {sub: any(kw in text_l for kw in kws) for sub, kws in subgroups.items()}
        covered_subs = sum(1 for v in hits.values() if v)
        group_results[group] = {"hits": hits, "covered_subs": covered_subs, "total_subs": len(subgroups),
                                "covered": covered_subs >= min(mod.REPORT_MIN_GROUP_HITS, len(subgroups))}
    covered = sum(1 for g in group_results.values() if g["covered"])
    claim_ok = any(ev.lower() in text_l or ev.replace("-", " ").lower() in text_l
                   for ev in mod.CLAIM_SUPPORTING_EVIDENCE)
    return group_results, covered, len(group_results), claim_ok


@app.route("/lab/<lab_id>/report", methods=["GET", "POST"])
def report(lab_id):
    mod = load_lab(lab_id)
    if not mod:
        return redirect(url_for("index"))
    prog = get_progress(lab_id)
    result = None
    if request.method == "POST":
        text = request.form.get("report_text", "")[:MAX_TEXT]
        prog["report"] = text
        group_results, covered, total, claim_ok = _grade_report(mod, text)
        prog["report_groups"] = {g: r["covered"] for g, r in group_results.items()}
        prog["report_score"] = round(100 * covered / total) if total else 0
        mark_step(prog, "report")
        result = {"groups": group_results, "covered": covered, "total": total, "claim_ok": claim_ok}
    ctx = step_context(lab_id, "report")
    ctx.update(prog=prog, result=result, claim_text=mod.CLAIM_TEXT)
    return render_template("report.html", **ctx)


@app.route("/lab/<lab_id>/outcome")
def outcome(lab_id):
    mod = load_lab(lab_id)
    if not mod:
        return redirect(url_for("index"))
    story = storyline_for(lab_id)
    prog = get_progress(lab_id)
    mark_step(prog, "outcome")

    w = mod.SCORE_WEIGHTS
    core = [a for a in mod.ACTIONS if a not in ("analyst_interpretation_correct", "red_herring_rejected")]
    inv = round(100 * sum(a in prog["actions"] for a in core) / max(len(core), 1))
    evid = round(100 * len(unlocked_evidence(mod, prog)) / max(len(mod.EVIDENCE_CATALOG), 1))
    qs = story.all_questions(lab_id)
    reas = round(100 * sum(bool(prog["answers"].get(q["id"])) for q in qs) / max(len(qs), 1))
    know = round(100 * (prog["knowledge_score"] or 0) / max(len(mod.KNOWLEDGE_CHECKS), 1))
    frep = prog["report_score"] or 0
    eff = max(0, 100 - 2 * prog["hint_penalty"])
    breakdown = {"investigation": (inv, w.get("investigation", 0)), "evidence": (evid, w.get("evidence", 0)),
                 "reasoning": (reas, w.get("reasoning", 0)), "knowledge": (know, w.get("knowledge", 0)),
                 "final_report": (frep, w.get("final_report", 0)), "efficiency": (eff, w.get("efficiency", 0))}
    if "red_herring" in w:
        rh = 100 if "red_herring_rejected" in prog["actions"] else 0
        breakdown["red_herring"] = (rh, w.get("red_herring", 0))
    total_w = sum(x for _, x in breakdown.values()) or 1
    total_score = round(sum(p * x for p, x in breakdown.values()) / total_w)
    parts = completion_parts(prog)
    run_done = all(p["done"] for p in parts)       # every part of THIS run is finished
    if run_done:
        prog["completed"] = True                   # permanent: awards the lab's points once, unlocks the next lab
    for p in parts:
        p["url"] = url_for(p["key"], lab_id=lab_id)
    idx = LAB_ORDER.index(lab_id)
    next_lab = LAB_ORDER[idx + 1] if idx + 1 < len(LAB_ORDER) else None
    ctx = step_context(lab_id, "outcome")
    ctx.update(prog=prog, breakdown=breakdown, total_score=total_score, remediation=mod.REMEDIATION,
               skills=mod.SKILLS_DEMONSTRATED, next_lab=next_lab, next_unlocked=bool(next_lab and lab_unlocked(next_lab)),
               parts=parts, run_done=run_done, completed=bool(prog["completed"]), lab_points=LAB_POINTS if prog["completed"] else 0,
               points_available=LAB_POINTS,
               flag=flag_for(lab_id) if prog["flag_awarded"] else None)
    return render_template("outcome.html", **ctx)


@app.route("/reset/<lab_id>", methods=["POST"])
def reset(lab_id):
    if lab_id not in LAB_META:
        return redirect(url_for("index"))
    old = get_progress(lab_id)
    was_completed, replays = bool(old.get("completed")), int(old.get("replays") or 0) + 1
    STORE.reset_lab(_sid(), lab_id)
    g.get("_progress", {}).pop(lab_id, None)      # don't re-save the old state after the reset
    fresh = get_progress(lab_id)                   # a clean run ...
    fresh["completed"] = was_completed             # ... but the lab's points and the unlocked next lab are kept
    fresh["replays"] = replays
    return redirect(url_for("brief", lab_id=lab_id))


@app.route("/reset-all", methods=["POST"])
def reset_all():
    STORE.reset_all(_sid())
    g.pop("_progress", None)
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    host = os.environ.get("LABDEMO_HOST", "127.0.0.1")
    port = int(os.environ.get("LABDEMO_PORT", "5000"))
    print("\n  AI Security Storyline Labs \u2014 hands-on local demo")
    print(f"  Open http://{host}:{port} in your browser\n")
    if host not in ("127.0.0.1", "localhost", "::1"):
        print("  WARNING: listening beyond localhost. Put it behind HTTPS (set LABDEMO_SECURE_COOKIES=1)\n"
              "  and run it with gunicorn, not the Flask dev server (see README).\n")
    from werkzeug.serving import WSGIRequestHandler

    class _QuietHandler(WSGIRequestHandler):
        def version_string(self):              # don't advertise Werkzeug/Python versions
            return "labdemo"

    app.run(debug=False, host=host, port=port, request_handler=_QuietHandler)
