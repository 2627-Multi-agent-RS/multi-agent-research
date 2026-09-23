import pytest

from app.schemas.websocket import make_event
from app.services.connection_mgr import ConnectionManager


class FakeWebSocket:
    def __init__(self) -> None:
        self.accepted = False
        self.messages: list[dict] = []

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, message: dict) -> None:
        self.messages.append(message)


class BrokenWebSocket(FakeWebSocket):
    async def send_json(self, message: dict) -> None:
        raise OSError("socket closed")


@pytest.mark.asyncio
async def test_manager_connect_broadcast_and_disconnect() -> None:
    manager = ConnectionManager()
    first = FakeWebSocket()
    second = FakeWebSocket()

    await manager.connect(first, "thread-1")
    await manager.connect(second, "thread-1")

    assert first.accepted and second.accepted
    assert manager.connection_count("thread-1") == 2

    event = make_event("thread-1", "agent_status", agent="researcher", status="running", progress=30)
    await manager.broadcast_to_thread("thread-1", event)

    assert len(first.messages) == 1
    assert len(second.messages) == 1
    assert first.messages[0]["type"] == "agent_status"
    assert first.messages[0]["agent"] == "researcher"

    manager.disconnect(first, "thread-1")
    assert manager.connection_count("thread-1") == 1

    manager.disconnect(second, "thread-1")
    assert manager.connection_count("thread-1") == 0


@pytest.mark.asyncio
async def test_manager_move_to_thread() -> None:
    manager = ConnectionManager()
    socket = FakeWebSocket()

    await manager.connect(socket, "old-thread")
    assert manager.connection_count("old-thread") == 1
    assert manager.connection_count("new-thread") == 0

    manager.move_to_thread(socket, "old-thread", "new-thread")
    assert manager.connection_count("old-thread") == 0
    assert manager.connection_count("new-thread") == 1


@pytest.mark.asyncio
async def test_manager_removes_socket_when_delivery_fails() -> None:
    manager = ConnectionManager()
    broken_socket = BrokenWebSocket()

    await manager.connect(broken_socket, "thread-1")
    assert manager.connection_count("thread-1") == 1

    delivered = await manager.send_event(broken_socket, make_event("thread-1", "error"))
    assert delivered is False
    assert manager.connection_count("thread-1") == 0
