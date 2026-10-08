(function () {
  const R = JSON.parse(document.getElementById("room-data").textContent);
  const CSRF = document.querySelector('meta[name="csrf-token"]').content;
  const out = document.getElementById("term-out");
  const input = document.getElementById("term-in");
  const term = document.getElementById("term");
  const history = [];
  let hpos = 0;

  function post(url, body) {
    return fetch(`/lab/${R.labId}/${url}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": CSRF },
      body: JSON.stringify(body || {}),
    }).then((r) => r.json());
  }

  function append(text, cls) {
    const d = document.createElement("div");
    if (cls) d.className = cls;
    d.textContent = text;
    out.appendChild(d);
    term.scrollTop = term.scrollHeight;
  }

  function refreshEvidence(unlocked, earned) {
    if (earned) Object.assign(R.evidence, earned);   // the server only ever sends text for unlocked items
    let n = 0;
    R.evidenceIds.forEach((k) => {
      const el = document.getElementById("ev-" + k);
      if (!el) return;
      const on = unlocked.indexOf(k) !== -1;
      if (on) n++;
      el.classList.toggle("on", on);
      const info = R.evidence[k];
      el.querySelector(".ev-title").textContent = on && info ? info.title : "Locked";
      el.querySelector(".ev-desc").textContent = on && info ? info.description : "";
    });
    document.getElementById("ev-count").textContent = n + "/" + R.evidenceIds.length;
  }

  input.addEventListener("keydown", function (e) {
    if (e.key === "ArrowUp") {
      if (hpos > 0) hpos--;
      input.value = history[hpos] || "";
      e.preventDefault();
    } else if (e.key === "ArrowDown") {
      if (hpos < history.length) hpos++;
      input.value = history[hpos] || "";
      e.preventDefault();
    } else if (e.key === "Enter") {
      const cmd = input.value.trim();
      input.value = "";
      if (!cmd) return;
      history.push(cmd);
      hpos = history.length;
      append(R.prompt + ":~$ " + cmd, "echo");
      if (cmd === "clear") {
        out.innerHTML = "";
        return;
      }
      post("term", { cmd: cmd }).then((res) => {
        if (res.output) append(res.output);
        if (res.unlocked) refreshEvidence(res.unlocked, res.evidence);
      });
    }
  });
  term.addEventListener("click", () => input.focus());

  // ---- answers
  document.querySelectorAll(".question").forEach((qEl) => {
    const btn = qEl.querySelector(".ans-btn");
    const msg = qEl.querySelector(".q-msg");
    const qid = qEl.dataset.qid;
    const txt = qEl.querySelector(".q-input");
    const hintBtn = qEl.querySelector(".hint-q");
    if (hintBtn) {
      hintBtn.addEventListener("click", () => {
        const h = qEl.querySelector(".q-hint");
        h.hidden = !h.hidden;
      });
    }
    if (txt) txt.addEventListener("keydown", (e) => { if (e.key === "Enter") btn.click(); });
    btn.addEventListener("click", () => {
      let answer;
      if (qEl.dataset.qtype === "choice") {
        const sel = qEl.querySelector("input[name='" + qid + "']:checked");
        if (!sel) { msg.textContent = "Pick an option first."; msg.className = "q-msg bad"; return; }
        answer = sel.value;
      } else {
        answer = txt.value.trim();
        if (!answer) return;
      }
      post("answer", { qid: qid, answer: answer }).then((res) => {
        msg.textContent = res.message || "";
        msg.className = "q-msg " + (res.correct ? "ok" : "bad");
        if (!res.ok) return;
        if (res.correct) {
          qEl.classList.add("solved");
          if (txt) { txt.disabled = true; }
          btn.disabled = true;
          qEl.querySelectorAll("input[type=radio]").forEach((r) => (r.disabled = true));
          document.getElementById("pts").textContent = (res.points100 !== undefined ? res.points100 : res.points);
          document.getElementById("tasks-done").textContent = res.done_tasks;
          Object.keys(res.task_done).forEach((tid) => {
            const t = document.getElementById("task-" + tid);
            if (t) t.classList.toggle("done", res.task_done[tid]);
          });
          if (res.room_done) {
            document.getElementById("flag-val").textContent = res.flag;
            document.getElementById("flag-box").hidden = false;
          }
        }
      });
    });
  });

  // ---- hints
  const hintBtn = document.getElementById("hint-btn");
  const hintBox = document.getElementById("hint-box");
  let used = parseInt(document.getElementById("hint-count").textContent.replace(/[^0-9]/g, ""), 10) || 0;
  hintBtn.addEventListener("click", () => {
    post("hint").then((res) => {
      hintBox.hidden = false;
      const p = document.createElement("div");
      p.textContent = (res.level ? "Hint " + res.level + " (-" + res.penalty + " score): " : "") + res.text;
      hintBox.appendChild(p);
      if (res.level) used = res.level;
      document.getElementById("hint-count").textContent = "(" + used + "/" + R.hintsTotal + ")";
    });
  });

  // ---- Start Lab / lab timer (a stopwatch kept in this browser tab; the terminal only works while it runs)
  const KEY = "labdemo.timer." + R.labId;
  const tBtn = document.getElementById("lab-toggle");
  const tVal = document.getElementById("lab-time");
  const tState = document.getElementById("lab-state");
  const tDot = document.getElementById("ab-dot");
  const tLocked = document.getElementById("term-locked");
  const RUN = String((document.getElementById("labbar") || {}).dataset ? document.getElementById("labbar").dataset.run : "0");
  let timer = { running: false, startedAt: 0, accMs: 0, run: RUN };
  try {
    const saved = JSON.parse(sessionStorage.getItem(KEY) || "null");
    // a timer saved before the last "Reset Lab" belongs to the old run, so it is dropped
    if (saved && saved.run === RUN && typeof saved.accMs === "number" && typeof saved.startedAt === "number") timer = saved;
  } catch (e) { /* storage unavailable: start from zero */ }
  function saveTimer() { try { sessionStorage.setItem(KEY, JSON.stringify(timer)); } catch (e) { /* ignore */ } }
  function elapsed() { return timer.accMs + (timer.running ? Date.now() - timer.startedAt : 0); }
  function fmt(ms) {
    const t = Math.floor(ms / 1000), h = Math.floor(t / 3600), m = Math.floor((t % 3600) / 60), s = t % 60;
    return [h, m, s].map((n) => String(n).padStart(2, "0")).join(":");
  }
  function renderTimer() {
    tVal.textContent = fmt(elapsed());
    tBtn.innerHTML = timer.running ? "&#9632; Stop Lab" : (timer.accMs ? "&#9654; Resume Lab" : "&#9654; Start Lab");
    tBtn.classList.toggle("running", timer.running);
    tState.textContent = timer.running ? "Running" : "Stopped";
    tState.classList.toggle("on", timer.running);
    tDot.classList.toggle("off", !timer.running);
    tLocked.hidden = timer.running;
    input.disabled = !timer.running;
    if (timer.running && document.activeElement === document.body) input.focus();
  }
  tBtn.addEventListener("click", () => {
    if (timer.running) { timer.accMs += Date.now() - timer.startedAt; timer.running = false; }
    else { timer.startedAt = Date.now(); timer.running = true; }
    saveTimer();
    renderTimer();
    if (timer.running) input.focus();
  });
  renderTimer();
  setInterval(() => { if (timer.running) tVal.textContent = fmt(elapsed()); }, 1000);

  // ---- AttackBox desktop
  function win(id, show) {
    const w = document.getElementById(id);
    if (!w) return;
    w.hidden = !show;
    if (show && id === "term-win") input.focus();
  }
  document.querySelectorAll("[data-open]").forEach((b) => b.addEventListener("click", () => win(b.dataset.open, true)));
  document.querySelectorAll("[data-close]").forEach((b) => b.addEventListener("click", () => win(b.dataset.close, false)));
  function tick() {
    const d = new Date();
    document.getElementById("ab-clock").textContent = d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
    document.getElementById("ab-date").textContent = d.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" }) + ", " + d.toLocaleTimeString([], { hour12: false });
  }
  tick();
  setInterval(tick, 30000);
})();
