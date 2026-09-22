"""WebSocket data contracts shared with the frontend."""
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

EventType = Literal[
    "connection_ack",
    "agent_status",
    "sources_updated",
    "analysis_summary",
    "final_report",
    "error",
]


class ResearchStartRequest(BaseModel):
    topic: str = Field(min_length=5, max_length=500, description="Đề tài nghiên cứu")
    thread_id: str = Field(min_length=1, max_length=128, description="Định danh phiên nghiên cứu")

    @field_validator("topic")
    @classmethod
    def topic_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("topic must not be blank")
        return value


class WebSocketEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{uuid4().hex[:12]}")
    thread_id: str
    type: EventType
    agent: str | None = None
    status: str | None = None
    progress: int | None = Field(default=None, ge=0, le=100)
    message: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any] = Field(default_factory=dict)


def make_event(thread_id: str, event_type: EventType, **kwargs: Any) -> WebSocketEvent:
    """Tạo gói tin WebSocket event chuẩn theo bảng mã sự kiện Section 7.3."""
    return WebSocketEvent(thread_id=thread_id, type=event_type, **kwargs)
