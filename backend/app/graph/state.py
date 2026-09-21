from typing import TypedDict

from app.schemas.research import (
    AnalystOutput,
    Finding,
    ResearchPlan,
    WriterOutput,
)


class AgentState(TypedDict):
    """
    Trạng thái chia sẻ trung tâm của LangGraph StateGraph.
    Lưu trữ toàn bộ dữ liệu ngữ cảnh của một phiên nghiên cứu từ đầu vào đến báo cáo cuối cùng.
    Định kiểu nghiêm ngặt (Strict Type-Safety) bằng các model Pydantic cụ thể, không sử dụng Any.
    """

    # --- Thông tin định danh & phiên làm việc ---
    thread_id: str
    topic: str

    # --- Kế hoạch phân rã từ Orchestrator Agent ---
    plan: ResearchPlan | None

    # --- Dữ liệu bằng chứng thu thập từ Researcher Agent ---
    findings: list[Finding]
    search_queries: list[str]

    # --- Kết quả đối soát & thẩm định từ Analyst Agent ---
    analysis: AnalystOutput | None

    # --- Báo cáo khoa học cuối cùng từ Writer Agent ---
    final_report: WriterOutput | None

    # --- Kiểm soát luồng điều phối & lỗi ---
    retry_count: int
    errors: list[str]
