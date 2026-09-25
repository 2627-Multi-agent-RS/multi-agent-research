# KẾ HOẠCH PHÂN CHIA CÔNG VIỆC DỰ ÁN MULTI-AGENT RESEARCH SYSTEM (MAS)
> **Dự án:** Hệ thống Multi-Agent hỗ trợ Deep Research, Fact-Checking & Realtime Streaming  

---

## 1. BẢNG PHÂN VAI TỔNG QUAN (TEAM ROLES OVERVIEW)

| STT | Thành viên | Vai trò (Role) | Trách nhiệm trọng tâm | Module / Thư mục chính |
| :---: | :--- | :--- | :--- | :--- |
| **1** | **Hoàng** | **Graph Orchestrator** | Thiết kế đồ thị LangGraph StateGraph, Routing logic, Planner Node, Architecture Integrity & Hợp nhất mã nguồn. | `backend/app/graph/`<br>`backend/app/agents/orchestrator/` |
| **2** | **Cường** | **Data Retrieval & Tool Engineer** | Xây dựng Researcher Agent, tích hợp Tavily Search, DuckDuckGo, Trafilatura Deep Web Scraper, lọc trùng và tối ưu song song. | `backend/app/agents/researcher/`<br>`backend/app/tools/search/`<br>`backend/app/tools/scrapers/` |
| **3** | **Hiệu** | **Reasoning & Synthesis AI Engineer** | Xây dựng Analyst Agent (kiểm chứng chéo, tính điểm tin cậy) và Writer Agent (tổng hợp báo cáo, footnotes citations, warnings). | `backend/app/agents/analyst/`<br>`backend/app/agents/writer/`<br>`backend/app/schemas/research.py` |
| **4** | **Dũng** | **Backend & Realtime Gateway Engineer** | FastAPI Server, WebSocket Router `/ws/research`, Event Streaming (`astream_events`), LLM Factory & Tenacity Resilience. | `backend/app/api/`<br>`backend/app/services/`<br>`backend/app/tools/llm/`<br>`backend/app/core/` |
| **5** | **Huy** | **Frontend Realtime & UX Engineer** | React + Vite + TypeScript, Custom Hook `useResearchSocket`, Form nhập liệu (`ResearchInput`), Timeline 4 Agents (`AgentTimeline`). | `frontend/src/hooks/`<br>`frontend/src/components/research/ResearchInput.tsx`<br>`frontend/src/components/research/AgentTimeline.tsx` |
| **6** | **Hảo** | **Frontend Deliverables & DevOps / QA** | Trình đọc báo cáo (`MarkdownReport` + Footnotes), Sidebar nguồn (`SourceViewer`), Docker Compose & Bộ test tự động (Pytest). | `frontend/src/components/research/MarkdownReport.tsx`<br>`frontend/src/components/research/SourceViewer.tsx`<br>`docker-compose.yml`, `backend/tests/` |

---

## 2. CHI TIẾT NHIỆM VỤ TỪNG THÀNH VIÊN

---

### Hoàng: GRAPH ORCHESTRATOR
* **Mục tiêu**: Đảm bảo xương sống điều phối của hệ thống hoạt động chính xác, không lặp vô hạn và các node giao tiếp chuẩn xác qua State chung.
* **Công việc cụ thể**:
  1. **Khởi tạo đồ án**: Tạo Git repository, thiết lập Git flow (main, dev, feature branches), quy chuẩn commit và PR review.
  2. **Xây dựng StateGraph (`app/graph/`)**:
     * `state.py`: Khai báo cấu trúc `AgentState` lưu trữ phiên làm việc.
     * `build.py`: Khởi tạo đồ thị `StateGraph`, đăng ký 4 nodes (`orchestrator`, `researcher`, `analyst`, `writer`).
     * `routing.py`: Lập trình hàm `should_continue_research` kiểm soát feedback loop (`retry_count < 1`).
     * Tích hợp `SqliteSaver` checkpointer để lưu phiên làm việc theo `thread_id`.
  3. **Xây dựng Node Orchestrator (`app/agents/orchestrator/`)**:
     * Viết System Prompt phân tích mục tiêu nghiên cứu.
     * Bóc tách đề tài thành 3–5 `sub_queries` góc nhìn độc lập kèm `expected_metrics`.
  4. **Code Review & Release**: Quản trị việc merge code của cả 6 thành viên, giải quyết conflict.

