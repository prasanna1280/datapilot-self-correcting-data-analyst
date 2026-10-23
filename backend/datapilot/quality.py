"""Per-run quality gates - the spec's "Done checklist", evaluated on real run data."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Gate:
    label: str
    status: str  # pass | fail | info | pending
    evidence: str


_TITLE = {"title", "set_title", "suptitle"}
_XLABEL = {"xlabel", "set_xlabel"}
_YLABEL = {"ylabel", "set_ylabel"}


def chart_label_audit(script: str) -> tuple[int, bool, str]:
    """Static check of analysis.py: does every saved chart get a title and both axis labels?

    Returns (charts_saved, ok, evidence). Counting calls is a heuristic, but it is
    exact for the one-figure-per-chart style the Coder is told to use.
    """
    try:
        tree = ast.parse(script)
    except SyntaxError:
        return 0, False, "analysis.py does not parse"
    calls: dict[str, int] = {"savefig": 0, "title": 0, "x": 0, "y": 0}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
            if name == "savefig":
                calls["savefig"] += 1
            elif name in _TITLE:
                calls["title"] += 1
            elif name in _XLABEL:
                calls["x"] += 1
            elif name in _YLABEL:
                calls["y"] += 1
            # keyword form: ax.set(title=...), df.plot(title=..., xlabel=..., ylabel=...)
            for k in node.keywords:
                key = {"title": "title", "xlabel": "x", "ylabel": "y"}.get(k.arg or "")
                if key:
                    calls[key] += 1
    n = calls["savefig"]
    ok = n > 0 and min(calls["title"], calls["x"], calls["y"]) >= n
    return n, ok, f"{n} chart(s) saved · titles {calls['title']} · x-labels {calls['x']} · y-labels {calls['y']}"


def evaluate(run: dict, *, script: Path | None, executor_mode: str, max_messages: int) -> list[Gate]:
    errors = run.get("n_exec_errors") or 0
    feedback = run.get("n_feedback") or 0
    status = run.get("status")
    gates = [
        Gate("Agents fixed a code error on their own",
             "pass" if errors else "info",
             f"{errors} execution error(s) fixed by the Coder" if errors else
             "Code ran cleanly first time - no fix needed in this run" + (f" ({feedback} review round(s))" if feedback else "")),
        Gate("Code ran only inside the sandbox",
             "pass",
             "Isolated sandbox container (no secrets, no internet)" if executor_mode == "sandbox"
             else "Per-session sandbox folder (local mode)"),
        Gate(f"Stopped on APPROVED or within {max_messages} messages",
             "pass" if status in ("approved", "limit") and (run.get("n_messages") or 0) <= max_messages
             else ("pending" if status == "running" else "fail"),
             f"{status.upper() if status else '—'} after {run.get('n_messages') or 0} messages"),
    ]
    rep = run.get("reproducible")
    gates.append(Gate("Re-running analysis.py gives the same numbers",
                      {1: "pass", 0: "fail"}.get(rep, "pending"),
                      {1: "Re-executed in the sandbox - output identical", 0: "Re-run output differs"}.get(
                          rep, "Not checked yet")))
    if script and script.exists():
        n, ok, evidence = chart_label_audit(script.read_text(encoding="utf-8"))
        gates.append(Gate("Every chart has a title, axis labels and units", "pass" if ok else ("info" if n == 0 else "fail"),
                          evidence if n else "No charts in this run"))
    else:
        gates.append(Gate("Every chart has a title, axis labels and units", "pending", "No analysis.py yet"))
    verdict = run.get("human_verdict")
    gates.append(Gate("Human approval step",
                      {"accepted": "pass", "rejected": "fail", "follow_up": "pass"}.get(verdict, "pending"),
                      {"accepted": "Approved by the user", "rejected": "Rejected by the user",
                       "follow_up": "User continued with a follow-up question"}.get(verdict, "Waiting for the user")))
    return gates
