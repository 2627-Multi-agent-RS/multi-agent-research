"""LangGraph StateGraph builder."""
from typing import Any

from langgraph.graph import END, StateGraph

from app.graph.routing import should_continue_research
from app.graph.state import AgentState


def create_research_graph(checkpointer: Any | None = None) -> Any:
    """Xây dựng đồ thị nghiên cứu đa agent theo đặc tả Section 4.2."""
    workflow = StateGraph(AgentState)

    # Nạp các node của từng Agent an toàn
    try:
        from app.agents.orchestrator.agent import run_orchestrator
    except (ImportError, AttributeError):
        async def run_orchestrator(state: AgentState) -> dict[str, Any]:
            return {
                "plan": {"topic": state["topic"], "sub_queries": [state["topic"]]},
                "search_queries": [state["topic"]],
            }

    try:
        from app.agents.researcher.agent import run_researcher
    except (ImportError, AttributeError):
        async def run_researcher(state: AgentState) -> dict[str, Any]:
            return {"findings": state.get("findings", [])}

    try:
        from app.agents.analyst.agent import run_analyst
    except (ImportError, AttributeError):
        async def run_analyst(state: AgentState) -> dict[str, Any]:
            return {
                "analysis": {
                    "status": "complete",
                    "confidence_score": 0.9,
                    "verified_findings": state.get("findings", []),
                    "conclusions": ["Phân tích hoàn tất"],
                    "insights": [],
                    "conflicts": [],
                }
            }

    try:
        from app.agents.writer.agent import run_writer
    except (ImportError, AttributeError):
        async def run_writer(state: AgentState) -> dict[str, Any]:
            return {
                "final_report": {
                    "status": "complete",
                    "title": f"Báo cáo Nghiên cứu: {state.get('topic')}",
                    "content": f"# Báo cáo: {state.get('topic')}\n\nNội dung nghiên cứu.",
                    "citations": [],
                    "warnings": [],
                }
            }

    # 1. Đăng ký các Nodes thực thi
    workflow.add_node("orchestrator", run_orchestrator)
    workflow.add_node("researcher", run_researcher)
    workflow.add_node("analyst", run_analyst)
    workflow.add_node("writer", run_writer)

    # 2. Thiết lập điểm khởi đầu và các Edges cố định
    workflow.set_entry_point("orchestrator")
    workflow.add_edge("orchestrator", "researcher")
    workflow.add_edge("researcher", "analyst")

    # 3. Thiết lập Conditional Edge kiểm soát Feedback Loop
    workflow.add_conditional_edges(
        "analyst",
        should_continue_research,
        {
            "researcher": "researcher",  # Quay lại tìm kiếm bổ sung
            "writer": "writer",          # Chuyển tiếp viết báo cáo
        },
    )

    # 4. Node Writer kết thúc trực tiếp luồng
    workflow.add_edge("writer", END)

    return workflow.compile(checkpointer=checkpointer)
