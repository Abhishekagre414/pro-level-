# -*- coding: utf-8 -*-
"""
Helpers shared by the storyline-1 (sandbox.py) and storyline-2 (sandbox2.py)
terminal bridges. These used to be copy-pasted into both files.

Security notes
  * Every number a learner types is untrusted. `num` / `int_arg` reject NaN and
    +/-inf and clamp to a range, so `--noise nan`, `pad 99999999999` or
    `test-keys 1000000` can't crash a handler or burn unbounded CPU.
  * `execute` never lets an exception escape: a bad command returns a short
    message instead of a 500, and nothing is ever passed to a shell/eval.
"""
import logging
import math
import shlex

log = logging.getLogger("labdemo.sandbox")

MAX_LINE = 300   # characters accepted per terminal command
MAX_ARGS = 16    # tokens accepted per terminal command


def rec(mod, prog, action, friendly):
    """Record an action if its dependencies are met. Returns a note (or '')."""
    if action in prog["actions"]:
        return ""
    missing = [d for d in mod.ACTION_DEPENDENCIES.get(action, []) if d not in prog["actions"]]
    if missing:
        return "\n[i] Progress not recorded yet. First: " + friendly.get(missing[0], missing[0])
    prog["actions"].append(action)
    return ""


def parse(args):
    """Split args into positionals and --flags (supports `--k v` and `--k=v`)."""
    pos, flags, i = [], {}, 0
    while i < len(args):
        a = args[i]
        if a.startswith("--"):
            key = a[2:]
            if "=" in key:
                k, v = key.split("=", 1)
                flags[k] = v
            elif i + 1 < len(args) and not args[i + 1].startswith("--"):
                flags[key] = args[i + 1]
                i += 1
            else:
                flags[key] = True
        else:
            pos.append(a)
        i += 1
    return pos, flags


def num(v, default, lo=None, hi=None):
    """Parse a float safely: non-numeric / NaN / inf -> default; clamp to [lo, hi]."""
    try:
        x = float(v)
    except (TypeError, ValueError, OverflowError):
        return default
    if not math.isfinite(x):
        return default
    if lo is not None:
        x = max(lo, x)
    if hi is not None:
        x = min(hi, x)
    return x


def int_arg(v, default, lo, hi):
    """Parse an int safely (accepts '5', '5.0', '1e3'); always returns lo <= n <= hi."""
    return int(num(v, default, lo, hi))


def state(prog):
    """Per-lab live sandbox state (not persisted; rebuilt on demand)."""
    return prog["sandbox"]


def execute(labs, whoami, lab_id, mod, prog, line):
    """Parse and run one terminal command for `lab_id` against the `labs` table."""
    line = (line or "").strip() if isinstance(line, str) else ""
    if not line:
        return ""
    if len(line) > MAX_LINE:
        return f"error: command too long (max {MAX_LINE} characters)."
    try:
        parts = shlex.split(line)
    except ValueError:
        return "parse error: unbalanced quotes"
    if not parts:
        return ""
    if len(parts) > MAX_ARGS:
        return f"error: too many arguments (max {MAX_ARGS})."
    cmd, args = parts[0], parts[1:]
    lab = labs[lab_id]
    if cmd == "help":
        return lab["help"]
    if cmd == "whoami":
        return whoami
    fn = lab["cmds"].get(cmd)
    if not fn:
        return f"{cmd}: command not found. Type 'help' to see the tools in this sandbox."
    try:
        return fn(mod, prog, args)
    except Exception:  # a learner typo must never become a 500 or leak a traceback
        log.exception("sandbox command failed: lab=%s cmd=%r", lab_id, cmd)
        return f"{cmd}: that command failed. Check usage with 'help'."
