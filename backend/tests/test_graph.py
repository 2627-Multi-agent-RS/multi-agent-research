"""Integration tests for the LangGraph StateGraph assembly and SQLite checkpointer."""

import asyncio
from unittest.mock import AsyncMock, patch

from app.graph.build import (
    ANALYST_NODE,
    ORCHESTRATOR_NODE,
    RESEARCHER_NODE,
    WRITER_NODE,
    build_research_graph,
    get_async_sqlite_checkpointer,
    get_sqlite_checkpointer,
)
from app.graph.state import AgentState
from app.schemas.research import ResearchPlan
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver


def _mock_plan() -> ResearchPlan:
    return ResearchPlan(
        topic="Future of AI Agents",
        sub_queries=[
            "Agent architectures 2026",
            "Multi-agent state checkpointing",
            "Autonomous evaluation benchmarks",
        ],
        expected_metrics=["Accuracy", "Latency"],
    )


def test_graph_topology_and_nodes() -> None:
    """Verifies that all required nodes are registered in the compiled graph."""
    graph = build_research_graph()
    node_names = set(graph.get_graph().nodes.keys())

    assert "__start__" in node_names
    assert ORCHESTRATOR_NODE in node_names
    assert RESEARCHER_NODE in node_names
    assert ANALYST_NODE in node_names
    assert WRITER_NODE in node_names
    assert "__end__" in node_names


def test_get_sqlite_checkpointer_sync() -> None:
    """Verifies that get_sqlite_checkpointer successfully sets up a synchronous SQLite saver."""
    saver = get_sqlite_checkpointer(":memory:")
    assert isinstance(saver, SqliteSaver)


def test_get_async_sqlite_checkpointer() -> None:
    """Verifies that get_async_sqlite_checkpointer sets up an asynchronous SQLite saver."""

    async def _test() -> None:
        saver = await get_async_sqlite_checkpointer(":memory:")
        assert isinstance(saver, AsyncSqliteSaver)

    asyncio.run(_test())


def test_graph_execution_single_pass_end_to_end() -> None:
    """
    Executes the compiled graph end-to-end where the Analyst completes on the first pass.
    Verifies that all state fields are updated sequentially.
    """

    async def _test() -> None:
        checkpointer = await get_async_sqlite_checkpointer(":memory:")
        graph = build_research_graph(checkpointer=checkpointer)

        initial_state: AgentState = {
            "thread_id": "thread-single-pass",
            "topic": "Future of AI Agents",
            "plan": None,
            "findings": [],
            "search_queries": [],
            "analysis": None,
            "final_report": None,
            "retry_count": 0,
            "errors": [],
        }

        with patch(
            "app.agents.orchestrator.agent.invoke_with_resilience",
            new_callable=AsyncMock,
        ) as mock_invoke:
            mock_invoke.return_value = _mock_plan()

            config = {"configurable": {"thread_id": "thread-single-pass"}}
            final_state = await graph.ainvoke(initial_state, config=config)

            # Assertions
            assert final_state["plan"] is not None
            assert len(final_state["findings"]) > 0
            assert final_state["analysis"] is not None
            assert final_state["analysis"].status == "complete"
            assert final_state["final_report"] is not None
            assert final_state["final_report"].status == "complete"
            assert len(final_state["final_report"].citations) > 0

    asyncio.run(_test())


def test_graph_execution_with_retry_loop() -> None:
    """
    Executes the compiled graph where initial findings are sparse, triggering
    the Analyst to request more research, looping back to Researcher, and then completing.
    """

    async def _test() -> None:
        checkpointer = await get_async_sqlite_checkpointer(":memory:")
        graph = build_research_graph(checkpointer=checkpointer)

        # Plan with only 1 sub-query to simulate sparse findings (<2 findings initially)
        sparse_plan = ResearchPlan(
            topic="Sparse Topic",
            sub_queries=["Single targeted query"],
            expected_metrics=[],
        )

        initial_state: AgentState = {
            "thread_id": "thread-retry-loop",
            "topic": "Sparse Topic",
            "plan": None,
            "findings": [],
            "search_queries": [],
            "analysis": None,
            "final_report": None,
            "retry_count": 0,
            "errors": [],
        }

        with patch(
            "app.agents.orchestrator.agent.invoke_with_resilience",
            new_callable=AsyncMock,
        ) as mock_invoke:
            mock_invoke.return_value = sparse_plan

            config = {"configurable": {"thread_id": "thread-retry-loop"}}
            final_state = await graph.ainvoke(initial_state, config=config)

            # Retry loop should have triggered once and incremented retry_count
            assert final_state["retry_count"] == 1
            assert final_state["analysis"] is not None
            assert final_state["analysis"].status == "complete"
            assert final_state["final_report"] is not None
            assert len(final_state["findings"]) >= 2

    asyncio.run(_test())


def test_graph_sqlite_state_persistence() -> None:
    """
    Verifies that state is checkpointed in SQLite and retrievable via aget_state(thread_id).
    """

    async def _test() -> None:
        checkpointer = await get_async_sqlite_checkpointer(":memory:")
        graph = build_research_graph(checkpointer=checkpointer)

        thread_id = "thread-persist-check"
        initial_state: AgentState = {
            "thread_id": thread_id,
            "topic": "Persistence Verification",
            "plan": None,
            "findings": [],
            "search_queries": [],
            "analysis": None,
            "final_report": None,
            "retry_count": 0,
            "errors": [],
        }

        with patch(
            "app.agents.orchestrator.agent.invoke_with_resilience",
            new_callable=AsyncMock,
        ) as mock_invoke:
            mock_invoke.return_value = _mock_plan()

            config = {"configurable": {"thread_id": thread_id}}
            await graph.ainvoke(initial_state, config=config)

            # Retrieve persisted state asynchronously from checkpointer
            snapshot = await graph.aget_state(config)
            assert snapshot is not None
            assert snapshot.values["topic"] == "Persistence Verification"
            assert snapshot.values["final_report"] is not None
            assert snapshot.values["plan"] is not None

    asyncio.run(_test())