---

### Cường: DATA RETRIEVAL & TOOL ENGINEER
* **Mục tiêu**: Thu thập dữ liệu Internet nhanh nhất có thể bằng cơ chế song song, đảm bảo có cả bản tóm tắt nhanh và văn bản gốc chuyên sâu.
* **Công việc cụ thể**:
  1. **Tích hợp Search Engines (`app/tools/search/`)**:
     * `tavily_tool.py`: Viết adapter gọi Tavily Search API (`advanced` search, trích xuất ngữ cảnh RAG).
     * `ddg_tool.py`: Viết adapter gọi DuckDuckGo Search đóng vai trò nguồn bổ trợ miễn phí.
     * `engine.py`: Viết hàm `parallel_search(queries: List[str])` chạy đồng thời bằng `asyncio.gather()`, loại bỏ trùng lặp theo `source_url`.
  2. **Deep Content Scraper (`app/tools/scrapers/web_reader.py`)**:
     * Sử dụng thư viện `trafilatura` để cào toàn văn bài viết của top 3 URL chất lượng nhất.
     * Làm sạch HTML rác, quảng cáo, bảng điều hướng; cắt chunk tối đa 1.500 tokens để tránh làm tràn Context Window của LLM.
  3. **Xây dựng Researcher Agent (`app/agents/researcher/`)**:
     * Tiếp nhận danh sách `sub_queries` và `follow_up_request` từ State.
     * Trích xuất các sự kiện thành danh sách Pydantic `Finding` (gồm `claim`, `evidence`, `source_url`, `source_title`, `published_at`).
     * Ghi nhận các điểm hạn chế vào `limitations` nếu nguồn bị chặn/lỗi.

---

### Hiệu: REASONING & SYNTHESIS AI ENGINEER
* **Mục tiêu**: Chịu trách nhiệm về "bộ não" phân tích phản biện và khả năng hành văn của báo cáo khoa học.
* **Công việc cụ thể**:
  1. **Định nghĩa Hợp đồng dữ liệu (`app/schemas/research.py`)**:
     * Phối hợp cùng Team Lead chuẩn hóa Pydantic v2 Models: `ResearchPlan`, `Finding`, `AnalystOutput`, `WriterOutput`, `Citation`.
  2. **Xây dựng Analyst Agent (`app/agents/analyst/`)**:
     * Viết System Prompt chuyên sâu về đối soát chéo và tư duy phản biện.
     * Đối chiếu chéo các findings: phát hiện xung đột số liệu (`conflicts`).
     * Tính toán chỉ số tin cậy `confidence_score` (`0.0` - `1.0`).
     * Tạo `follow_up_request` với câu hỏi định hướng nếu `confidence_score < 0.75`.
  3. **Xây dựng Writer Agent (`app/agents/writer/`)**:
     * Viết prompt sinh báo cáo chuyên sâu chuẩn Markdown (Executive Summary, Findings, In-depth Analysis, Outlook).
     * Thuật toán gắn chỉ số trích dẫn `[1]`, `[2]` vào văn bản tương ứng với danh mục `citations`.
     * **Graceful Degradation**: Tự động chèn khối `Cảnh báo & Giới hạn dữ liệu` nếu phát hiện mâu thuẫn hoặc sau 1 lần retry mà dữ liệu vẫn chưa đủ.

---

### Dũng: BACKEND & REALTIME GATEWAY ENGINEER
* **Mục tiêu**: Xây dựng máy chủ FastAPI ổn định, chịu tải tốt, chống sập API và truyền phát sự kiện mượt mà qua WebSocket.
* **Công việc cụ thể**:
  1. **Tầng lõi & Cấu hình (`app/core/`)**:
     * `config.py`: Dùng `pydantic-settings` load và kiểm định các biến môi trường (`.env`).
     * `logging.py`: Thiết lập `loguru` format log JSON, xoay vòng file log (log rotation).
  2. **LLM Factory & Chống sập (`app/tools/llm/factory.py`)**:
     * Khởi tạo `ChatGoogleGenerativeAI` với model chính `gemini-2.0-flash` và model dự phòng `gemini-1.5-flash`.
     * Tích hợp thư viện `tenacity`: Tự động thử lại với thuật toán **Exponential Backoff with Jitter** khi gặp lỗi HTTP 429 (Rate Limit) hoặc 503.
  3. **WebSocket Gateway & Connection Manager (`app/api/websocket.py`, `app/services/`)**:
     * Tạo WebSocket router tại endpoint `/ws/research`.
     * `ConnectionManager`: Quản lý danh sách kết nối mở, gửi nhận JSON an toàn, chống leak memory khi client đóng tab đột ngột.
     * `research_service.py`: Cắm hàm `graph.astream_events()` để bóc tách sự kiện `on_node_start` / `on_node_end` và broadcast gói tin `agent_status` xuống Client theo thời gian thực.

