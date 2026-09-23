# app/schemas/research.py
from typing import Literal

from pydantic import BaseModel, Field


class ResearchPlan(BaseModel):
    """Kế hoạch nghiên cứu phân rã từ đề tài ban đầu do Orchestrator Agent khởi tạo."""

    topic: str = Field(description="Chủ đề nghiên cứu được chỉ định")
    sub_queries: list[str] = Field(
        min_length=1,
        max_length=5,
        description="Danh sách 3-5 câu hỏi tìm kiếm đa chiều độc lập",
    )
    expected_metrics: list[str] = Field(
        default_factory=list,
        description="Các chỉ số số liệu cụ thể cần đối soát thực tế",
    )


class Finding(BaseModel):
    """Đơn vị thông tin và bằng chứng trích xuất từ tài liệu do Researcher Agent thu thập."""

    claim: str = Field(description="Luận điểm hoặc sự kiện trích xuất được")
    evidence: str = Field(
        description="Đoạn văn trích dẫn nguyên văn làm bằng chứng xác thực"
    )
    source_url: str = Field(description="Đường dẫn URL của nguồn dữ liệu")
    source_title: str = Field(description="Tiêu đề bài viết hoặc tên tổ chức xuất bản")
    published_at: str | None = Field(
        default=None, description="Thời điểm xuất bản bài viết nếu có"
    )


class FollowUpRequest(BaseModel):
    """Yêu cầu tra cứu bổ sung do Analyst Agent kích hoạt khi dữ liệu xung đột hoặc chưa đủ."""

    questions: list[str] = Field(
        description="Danh sách câu hỏi cần tập trung tra cứu bổ sung"
    )
    preferred_sources: list[str] = Field(
        default_factory=list,
        description="Loại nguồn tin cậy cần ưu tiên tìm kiếm",
    )


class ResearcherOutput(BaseModel):
    """Kết quả thu thập dữ liệu tổng hợp của Researcher Agent."""

    status: Literal["complete", "partial", "failed"] = Field(
        default="complete",
        description="Trạng thái hoàn thành của quá trình tìm kiếm",
    )
    findings: list[Finding] = Field(
        default_factory=list,
        description="Danh sách các phát hiện kèm trích dẫn chứng cứ",
    )
    search_queries: list[str] = Field(
        default_factory=list,
        description="Danh sách các truy vấn tìm kiếm đã thực thi",
    )
    limitations: list[str] = Field(
        default_factory=list,
        description="Các giới hạn gặp phải trong quá trình thu thập",
    )


class AnalystOutput(BaseModel):
    """Kết quả kiểm chứng chéo và đánh giá độ tin cậy từ Analyst Agent."""

    status: Literal["complete", "needs_more_research"] = Field(
        description="Trạng thái hoàn tất đánh giá hoặc yêu cầu thêm vòng tra cứu"
    )
    confidence_score: float = Field(
        ge=0.0, le=1.0, description="Điểm tin cậy tổng thể từ 0.0 đến 1.0"
    )
    verified_findings: list[Finding] = Field(
        default_factory=list,
        description="Danh sách các phát hiện đã được đối chiếu chéo và xác thực",
    )
    conclusions: list[str] = Field(
        default_factory=list,
        description="Các kết luận chính rút ra sau khi phân tích",
    )
    insights: list[str] = Field(
        default_factory=list,
        description="Các góc nhìn chuyên sâu và insight giá trị từ dữ liệu",
    )
    conflicts: list[str] = Field(
        default_factory=list,
        description="Danh sách mâu thuẫn số liệu phát hiện giữa các nguồn",
    )
    limitations: list[str] = Field(
        default_factory=list,
        description="Các giới hạn dữ liệu cần lưu ý trong báo cáo",
    )
    follow_up_request: FollowUpRequest | None = Field(
        default=None,
        description="Yêu cầu tra cứu bổ sung chi tiết nếu status là needs_more_research",
    )


class Citation(BaseModel):
    """Mục trích dẫn tài liệu tham khảo trong báo cáo nghiên cứu."""

    id: int = Field(description="Chỉ số trích dẫn tương ứng trong văn bản [1], [2]...")
    title: str = Field(description="Tiêu đề bài viết hoặc tài liệu nguồn")
    url: str = Field(description="Đường dẫn liên kết gốc đến bài viết")
    snippet: str = Field(description="Đoạn văn trích dẫn ngắn minh chứng cho luận điểm")


class WriterOutput(BaseModel):
    """Báo cáo nghiên cứu khoa học hoàn chỉnh do Writer Agent tổng hợp."""

    status: Literal["complete", "partial"] = Field(
        default="complete", description="Trạng thái hoàn thiện của báo cáo"
    )
    title: str = Field(description="Tiêu đề chính thức của bài báo cáo nghiên cứu")
    content: str = Field(
        description="Toàn văn nội dung báo cáo chi tiết theo định dạng Markdown chuẩn"
    )
    citations: list[Citation] = Field(
        default_factory=list,
        description="Danh mục tài liệu tham khảo được đánh số",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Cảnh báo nổi bật về dữ liệu mâu thuẫn hoặc giới hạn nghiên cứu",
    )