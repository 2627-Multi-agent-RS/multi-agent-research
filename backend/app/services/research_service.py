"""Translate LangGraph execution into stable frontend WebSocket events."""
import asyncio
from collections.abc import AsyncIterator
from typing import Any

from loguru import logger

from app.schemas.websocket import WebSocketEvent, make_event
from app.services.connection_mgr import ConnectionManager

NODE_PROGRESS: dict[str, tuple[int, int]] = {
    "orchestrator": (5, 25),
    "researcher": (30, 55),
    "analyst": (60, 75),
    "writer": (80, 100),
}

NODE_MESSAGES: dict[str, str] = {
    "orchestrator": "Đang lập kế hoạch nghiên cứu...",
    "researcher": "Đang tìm kiếm dữ liệu đa nguồn...",
    "analyst": "Đang đối soát chéo và tính điểm tin cậy...",
    "writer": "Đang viết báo cáo và lập danh mục trích dẫn...",
}


def build_initial_state(thread_id: str, topic: str) -> dict[str, Any]:
    """Khởi tạo trạng thái ban đầu AgentState theo hợp đồng với LangGraph."""
    return {
        "thread_id": thread_id,
        "topic": topic,
        "plan": None,
        "findings": [],
        "search_queries": [],
        "analysis": None,
        "final_report": None,
        "retry_count": 0,
        "errors": [],
    }


async def _mock_events(thread_id: str, topic: str) -> AsyncIterator[WebSocketEvent]:
    """Phát luồng sự kiện mẫu chuẩn xác phục vụ phát triển Frontend và kiểm thử tự động."""
    # 1. Orchestrator
    yield make_event(
        thread_id,
        "agent_status",
        agent="orchestrator",
        status="running",
        progress=10,
        message=NODE_MESSAGES["orchestrator"],
    )
    await asyncio.sleep(0.02)
    yield make_event(
        thread_id,
        "agent_status",
        agent="orchestrator",
        status="completed",
        progress=25,
        message="Orchestrator đã phân tách thành công các câu hỏi nghiên cứu.",
    )

    # 2. Researcher
    yield make_event(
        thread_id,
        "agent_status",
        agent="researcher",
        status="running",
        progress=35,
        message=NODE_MESSAGES["researcher"],
        payload={"sub_queries_count": 4, "current_sources_count": 6},
    )
    await asyncio.sleep(0.02)
    mock_sources = [
        {"url": "https://example.com/reports/electric-vehicles-2025", "title": "Báo cáo Thị trường Xe điện Toàn cầu 2025"},
        {"url": "https://example.com/analysis/battery-technology", "title": "Phân tích Xu hướng Công nghệ Pin Thế hệ mới"},
        {"url": "https://example.com/policy/clean-energy-subsidies", "title": "Chính sách Trợ cấp Năng lượng Sạch"},
    ]
    yield make_event(
        thread_id,
        "sources_updated",
        agent="researcher",
        payload={"sources": mock_sources},
    )
    yield make_event(
        thread_id,
        "agent_status",
        agent="researcher",
        status="completed",
        progress=55,
        message="Researcher đã thu thập và bóc tách dữ liệu từ các nguồn thành công.",
    )

    # 3. Analyst
    yield make_event(
        thread_id,
        "agent_status",
        agent="analyst",
        status="running",
        progress=65,
        message=NODE_MESSAGES["analyst"],
    )
    await asyncio.sleep(0.02)
    yield make_event(
        thread_id,
        "analysis_summary",
        agent="analyst",
        payload={
            "confidence": 0.92,
            "conflicts": [],
            "limitations": [],
        },
    )
    yield make_event(
        thread_id,
        "agent_status",
        agent="analyst",
        status="completed",
        progress=75,
        message="Analyst đã hoàn tất kiểm chứng chéo và đánh giá độ tin cậy.",
    )

    # 4. Writer
    yield make_event(
        thread_id,
        "agent_status",
        agent="writer",
        status="running",
        progress=85,
        message=NODE_MESSAGES["writer"],
    )
    await asyncio.sleep(0.02)
    yield make_event(
        thread_id,
        "agent_status",
        agent="writer",
        status="completed",
        progress=100,
        message="Writer đã hoàn thiện bản báo cáo nghiên cứu.",
    )
    yield make_event(
        thread_id,
        "final_report",
        agent="writer",
        status="completed",
        progress=100,
        payload={
            "status": "complete",
            "title": f"Báo cáo Nghiên cứu Chuyên sâu: {topic}",
            "content": f"# Báo cáo Nghiên cứu: {topic}\n\n## 1. Tóm tắt Tổng quan (Executive Summary)\nNghiên cứu tổng hợp các dữ liệu thực tế và xu hướng liên quan đến đề tài **{topic}** [1].\n\n## 2. Phân tích Dữ liệu Thực tế\nCác thống kê mới nhất cho thấy sự tăng trưởng vượt bậc trong ngành [2].\n\n## 3. Triển vọng & Đánh giá\nĐịnh hướng phát triển bền vững đang là trọng tâm [3].",
            "citations": [
                {
                    "id": 1,
                    "title": "Báo cáo Thị trường Xe điện Toàn cầu 2025",
                    "url": "https://example.com/reports/electric-vehicles-2025",
                    "snippet": "Dữ liệu thị trường xe điện toàn cầu năm 2025.",
                },
                {
                    "id": 2,
                    "title": "Phân tích Xu hướng Công nghệ Pin Thế hệ mới",
                    "url": "https://example.com/analysis/battery-technology",
                    "snippet": "Phân tích hiệu suất và mật độ năng lượng pin.",
                },
                {
                    "id": 3,
                    "title": "Chính sách Trợ cấp Năng lượng Sạch",
                    "url": "https://example.com/policy/clean-energy-subsidies",
                    "snippet": "Chính sách tài chính và hỗ trợ của các chính phủ.",
                },
            ],
            "warnings": [],
        },
    )


