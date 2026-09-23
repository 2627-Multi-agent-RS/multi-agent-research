"""Realtime research WebSocket endpoint."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger
from pydantic import ValidationError

from app.api.deps import get_connection_manager, get_research_graph
from app.core.config import settings
from app.schemas.websocket import ResearchStartRequest, make_event
from app.services.research_service import stream_research

router = APIRouter()


@router.websocket("/ws/research")
async def research_websocket(websocket: WebSocket) -> None:
    """Endpoint tiếp nhận kết nối WebSocket từ Frontend và truyền phát sự kiện Agent thời gian thực."""
    raw_thread_id = websocket.query_params.get("thread_id", "pending")
    manager = get_connection_manager()
    await manager.connect(websocket, raw_thread_id)
    active_thread_id = raw_thread_id

    try:
        # 1. Gửi xác nhận kết nối connection_ack
        await manager.send_event(
            websocket,
            make_event(
                active_thread_id,
                "connection_ack",
                payload={"session_id": active_thread_id},
            ),
        )

        # 2. Nhận yêu cầu khởi tạo nghiên cứu { topic, thread_id }
        payload = await websocket.receive_json()
        request = ResearchStartRequest.model_validate(payload)

        # 3. Đồng bộ thread_id nếu client cung cấp thread_id mới
        if active_thread_id != request.thread_id:
            manager.move_to_thread(websocket, active_thread_id, request.thread_id)
            active_thread_id = request.thread_id

        # 4. Lấy đồ thị StateGraph và thực thi truyền phát luồng sự kiện
        graph = get_research_graph()
        await stream_research(
            thread_id=active_thread_id,
            topic=request.topic,
            manager=manager,
            graph=graph,
            use_mock=settings.use_mock_research,
        )

    except WebSocketDisconnect:
        logger.bind(thread_id=active_thread_id).info("websocket_client_disconnected")
    except ValidationError as exc:
        logger.bind(thread_id=active_thread_id).warning(
            "invalid_research_request: {}", exc
        )
        await manager.send_event(
            websocket,
            make_event(
                active_thread_id,
                "error",
                status="failed",
                message="Dữ liệu yêu cầu nghiên cứu không hợp lệ.",
                payload={"code": 400, "detail": exc.errors(include_url=False)},
            ),
        )
    except Exception as exc:  # noqa: BLE001
        logger.bind(thread_id=active_thread_id).exception(
            "research_stream_failed: {}", exc
        )
        await manager.send_event(
            websocket,
            make_event(
                active_thread_id,
                "error",
                status="failed",
                message="Không thể hoàn tất phiên nghiên cứu do lỗi hệ thống.",
                payload={"code": 500, "detail": str(exc)},
            ),
        )
    finally:
        manager.disconnect(websocket, active_thread_id)
