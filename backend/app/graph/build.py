"""StateGraph assembly, routing configuration, and checkpointer integration."""

import sqlite3
from pathlib import Path
from typing import Final

import aiosqlite
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.analyst.agent import run_analyst
from app.agents.orchestrator.agent import run_orchestrator
from app.agents.researcher.agent import run_researcher
from app.agents.writer.agent import run_writer
from app.core.config import settings
from app.graph.routing import (
    RESEARCHER_NODE,
    WRITER_NODE,
    should_continue_research,
)
from app.graph.state import AgentState

ORCHESTRATOR_NODE = "orchestrator"
ANALYST_NODE = "analyst"

CHECKPOINT_MSGPACK_ALLOWLIST: Final = [
    ("app.schemas.research", "AnalystOutput"),
    ("app.schemas.research", "Finding"),
    ("app.schemas.research", "ResearchPlan"),
    ("app.schemas.research", "WriterOutput"),
]


def make_checkpoint_serde() -> JsonPlusSerializer:
    """Serde dùng chung cho mọi SQLite checkpointer của hệ thống."""
    return JsonPlusSerializer(allowed_msgpack_modules=CHECKPOINT_MSGPACK_ALLOWLIST)


def get_sqlite_checkpointer(
    db_path: str | Path | None = None,
) -> SqliteSaver:
    """
    Initialize and prepare a synchronous SqliteSaver checkpointer.

    Args:
        db_path: Target SQLite database file path, ':memory:' for in-memory DB,
                 or None to default to settings.CHECKPOINT_DB_PATH.

    Returns:
        Configured SqliteSaver with initialized schema tables.
    """
    target_path = str(db_path) if db_path is not None else settings.CHECKPOINT_DB_PATH

    if target_path != ":memory:":
        path_obj = Path(target_path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(target_path, check_same_thread=False)
    saver = SqliteSaver(conn, serde=make_checkpoint_serde())
    saver.setup()
    return saver


async def get_async_sqlite_checkpointer(
    db_path: str | Path | None = None,
) -> AsyncSqliteSaver:
    """
    Initialize and prepare an asynchronous AsyncSqliteSaver checkpointer for async workflows.

    Args:
        db_path: Target SQLite database file path, ':memory:' for in-memory DB,
                 or None to default to settings.CHECKPOINT_DB_PATH.

    Returns:
        Configured AsyncSqliteSaver with initialized schema tables.
    """
    target_path = str(db_path) if db_path is not None else settings.CHECKPOINT_DB_PATH

    if target_path != ":memory:":
        path_obj = Path(target_path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)

    conn = await aiosqlite.connect(target_path)
    saver = AsyncSqliteSaver(conn, serde=make_checkpoint_serde())
    await saver.setup()
    return saver


def build_research_graph(
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    """
    Construct, wire edges, and compile the Multi-Agent Research StateGraph.

    Graph Topology:
        START -> orchestrator -> researcher -> analyst
        analyst -> should_continue_research:
            - "researcher" (if follow-up needed and retry budget < 1)
            - "writer" (if complete or retry budget exhausted)
        writer -> END

    Args:
        checkpointer: Optional LangGraph BaseCheckpointSaver for thread persistence.

    Returns:
        CompiledStateGraph ready for invoke/stream execution.
    """
    builder = StateGraph(AgentState)

    builder.add_node(ORCHESTRATOR_NODE, run_orchestrator)
    builder.add_node(RESEARCHER_NODE, run_researcher)
    builder.add_node(ANALYST_NODE, run_analyst)
    builder.add_node(WRITER_NODE, run_writer)

    builder.add_edge(START, ORCHESTRATOR_NODE)
    builder.add_edge(ORCHESTRATOR_NODE, RESEARCHER_NODE)
    builder.add_edge(RESEARCHER_NODE, ANALYST_NODE)

    builder.add_conditional_edges(
        ANALYST_NODE,
        should_continue_research,
        {
            RESEARCHER_NODE: RESEARCHER_NODE,
            WRITER_NODE: WRITER_NODE,
        },
    )

    builder.add_edge(WRITER_NODE, END)

    return builder.compile(checkpointer=checkpointer)


__all__ = [
    "ANALYST_NODE",
    "ORCHESTRATOR_NODE",
    "RESEARCHER_NODE",
    "WRITER_NODE",
    "build_research_graph",
    "get_async_sqlite_checkpointer",
    "get_sqlite_checkpointer",
]
