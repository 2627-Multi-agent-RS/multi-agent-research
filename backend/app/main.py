"""FastAPI entry point for the Multi-Agent Research System."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.websocket import router as websocket_router
from app.core.config import settings
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Cấu hình logging và khởi tạo hạ tầng khi FastAPI server khởi động."""
    configure_logging()
    yield


app = FastAPI(
    title="Multi-Agent Research System API",
    description="Realtime Multi-Agent Deep Research & Fact-Checking Gateway",
    version="1.0.0",
    lifespan=lifespan,
)

# Cấu hình CORS an toàn theo danh sách allowed_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký router WebSocket
app.include_router(websocket_router)


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Health check endpoint kiểm tra trạng thái máy chủ."""
    return {"status": "ok", "environment": settings.environment}
