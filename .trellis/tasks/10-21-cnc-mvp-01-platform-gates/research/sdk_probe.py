"""Offline SDK feasibility: scripted decisions and SQLite checkpoints, never live quotes."""

import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from importlib.metadata import version
from itertools import chain
from pathlib import Path
from typing import Literal
from unittest.mock import patch

# This standalone fixture must not export traces or resolve a real model.
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["OTEL_SDK_DISABLED"] = "true"

import aiosqlite
from deepagents import create_deep_agent
from deepagents.backends import StateBackend
from deepagents.middleware.filesystem import FilesystemPermission
from deepagents.profiles import GeneralPurposeSubagentProfile, HarnessProfile, register_harness_profile
from langchain.agents.structured_output import ToolStrategy
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_core.utils.function_calling import convert_to_openai_tool
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from pydantic import BaseModel, ConfigDict, PrivateAttr

RESEARCH_DIRECTORY = Path(__file__).resolve().parent
TURNS = 52
CONFIG = {"configurable": {"thread_id": "fixture-owner:item-1:incident-1"}, "recursion_limit": 16}
EXCLUDED = frozenset({"write_todos", "task", "execute", "ls", "read_file", "write_file", "edit_file", "glob", "grep", "delete"})


class ProbeDecision(BaseModel):
    """A fixture-only decision; not the production RecoveryDecision contract."""

    model_config = ConfigDict(extra="forbid")
    source: Literal["scripted_fixture"]
    strategy: Literal["HANDOFF"]
    evidence_ref: Literal["fixture:unknown-page"]


class ProbeModel(GenericFakeChatModel):
    """Pre-initialized local fixture with a fail-closed final tool-set check."""

    model_name: str = "cnc-sdk-probe"
    _bound_names: set[str] = PrivateAttr(default_factory=set)

    def bind_tools(self, tools, **kwargs):
        names = {convert_to_openai_tool(candidate)["function"]["name"] for candidate in tools}
        expected = {"inspect_fixture", "ProbeDecision"}
        if names != expected:
            raise RuntimeError(f"Unexpected effective fixture tool set: {sorted(names)}")
        self._bound_names.update(names)
        return self


@tool
def inspect_fixture() -> dict:
    """Read a synthetic, non-sensitive unknown-page observation without any browser."""
    return {"source": "scripted_fixture", "page_kind": "unknown", "allowed_strategies": ["HANDOFF"], "evidence_ref": "fixture:unknown-page"}


def decision_message(turn: int) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": "ProbeDecision", "args": {"source": "scripted_fixture", "strategy": "HANDOFF", "evidence_ref": "fixture:unknown-page"}, "id": f"decision-{turn}"}],
    )


def build_probe(saver: AsyncSqliteSaver, *, first_run: bool):
    initial = [AIMessage(content="", tool_calls=[{"name": "inspect_fixture", "args": {}, "id": "observe-1"}])] if first_run else []
    responses = chain(initial, (decision_message(turn) for turn in range(TURNS + 1)))
    model = ProbeModel(messages=iter(responses))
    provider = model._get_ls_params()["ls_provider"]
    register_harness_profile(
        f"{provider}:{model.model_name}",
        HarnessProfile(excluded_tools=EXCLUDED, general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False)),
    )
    agent = create_deep_agent(
        name="cnc-sdk-feasibility-fixture",
        model=model,
        tools=[inspect_fixture],
        system_prompt="This is an offline SDK fixture. Read the synthetic observation and return only the typed HANDOFF decision. No external actions.",
        subagents=[],
        backend=StateBackend(),
        permissions=[FilesystemPermission(operations=["read", "write"], paths=["/**"], mode="deny")],
        response_format=ToolStrategy(ProbeDecision, handle_errors=False),
        checkpointer=saver,
    )
    if type(agent.channels["messages"]).__name__ != "DeltaChannel":
        raise RuntimeError("The actual compiled message channel is not the expected DeltaChannel")
    return agent, model


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def fingerprint(messages: list) -> str:
    payload = [message.model_dump(mode="json") for message in messages]
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


