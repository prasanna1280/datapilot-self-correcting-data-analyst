from autogen_agentchat.messages import TextMessage

from backend.datapilot.team import CODER, EXECUTOR, PLANNER, REVIEWER, execution_failed, select_next_speaker


def msgs(*pairs):
    return [TextMessage(source=s, content=c) for s, c in pairs]


def test_task_goes_to_planner():
    assert select_next_speaker(msgs(("user", "question"))) == PLANNER


def test_plan_goes_to_coder_then_executor():
    assert select_next_speaker(msgs(("user", "q"), (PLANNER, "1) ..."))) == CODER
    assert select_next_speaker(msgs(("user", "q"), (CODER, "```python\n```"))) == EXECUTOR


def test_execution_error_loops_back_to_coder():
    err = "The script ran, then exited with an error (POSIX exit code: 1)\nIts output was:\nKeyError: 'revenue'"
    assert execution_failed(err)
    assert select_next_speaker(msgs((CODER, "code"), (EXECUTOR, err))) == CODER


def test_execution_ok_goes_to_reviewer():
    assert select_next_speaker(msgs((CODER, "code"), (EXECUTOR, "Electronics Aug: 18.4 L"))) == REVIEWER


def test_reviewer_feedback_goes_back_to_coder():
    assert select_next_speaker(msgs((REVIEWER, "FEEDBACK: chart 2 has no axis labels"))) == CODER


def test_follow_up_restarts_at_planner():
    history = msgs((REVIEWER, "ANSWER ...\nAPPROVED"), ("user", "follow-up?"))
    assert select_next_speaker(history) == PLANNER


def test_complete_answer_without_approved_line_still_approves():
    from backend.datapilot.team import is_approved, reviewer_approved
    answer = "ANSWER\nElectronics fell.\n\nWHERE IT CAME FROM\nSouth.\n\nSUGGESTED NEXT QUESTION\nWhy?"
    assert is_approved(answer) and is_approved(answer + "\n\nAPPROVED")
    assert not is_approved("FEEDBACK: the ANSWER section lacks WHERE IT CAME FROM numbers")
    assert reviewer_approved(msgs((REVIEWER, answer)))
    assert not reviewer_approved(msgs((CODER, answer)))
