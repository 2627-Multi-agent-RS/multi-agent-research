from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.orchestrator.prompts import ORCHESTRATOR_SYSTEM_PROMPT
from app.graph.state import AgentState
from app.schemas.research import ResearchPlan
from app.tools.llm.factory import LLMFactory, invoke_with_resilience


class OrchestratorUpdate(TypedDict):
    """Specific partial state update returned by the Orchestrator node."""

    plan: ResearchPlan
    search_queries: list[str]


async def run_orchestrator(state: AgentState) -> OrchestratorUpdate:
    """
    Node Orchestrator: Receives a raw research topic, decomposes it into 3-5
    analytical sub-queries with expected metrics, and updates the agent state.
    """
    raw_topic = state.get("topic", "")
    topic = raw_topic.strip() if raw_topic else ""

    if not topic:
        raise ValueError("Research topic cannot be empty or whitespace.")

    model = LLMFactory.get_primary_model(temperature=0.2)
    messages = [
        SystemMessage(content=ORCHESTRATOR_SYSTEM_PROMPT),
        HumanMessage(content=f"Đề tài nghiên cứu cần phân rã: {topic}"),
    ]

    plan: ResearchPlan = await invoke_with_resilience(
        model=model,
        prompt_messages=messages,
        structured_schema=ResearchPlan,
    )

    return {
        "plan": plan,
        "search_queries": plan.sub_queries,
    }
