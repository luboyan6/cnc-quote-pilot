"""Assemble a local LangChain graph with selected DeerFlow semantics."""

from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver

from .middleware import SkillAndSafetyMiddleware
from .prompts import SYSTEM_PROMPT
from .skills import SkillCatalog
from .state import CncAgentState


def build_graph(*, model: BaseChatModel, tools: list[BaseTool], catalog: SkillCatalog, checkpointer: BaseCheckpointSaver):
    names = [tool.name for tool in tools]
    if len(names) != len(set(names)):
        raise ValueError("DUPLICATE_TOOL_NAME")
    return create_agent(  # pyright: ignore[reportCallIssue]
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        middleware=[SkillAndSafetyMiddleware(catalog, set(names)), ToolCallLimitMiddleware(run_limit=20, exit_behavior="error")],  # pyright: ignore[reportArgumentType]
        state_schema=CncAgentState,
        checkpointer=checkpointer,
        name="cnc_lead",
    )
