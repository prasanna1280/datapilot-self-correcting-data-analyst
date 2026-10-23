"""Turn the agent message stream into the 6-step pipeline view and a one-line transcript.

Steps (as in the spec): 01 Ask, 02 Plan, 03 Code, 04 Run, 05 Review, 06 Answer.
Each step has a state: pending | active | done | retry | error | waiting.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

STEPS = [
    ("01", "Ask", "Upload CSV and type a question"),
    ("02", "Plan", "Planner writes analysis steps"),
    ("03", "Code", "Coder writes Python"),
    ("04", "Run", "Executor runs it, returns result or error"),
    ("05", "Review", "Reviewer approves or sends back"),
    ("06", "Answer", "Human approves, gets answer + charts"),
]


@dataclass
class StepState:
    num: str
    name: str
    caption: str
    state: str = "pending"
    detail: str = ""


def step_states(kinds: list[str], *, running: bool, run_status: str | None = None,
                human_verdict: str | None = None) -> list[StepState]:
    """kinds = event kinds in order (task, plan, code, exec_ok, exec_error, feedback, approved)."""
    s = [StepState(n, name, cap) for n, name, cap in STEPS]
    ask, plan, code, run, review, answer = s
    ask.state, ask.detail = "done", "Question received"

    n_code = kinds.count("code")
    n_err = kinds.count("exec_error")
    n_fb = kinds.count("feedback")
    last = kinds[-1] if kinds else "task"

    if "plan" in kinds:
        plan.state, plan.detail = "done", "Plan ready"
    elif running:
        plan.state, plan.detail = "active", "Planning…"

    if n_code:
        code.state = "done"
        code.detail = f"{n_code} version{'s' if n_code > 1 else ''}" + (f" · {n_err + n_fb} fix{'es' if n_err + n_fb > 1 else ''}" if n_code > 1 else "")
    if n_err or kinds.count("exec_ok"):
        run.state = "done" if "exec_ok" in kinds else "error"
        run.detail = f"{n_err} error{'s' if n_err != 1 else ''} self-corrected" if n_err and "exec_ok" in kinds else (
            f"{n_err} error{'s' if n_err != 1 else ''}" if n_err else "Ran cleanly")
    if "approved" in kinds:
        review.state, review.detail = "done", "APPROVED" + (f" after {n_fb} feedback" if n_fb else "")
    elif n_fb:
        review.state, review.detail = "retry", f"{n_fb} feedback round{'s' if n_fb > 1 else ''}"

    if running:  # highlight where the loop is right now
        if last in ("plan",) or (last in ("exec_error", "feedback")):
            code.state, code.detail = "active", "Fixing error…" if last == "exec_error" else (
                "Applying feedback…" if last == "feedback" else "Writing analysis.py…")
            if last == "exec_error":
                run.state = "retry"
        elif last == "code":
            run.state, run.detail = "active", "Running in sandbox…"
        elif last == "exec_ok":
            review.state, review.detail = "active", "Reviewing…"

    if "approved" in kinds:
        if human_verdict == "accepted":
            answer.state, answer.detail = "done", "Approved by you"
        elif human_verdict == "rejected":
            answer.state, answer.detail = "error", "Rejected by you"
        else:
            answer.state, answer.detail = "waiting", "Awaiting your approval"
    elif not running and run_status == "limit":
        answer.state, answer.detail = "error", "Stopped at message limit"
        if review.state == "pending":
            review.state = "error"
    elif not running and run_status == "error":
        answer.state, answer.detail = "error", "Run failed"
    return s


# --------------------------------------------------------------------------- transcript
_CODE_BLOCK = re.compile(r"```.*?```", re.DOTALL)


def _first_lines(text: str, n: int = 2, width: int = 160) -> str:
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    out = " ".join(lines[:n])
    return out if len(out) <= width else out[: width - 1] + "…"


def last_error_line(text: str) -> str:
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    for ln in reversed(lines):
        if re.match(r"^[A-Za-z_.]*(Error|Exception|Timeout)\b", ln) or "was not approved" in ln:
            return ln
    return lines[-1] if lines else "error"


def one_line(kind: str, content: str) -> str:
    """Shortened transcript line, like the spec's 'agent conversation (shortened)'."""
    if kind == "task":
        return _first_lines(content.replace("Business question:", ""), 1)
    if kind == "code":
        prose = _CODE_BLOCK.sub("", content).strip()
        return _first_lines(prose, 1) if prose else "[writes analysis.py]"
    if kind == "exec_error":
        return "ERROR  " + last_error_line(content)
    if kind == "exec_ok":
        body = [ln for ln in content.splitlines() if ln.strip() and not ln.startswith("SAVED:")]
        saved = sum(1 for ln in content.splitlines() if ln.startswith("SAVED:"))
        lead = _first_lines("\n".join(ln for ln in body if set(ln.strip()) != {"-"} and ln.strip() != "RESULTS"), 1, 110)
        return f"OK. {lead}" + (f" … saved {saved} chart{'s' if saved != 1 else ''}" if saved else "")
    if kind == "feedback":
        return _first_lines(content.replace("FEEDBACK:", ""), 2)
    if kind == "approved":
        return "APPROVED"
    return _first_lines(content, 2)


def parse_answer(answer: str) -> dict[str, str]:
    """Split the Reviewer's final answer into its sections."""
    keys = ["ANSWER", "WHERE IT CAME FROM", "FILES", "SUGGESTED NEXT QUESTION"]
    out: dict[str, str] = {}
    current = None
    for line in answer.splitlines():
        if line.strip().upper() in keys:
            current = line.strip().upper()
            out[current] = ""
        elif current:
            out[current] += line + "\n"
    out = {k: v.strip() for k, v in out.items()}
    if not out:
        out["ANSWER"] = answer.strip()
    return out
