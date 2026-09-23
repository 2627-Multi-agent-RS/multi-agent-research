from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Đường dẫn tuyệt đối đến thư mục gốc của backend (chứa file .env)
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """
    Cấu hình trung tâm cho Multi-Agent Research System (MAS).
    Tự động tải biến môi trường từ file .env hoặc môi trường hệ thống.
    """

    # --- Cấu hình AI Model ---
    GEMINI_API_KEY: str = Field(
        default="", description="Google Gemini API Key để khởi tạo LLM"
    )
    PRIMARY_LLM_MODEL: str = Field(
        default="gemini-2.0-flash",
        description="Model LLM chính cho Orchestrator, Analyst và Writer",
    )
    FALLBACK_LLM_MODEL: str = Field(
        default="gemini-1.5-flash",
        description="Model LLM dự phòng khi model chính quá tải",
    )

    # --- Cấu hình Search Engine ---
    TAVILY_API_KEY: str = Field(
        default="", description="Tavily API Key cho tìm kiếm nghiên cứu sâu"
    )

    # --- Cấu hình Hệ thống ---
    ENVIRONMENT: str = Field(
        default="development",
        description="Môi trường chạy: development, testing, production",
    )
    LOG_LEVEL: str = Field(
        default="INFO", description="Mức độ ghi log: DEBUG, INFO, WARNING, ERROR"
    )
    CHECKPOINT_DB_PATH: str = Field(
        default="./storage/checkpoints.db",
        description="Đường dẫn file database SQLite cho LangGraph Checkpointer",
    )
    ALLOWED_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        description="Danh sách các domain được phép truy cập CORS, phân tách bởi dấu phẩy",
    )

    # Cấu hình nạp file .env từ backend/ hoặc thư mục hiện tại
    model_config = SettingsConfigDict(
        env_file=(BASE_DIR / ".env", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    @property
    def cors_origins(self) -> list[str]:
        """Chuyển đổi chuỗi ALLOWED_ORIGINS thành danh sách các URL sạch."""
        return [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]


# Khởi tạo singleton instance sử dụng toàn hệ thống
settings = Settings()
