"""Static safety gate used as the Executor's approval_func.

This is a cheap first line of defence. The real isolation is the sandbox container
(no secrets, no network, read-only FS). Rejected code goes back to the Coder with
the reason, so it can rewrite the script, just like a runtime error.
"""

from __future__ import annotations

import ast

from autogen_agentchat.agents import ApprovalRequest, ApprovalResponse

ALLOWED_IMPORTS = {
    "pandas", "numpy", "matplotlib", "math", "statistics", "datetime", "calendar",
    "collections", "itertools", "functools", "json", "csv", "re", "decimal", "textwrap", "warnings", "pathlib",
}
BLOCKED_CALLS = {"eval", "exec", "compile", "__import__", "input", "breakpoint", "globals", "vars"}
BLOCKED_ATTRS = {"system", "popen", "environ", "getenv", "putenv", "remove", "unlink", "rmdir", "rmtree",
                 "chmod", "chown", "kill", "fork", "spawn", "read_pickle", "to_pickle", "read_sql", "to_sql"}


def check_code(code: str) -> str | None:
    """Return a reason string if the code is unsafe, else None."""
    code = code.strip()
    if code.startswith("```"):
        code = "\n".join(line for line in code.splitlines() if not line.startswith("```"))
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None  # let the Executor run it so the Coder sees Python's own error message
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            for name in names:
                if name.split(".")[0] not in ALLOWED_IMPORTS:
                    return f"import of '{name}' is not allowed (use pandas, numpy, matplotlib and the standard math/date libs)"
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in BLOCKED_CALLS:
            return f"call to {node.func.id}() is not allowed"
        elif isinstance(node, ast.Attribute) and node.attr in BLOCKED_ATTRS:
            return f"use of .{node.attr} is not allowed"
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and _is_outside_path(node.value):
            return f"path '{node.value}' is outside the sandbox folder; use files in the current folder only"
    return None


def _is_outside_path(s: str) -> bool:
    s = s.strip().replace("\\", "/")
    if " " in s or len(s) < 2:
        return False  # chart titles, separators, format strings
    return s.startswith(("/", "~/")) or "../" in s or s == ".." or (s[1:3] == ":/" and s[0].isalpha())


def approve_code(request: ApprovalRequest) -> ApprovalResponse:
    reason = check_code(request.code)
    if reason:
        return ApprovalResponse(approved=False, reason=f"Safety check failed: {reason}. Rewrite the script without it.")
    return ApprovalResponse(approved=True, reason="passed static safety check")
