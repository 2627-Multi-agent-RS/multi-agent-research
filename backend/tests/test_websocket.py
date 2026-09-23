from fastapi.testclient import TestClient

from app.main import app
from app.services.research_service import normalize_graph_event


def test_health_check() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_mock_research_stream(monkeypatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "use_mock_research", True)

    with TestClient(app) as client, client.websocket_connect("/ws/research?thread_id=test-thread") as websocket:
        acknowledged = websocket.receive_json()
        assert acknowledged["type"] == "connection_ack"
        assert acknowledged["payload"]["session_id"] == "test-thread"

        websocket.send_json({"topic": "Tình hình xe điện toàn cầu năm 2025", "thread_id": "test-thread"})
        received_types = []
        final_report_event = None

        while True:
            event = websocket.receive_json()
            received_types.append(event["type"])
            if event["type"] == "final_report":
                final_report_event = event
                break

    assert "agent_status" in received_types
    assert "sources_updated" in received_types
    assert "analysis_summary" in received_types
    assert final_report_event is not None
    assert final_report_event["payload"]["status"] == "complete"
    assert len(final_report_event["payload"]["citations"]) >= 3


def test_websocket_validation_error() -> None:
    with TestClient(app) as client, client.websocket_connect("/ws/research?thread_id=test-thread") as websocket:
        _ = websocket.receive_json()  # connection_ack
        websocket.send_json({"topic": "   ", "thread_id": "test-thread"})  # blank topic
        error_event = websocket.receive_json()
        assert error_event["type"] == "error"
        assert error_event["status"] == "failed"
        assert error_event["payload"]["code"] == 400


def test_normalize_graph_event_orchestrator() -> None:
    start_events = normalize_graph_event(
        "thread-1",
        {
            "event": "on_chain_start",
            "name": "orchestrator",
        },
    )
    assert len(start_events) == 1
    assert start_events[0].type == "agent_status"
    assert start_events[0].status == "running"
    assert start_events[0].agent == "orchestrator"

    end_events = normalize_graph_event(
        "thread-1",
        {
            "event": "on_chain_end",
            "name": "orchestrator",
            "data": {
                "output": {
                    "search_queries": ["q1", "q2"],
                }
            },
        },
    )
    assert len(end_events) == 1
    assert end_events[0].status == "completed"
    assert end_events[0].agent == "orchestrator"


def test_normalize_graph_event_researcher_sources() -> None:
    events = normalize_graph_event(
        "thread-1",
        {
            "event": "on_chain_end",
            "name": "researcher",
            "data": {
                "output": {
                    "findings": [
                        {"source_url": "https://a.com", "source_title": "A"},
                        {"source_url": "https://a.com", "source_title": "A duplicate"},
                        {"source_url": "https://b.com", "source_title": "B"},
                    ]
                }
            },
        },
    )
    assert len(events) == 2
    assert events[0].type == "agent_status"
    assert events[0].status == "completed"
    assert events[1].type == "sources_updated"
    assert len(events[1].payload["sources"]) == 2


def test_normalize_graph_event_analyst_with_conflicts() -> None:
    events = normalize_graph_event(
        "thread-1",
        {
            "event": "on_chain_end",
            "name": "analyst",
            "data": {
                "output": {
                    "analysis": {
                        "status": "needs_more_research",
                        "confidence_score": 0.65,
                        "conflicts": ["Nguồn A và B chênh lệch số liệu GDP"],
                        "limitations": ["Chưa có dữ liệu quý 4"],
                    }
                }
            },
        },
    )
    assert len(events) == 3
    assert events[0].type == "agent_status"
    assert events[0].status == "completed"
    assert events[1].type == "agent_status"
    assert events[1].status == "warning"
    assert "Dữ liệu xung đột" in events[1].message
    assert events[2].type == "analysis_summary"
    assert events[2].payload["confidence"] == 0.65
    assert len(events[2].payload["conflicts"]) == 1


def test_normalize_graph_event_writer_report() -> None:
    events = normalize_graph_event(
        "thread-1",
        {
            "event": "on_chain_end",
            "name": "writer",
            "data": {
                "output": {
                    "final_report": {
                        "status": "complete",
                        "title": "Báo cáo cuối cùng",
                        "content": "# Nội dung",
                        "citations": [{"id": 1, "title": "A", "url": "https://a.com", "snippet": "s"}],
                        "warnings": [],
                    }
                }
            },
        },
    )
    assert len(events) == 2
    assert events[0].type == "agent_status"
    assert events[1].type == "final_report"
    assert events[1].payload["title"] == "Báo cáo cuối cùng"