async def phase(database: Path, operation: str) -> dict:
    require(database.name == "checkpoint.sqlite", "Unexpected fixture database filename")
    require(database.parent.parent.resolve() == RESEARCH_DIRECTORY, "Fixture database outside the research directory")
    require(database.parent.name.startswith(".sdk-probe-"), "Fixture database outside its private temporary directory")
    require(version("deepagents") == "0.7.29", "Probe requires the verified SDK baseline")
    serde = JsonPlusSerializer(pickle_fallback=False, allowed_msgpack_modules=[ProbeDecision])
    async with aiosqlite.connect(database) as connection:
        saver = AsyncSqliteSaver(connection, serde=serde)
        agent, model = build_probe(saver, first_run=operation == "write")
        if operation == "write":
            for turn in range(TURNS):
                result = await agent.ainvoke({"messages": [HumanMessage(content=f"fixture-turn-{turn}", id=f"human-{turn}")]}, config=CONFIG)
                require(isinstance(result.get("structured_response"), ProbeDecision), "Typed structured output missing")
        before = await agent.aget_state(CONFIG)
        messages = before.values.get("messages", [])
        require({f"human-{turn}" for turn in range(TURNS)} <= {message.id for message in messages}, "Fixture history was lost")
        require(sum(isinstance(message, ToolMessage) and message.name == "inspect_fixture" for message in messages) == 1, "Observation missing or repeated")
        require(isinstance(before.values.get("structured_response"), ProbeDecision), "Typed decision did not survive checkpoint serialization")
        require(before.metadata["step"] > 50, "Probe did not cross the accumulated checkpoint boundary")
        require(not before.next, "Expected a settled fixture run")
        report = {"phase": operation, "message_count_before": len(messages), "digest_before": fingerprint(messages), "checkpoint_step": before.metadata["step"]}
        if operation == "read":
            isolated = await agent.aget_state({"configurable": {"thread_id": "fixture-owner:item-2:incident-2"}})
            require(not isolated.values, "Different thread leaked fixture state")
            resumed = await agent.ainvoke({"messages": [HumanMessage(content="fixture-after-process-restart", id="human-restart")]}, config=CONFIG)
            require(fingerprint(resumed["messages"][: len(messages)]) == report["digest_before"], "Restart changed preceding history")
            require(sum(isinstance(message, ToolMessage) and message.name == "inspect_fixture" for message in resumed["messages"]) == 1, "Restart repeated the observation")
            require(isinstance(resumed.get("structured_response"), ProbeDecision), "Restarted structured output missing")
            report.update({"thread_isolation": "PASS", "restart_append": "PASS", "observation_not_repeated": "PASS", "tools": sorted(model._bound_names)})
        else:
            report["tools"] = sorted(model._bound_names)
        return report


async def offline_phase(database: Path, operation: str) -> dict:
    # Windows creates its event-loop socketpair before entering this coroutine.
    with patch("socket.socket.connect", side_effect=RuntimeError("Network is disabled in the SDK fixture")):
        return await phase(database, operation)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=["write", "read"])
    parser.add_argument("--database", type=Path)
    args = parser.parse_args()
    if args.phase:
        require(args.database is not None, "Internal fixture phase requires a database")
        # SDK execution is offline, including tracing and lazy tokenizer fetches.
        print(json.dumps(asyncio.run(offline_phase(args.database.resolve(), args.phase)), sort_keys=True))
        return 0
    require(args.database is None, "Only internal child phases accept a database")
    with tempfile.TemporaryDirectory(prefix=".sdk-probe-", dir=RESEARCH_DIRECTORY) as temporary:
        root = Path(temporary).resolve()
        require(root.parent == RESEARCH_DIRECTORY, "Unexpected temporary directory before cleanup")
        database = root / "checkpoint.sqlite"
        reports = []
        for operation in ("write", "read"):
            result = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "--phase", operation, "--database", str(database)], capture_output=True, text=True, timeout=90, check=False)
            if result.returncode:
                print(f"FAIL SDK fixture {operation}: {result.stderr.strip() or result.stdout.strip()}", file=sys.stderr)
                return 1
            reports.append(json.loads(result.stdout))
        require(reports[0]["digest_before"] == reports[1]["digest_before"], "Cross-process checkpoint contents differ")
        require(reports[0]["message_count_before"] == reports[1]["message_count_before"], "Cross-process history length differs")
        print(json.dumps({"status": "PASS", "model": "scripted_fixture", "live_provider": "NOT_TESTED", "platform_quote": "NOT_TESTED", "turns_before_restart": TURNS, "reports": reports}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
