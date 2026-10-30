"""Full checkpoint state with only the conversation and active skill names."""

from langchain.agents import AgentState


class CncAgentState(AgentState):
    skill_context: list[str]
