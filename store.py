# -*- coding: utf-8 -*-
"""
Durable, bounded progress storage (replaces the old in-memory `STORE = {}`).

What is persisted (SQLite, JSON): everything a learner has *earned* -- actions,
answers, hypothesis, knowledge/evidence/report results, hints, flag status.
A server restart no longer wipes progress.

What is NOT persisted: `prog["sandbox"]`, the live terminal state (numpy arrays,
simulator objects). It is kept in a small in-process LRU cache and rebuilt on
demand, exactly like a real lab container that has to be re-run. Because of
that, run ONE worker process with several threads in production:
    gunicorn -w 1 --threads 8 app:app

Limits (so a bad client can't exhaust memory or disk): a capped LRU for live
sandboxes, a cap on stored text, and automatic expiry of old sessions.
"""
import json
import os
import sqlite3
import threading
import time
from collections import OrderedDict

SANDBOX_CACHE_MAX = 500          # live terminal sandboxes kept in memory
SESSION_TTL_SECONDS = 30 * 24 * 3600
MAX_TEXT = 8000                  # longest report / free-text we will persist
PURGE_EVERY_SECONDS = 3600


def new_progress():
    return {"hypothesis": None, "hypothesis_correct": None,
            "knowledge": {}, "knowledge_score": None,
            "chain": {}, "chain_correct": None,
            "report": "", "report_groups": {}, "report_score": None,
            "furthest_step": 0,
            "actions": [], "sandbox": {}, "answers": {}, "analyst_choice": None,
            "hints_used": 0, "hint_penalty": 0, "flag_awarded": False,
            "briefing_seen": False, "completed": False, "replays": 0}


def _durable(prog):
    """The JSON-safe part of a progress dict."""
    d = {k: v for k, v in prog.items() if k != "sandbox"}
    if isinstance(d.get("report"), str) and len(d["report"]) > MAX_TEXT:
        d["report"] = d["report"][:MAX_TEXT]
    return d


class ProgressStore:
    def __init__(self, path):
        self.path = path
        if path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self._db_lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("""CREATE TABLE IF NOT EXISTS progress (
            sid TEXT NOT NULL, lab_id TEXT NOT NULL, data TEXT NOT NULL, updated REAL NOT NULL,
            PRIMARY KEY (sid, lab_id))""")
        self._sandboxes = OrderedDict()           # (sid, lab) -> sandbox dict
        self._cache_lock = threading.Lock()
        self._locks = {}                          # sid -> RLock (serialise one learner's requests)
        self._locks_guard = threading.Lock()
        self._last_purge = 0.0
        self.purge()

    # ---- concurrency: one learner's requests are serialised, different learners run in parallel
    def session_lock(self, sid):
        with self._locks_guard:
            if len(self._locks) > 5000:
                # Drop only locks nobody holds. Clearing everything would let two concurrent
                # requests of one session run in parallel (each with its own fresh lock).
                for k in list(self._locks):
                    lk = self._locks[k]
                    if lk.acquire(blocking=False):
                        try:
                            del self._locks[k]
                        finally:
                            lk.release()
            return self._locks.setdefault(sid, threading.RLock())

    def ping(self):
        """Raise if the progress database can't be queried (used by /healthz)."""
        with self._db_lock:
            self._conn.execute("SELECT 1").fetchone()

    # ---- sandbox cache
    def _sandbox(self, sid, lab_id):
        key = (sid, lab_id)
        with self._cache_lock:
            sb = self._sandboxes.pop(key, None)
            if sb is None:
                sb = {}
            self._sandboxes[key] = sb
            while len(self._sandboxes) > SANDBOX_CACHE_MAX:
                self._sandboxes.popitem(last=False)
            return sb

    # ---- load / save
    def load(self, sid, lab_id):
        with self._db_lock:
            row = self._conn.execute("SELECT data FROM progress WHERE sid=? AND lab_id=?",
                                     (sid, lab_id)).fetchone()
        prog = new_progress()
        if row:
            try:
                saved = json.loads(row[0])
                if isinstance(saved, dict):
                    prog.update({k: v for k, v in saved.items() if k in prog and k != "sandbox"})
            except (ValueError, TypeError):
                pass                              # corrupt row -> start fresh rather than crash
        prog["sandbox"] = self._sandbox(sid, lab_id)
        return prog

    def snapshot(self, prog):
        """Serialised durable state, used to detect whether a request changed anything."""
        return json.dumps(_durable(prog), sort_keys=True, default=str)

    def save(self, sid, lab_id, prog, before=None):
        blob = self.snapshot(prog)
        if before is not None and blob == before:
            return False
        with self._db_lock:
            self._conn.execute(
                "INSERT INTO progress (sid, lab_id, data, updated) VALUES (?,?,?,?) "
                "ON CONFLICT(sid, lab_id) DO UPDATE SET data=excluded.data, updated=excluded.updated",
                (sid, lab_id, blob, time.time()))
        self._maybe_purge()
        return True

    # ---- reset
    def reset_lab(self, sid, lab_id):
        with self._db_lock:
            self._conn.execute("DELETE FROM progress WHERE sid=? AND lab_id=?", (sid, lab_id))
        with self._cache_lock:
            self._sandboxes.pop((sid, lab_id), None)

    def reset_all(self, sid):
        with self._db_lock:
            self._conn.execute("DELETE FROM progress WHERE sid=?", (sid,))
        with self._cache_lock:
            for k in [k for k in self._sandboxes if k[0] == sid]:
                del self._sandboxes[k]

    # ---- expiry
    def purge(self, ttl=SESSION_TTL_SECONDS):
        with self._db_lock:
            self._conn.execute("DELETE FROM progress WHERE updated < ?", (time.time() - ttl,))
        self._last_purge = time.time()

    def _maybe_purge(self):
        if time.time() - self._last_purge > PURGE_EVERY_SECONDS:
            self.purge()

    def close(self):
        with self._db_lock:
            self._conn.close()