---

### Huy: FRONTEND REALTIME & UX ENGINEER
* **Mục tiêu**: Xây dựng trải nghiệm người dùng hiện đại, hiển thị trực quan các bước suy luận của từng Agent theo thời gian thực.
* **Công việc cụ thể**:
  1. **Khởi tạo Frontend**: Cài đặt React + Vite + TypeScript + Tailwind CSS + Lucide Icons. Đồng bộ Typescript Interface khớp 100% với Pydantic schemas của Backend.
  2. **Custom Hook WebSocket (`src/hooks/useResearchSocket.ts`)**:
     * Thiết lập kết nối hai chiều tới `ws://localhost:8000/ws/research`.
     * Quản lý trạng thái: `isConnected`, `agentStatus`, `sources`, `report`, `error`.
     * Xử lý cơ chế tự động kết nối lại (Auto-reconnect) khi rớt mạng tạm thời.
  3. **Component Nhập liệu (`src/components/research/ResearchInput.tsx`)**:
     * Form nhập đề tài nghiên cứu, validate độ dài ký tự, nút gửi và hiệu ứng loading.
  4. **Component Tiến trình Agent (`src/components/research/AgentTimeline.tsx`)**:
     * Trực quan hóa tiến trình 4 Agent (Orchestrator -> Researcher -> Analyst -> Writer).
     * Hiển thị trạng thái động bằng Badge màu: Đang chờ (Xám), Đang chạy (Xanh/Spinner), Cảnh báo lặp (Vàng), Hoàn thành (Xanh lá).
     * Hiển thị message tiến độ chi tiết của agent đang chạy ("Đang tìm kiếm song song cho 4 câu hỏi con...").

---

### Hảo: FRONTEND DELIVERABLES & DEVOPS / QA
* **Mục tiêu**: Hoàn thiện giao diện đọc báo cáo học thuật, đóng gói toàn bộ hệ thống lên Docker và viết bộ kiểm thử tự động.
* **Công việc cụ thể**:
  1. **Component Hiển thị Báo cáo (`src/components/research/MarkdownReport.tsx`)**:
     * Dùng `react-markdown` + `remark-gfm` + `rehype-highlight` hiển thị định dạng đẹp (bảng, tiêu đề, code block, in đậm).
     * Xây dựng tính năng tương tác với trích dẫn: Click vào số `[1]`, `[2]` sẽ cuộn trang xuống danh mục nguồn tương ứng hoặc mở popup tóm tắt nguồn.
  2. **Component Danh sách Nguồn & Cảnh báo (`SourceViewer.tsx`, `ConflictWarning.tsx`)**:
     * Thanh Sidebar hiển thị danh sách các bài viết đã quét thời gian thực (Favicon, tiêu đề, domain, ngày đăng).
     * Banner cảnh báo mâu thuẫn số liệu nổi bật.
  3. **DevOps & Docker hóa**:
     * Viết `backend/Dockerfile` (Multi-stage Python 3.11).
     * Viết `frontend/Dockerfile` (Build Vite rồi serve bằng Nginx Alpine).
     * Hoàn thiện `docker-compose.yml`: Khởi chạy 1 lệnh `docker-compose up` lên toàn bộ cả FE và BE.
  4. **Bộ Test tự động (Pytest)**:
     * Viết `tests/test_agents.py`: Unit test từng agent với mock dữ liệu.
     * Viết `tests/test_graph.py`: Integration test kiểm tra đồ thị chạy đúng luồng thẳng và luồng quay lại Researcher.
