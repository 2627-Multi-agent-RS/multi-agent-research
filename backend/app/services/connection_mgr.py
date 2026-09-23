"""Safe lifecycle management for active WebSocket connections."""
from collections import defaultdict

from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

from app.schemas.websocket import WebSocketEvent


class ConnectionManager:
    """Quản lý các kết nối WebSocket đang hoạt động theo thread_id và dọn dẹp chống rò rỉ bộ nhớ."""

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, websocket: WebSocket, thread_id: str) -> None:
        """Chấp nhận kết nối WebSocket và gán vào phiên thread_id."""
        await websocket.accept()
        self._connections[thread_id].add(websocket)
        logger.bind(thread_id=thread_id).info("websocket_connected")

    def disconnect(self, websocket: WebSocket, thread_id: str) -> None:
        """Ngắt và dọn dẹp socket khỏi thread_id tương ứng."""
        sockets = self._connections.get(thread_id)
        if not sockets:
            return
        sockets.discard(websocket)
        if not sockets:
            self._connections.pop(thread_id, None)
        logger.bind(thread_id=thread_id).info("websocket_disconnected")

    def move_to_thread(self, websocket: WebSocket, old_thread_id: str, new_thread_id: str) -> None:
        """Chuyển WebSocket sang thread_id mới khi client gửi payload với thread_id khác."""
        if old_thread_id == new_thread_id:
            return
        self.disconnect(websocket, old_thread_id)
        self._connections[new_thread_id].add(websocket)
        logger.bind(thread_id=new_thread_id).info("websocket_thread_assigned")

    async def send_event(self, websocket: WebSocket, event: WebSocketEvent) -> bool:
        """Gửi JSON an toàn đến một WebSocket client. Tự động dọn dẹp nếu socket đã đóng."""
        try:
            await websocket.send_json(event.model_dump(mode="json"))
            return True
        except (RuntimeError, OSError, WebSocketDisconnect) as exc:
            logger.bind(thread_id=event.thread_id).warning("websocket_send_failed: {}", exc)
            self.disconnect(websocket, event.thread_id)
            return False

    async def broadcast_to_thread(self, thread_id: str, event: WebSocketEvent) -> None:
        """Broadcast một sự kiện tới tất cả các tab/client đang lắng nghe cùng thread_id."""
        sockets = tuple(self._connections.get(thread_id, set()))
        for websocket in sockets:
            await self.send_event(websocket, event)

    def connection_count(self, thread_id: str) -> int:
        """Trả về số lượng kết nối đang mở của một thread_id."""
        return len(self._connections.get(thread_id, set()))
