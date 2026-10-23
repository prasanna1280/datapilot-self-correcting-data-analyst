"""The DataPilot agent team.

Flow (decided at run time, not fixed):
    user -> Planner -> Coder -> Executor --error--> Coder (rewrite)
                                         --ok-----> Reviewer --feedback--> Coder
                                                             --APPROVED--> stop

We use SelectorGroupChat (the stretch goal) with a `selector_func` that encodes
the loop above. If the function returns None (an unexpected state), the LLM
selector picks the next speaker instead. Set TEAM_MODE=roundrobin to use the
basic RoundRobinGroupChat from the spec.
"""

from __future__ import annotations

import os
from typing import Sequence

from autogen_agentchat.agents import AssistantAgent, CodeExecutorAgent
from autogen_agentchat.base import TerminationCondition
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage
from autogen_agentchat.teams import BaseGroupChat, RoundRobinGroupChat, SelectorGroupChat
from autogen_core.code_executor import CodeExecutor
from autogen_core.models import ChatCompletionClient

from . import prompts
from .config import settings
from .safety import approve_code

PLANNER, CODER, EXECUTOR, REVIEWER = "Planner", "Coder", "Executor", "Reviewer"
APPROVED = "APPROVED"

# Markers AutoGen's CodeExecutorAgent / our executors put in failed results.
_ERROR_MARKERS = ("exited with an error", "Traceback (most recent call last)", "No code blocks found",
                  "Sandbox unavailable", "Sandbox rejected", "Timeout:",
                  "was not approved")


def execution_failed(text: str) -> bool:
    return any(m in text for m in _ERROR_MARKERS)


def is_approved(text: str) -> bool:
    return text.rstrip().endswith(APPROVED)


def select_next_speaker(messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> str | None:
    """Deterministic routing for the self-correction loop."""
    chat = [m for m in messages if isinstance(m, BaseChatMessage)]
    if not chat:
        return PLANNER
    last = chat[-1]
    text = last.to_text()
    if last.source == PLANNER:
        return CODER
    if last.source == CODER:
        return EXECUTOR
    if last.source == EXECUTOR:
        return CODER if execution_failed(text) else REVIEWER
    if last.source == REVIEWER:
        return None if is_approved(text) else CODER  # approved -> termination fires first
    # A new task / follow-up from the user always starts with a fresh plan.
    return PLANNER


def make_model_client() -> ChatCompletionClient:
    from autogen_ext.models.openai import OpenAIChatCompletionClient

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Add it to .env (see .env.example).")
    return OpenAIChatCompletionClient(model=settings.model, api_key=settings.openai_api_key, temperature=0)


def make_termination(max_messages: int | None = None) -> TerminationCondition:
    # Only the Reviewer can approve, so a Planner saying "until APPROVED" can't end the run.
    return TextMentionTermination(APPROVED, sources=[REVIEWER]) | MaxMessageTermination(
        max_messages or settings.max_messages
    )


def build_team(
    model_client: ChatCompletionClient,
    code_executor: CodeExecutor,
    *,
    max_messages: int | None = None,
    mode: str | None = None,
) -> BaseGroupChat:
    planner = AssistantAgent(
        PLANNER, model_client=model_client, system_message=prompts.PLANNER,
        description="Writes a short step-by-step analysis plan from the question and data columns.",
    )
    coder = AssistantAgent(
        CODER, model_client=model_client, system_message=prompts.CODER,
        description="Writes the Python (pandas + matplotlib) script and fixes it after errors or feedback.",
    )
    executor = CodeExecutorAgent(
        EXECUTOR, code_executor=code_executor, sources=[CODER], supported_languages=["python"], approval_func=approve_code,
        description="Runs the Coder's script in the sandbox and returns output or errors.",
    )
    reviewer = AssistantAgent(
        REVIEWER, model_client=model_client, system_message=prompts.REVIEWER,
        description="Checks results, numbers and chart labels; replies APPROVED or sends feedback.",
    )
    participants = [planner, coder, executor, reviewer]
    termination = make_termination(max_messages)

    if (mode or os.environ.get("TEAM_MODE", "selector")).lower() == "roundrobin":
        return RoundRobinGroupChat(participants, termination_condition=termination)
    return SelectorGroupChat(
        participants,
        model_client=model_client,
        termination_condition=termination,
        selector_func=select_next_speaker,
        allow_repeated_speaker=True,
    )