def _node_name(event: dict[str, Any]) -> str | None:
    name = event.get("name") or event.get("metadata", {}).get("langgraph_node")
    return name if name in NODE_PROGRESS else None


def normalize_graph_event(thread_id: str, event: dict[str, Any]) -> list[WebSocketEvent]:
    """Chuyển đổi LangGraph v2 stream event thành các WebSocketEvent chuẩn."""
    node = _node_name(event)
    if not node:
        return []

    kind = event.get("event", "")
    start_progress, end_progress = NODE_PROGRESS[node]

    # Node bắt đầu
    if kind.endswith("_start"):
        return [
            make_event(
                thread_id,
                "agent_status",
                agent=node,
                status="running",
                progress=start_progress,
                message=NODE_MESSAGES.get(node, f"Đang thực thi {node}..."),
            )
        ]

    # Node kết thúc
    if not kind.endswith("_end"):
        return []

    events: list[WebSocketEvent] = [
        make_event(
            thread_id,
            "agent_status",
            agent=node,
            status="completed",
            progress=end_progress,
            message=f"{node.capitalize()} đã hoàn thành.",
        )
    ]

    output = event.get("data", {}).get("output") or {}
    if not isinstance(output, dict):
        output = {}

    if node == "researcher":
        findings = output.get("findings", [])
        seen_urls: set[str] = set()
        sources: list[dict[str, str]] = []
        for finding in findings:
            if isinstance(finding, dict):
                url = finding.get("source_url")
                title = finding.get("source_title", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    sources.append({"url": url, "title": title})
        if sources:
            events.append(make_event(thread_id, "sources_updated", agent=node, payload={"sources": sources}))

    elif node == "analyst":
        analysis = output.get("analysis", output)
        if not isinstance(analysis, dict):
            analysis = {}
        status = analysis.get("status")
        if status == "needs_more_research":
            events.append(
                make_event(
                    thread_id,
                    "agent_status",
                    agent=node,
                    status="warning",
                    progress=end_progress,
                    message="Dữ liệu xung đột hoặc chưa đủ tin cậy, kích hoạt tìm kiếm bổ sung.",
                )
            )
        events.append(
            make_event(
                thread_id,
                "analysis_summary",
                agent=node,
                payload={
                    "confidence": analysis.get("confidence_score"),
                    "conflicts": analysis.get("conflicts", []),
                    "limitations": analysis.get("limitations", []),
                },
            )
        )

    elif node == "writer":
        report = output.get("final_report", output)
        events.append(
            make_event(
                thread_id,
                "final_report",
                agent=node,
                status="completed",
                progress=100,
                payload=report,
            )
        )

    return events


async def stream_research(
    thread_id: str,
    topic: str,
    manager: ConnectionManager,
    graph: Any | None = None,
    use_mock: bool = False,
) -> None:
    """Khởi chạy đồ thị nghiên cứu và broadcast stream sự kiện theo thời gian thực tới Client."""
    logger.bind(thread_id=thread_id).info("research_started: topic={}", topic)
    if use_mock:
        async for event in _mock_events(thread_id, topic):
            await manager.broadcast_to_thread(thread_id, event)
        return

    if graph is None:
        raise RuntimeError("Research graph is not available. Please ensure graph is compiled or enable USE_MOCK_RESEARCH.")

    config = {"configurable": {"thread_id": thread_id}}
    initial_state = build_initial_state(thread_id, topic)

    async for raw_event in graph.astream_events(initial_state, config=config, version="v2"):
        for event in normalize_graph_event(thread_id, raw_event):
            await manager.broadcast_to_thread(thread_id, event)
