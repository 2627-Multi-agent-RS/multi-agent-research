# Merge Log & Testing Guide — Nhánh `Backend-demo`

> Ghi lại toàn bộ quá trình merge nhánh `Hieu` (Analyst + Writer Agent) với
> `feature/stategraph-orchestrator` (Hoàng — Graph, Orchestrator, Routing, State) vào nhánh
> tích hợp `Backend-demo`, cùng hướng dẫn chạy test đầy đủ cho người sau (hoặc chính mình sau này).

---

## 1. Bối cảnh

- Nhánh `Hieu`: implement `AnalystAgent`, `WriterAgent`, `schemas/research.py` — đã test thật với
  Gemini API, lint/mypy/pytest sạch, CI xanh.
- Nhánh `feature/stategraph-orchestrator`: implement `StateGraph`, `AgentState`, `routing.py`,
  `orchestrator/agent.py`, kèm **stub tạm** cho Analyst/Writer để graph compile được trước khi
  chờ code thật.
- Mục tiêu: merge cả 2 vào 1 nhánh tích hợp (`Backend-demo`) để test end-to-end trước khi đưa
  vào `main`, tránh merge thẳng `main` khi Researcher (Cường) chưa xong.

## 2. Các bước đã thực hiện

```powershell
git checkout main
git pull origin main
git checkout -b Backend-demo
git push origin Backend-demo

git merge origin/feature/stategraph-orchestrator
```

---

## 3. Các vấn đề đã gặp và cách xử lý

### 3.1. Conflict `add/add` ở 3 file — do cả 2 nhánh cùng tạo file mới

**File**: `app/agents/analyst/agent.py`, `app/agents/writer/agent.py`, `app/schemas/research.py`

**Nguyên nhân**: Hoàng viết stub tạm cho Analyst/Writer để test compile graph trước, còn nhánh
`Hieu` đã có code thật (gọi LLM, build citation, warning block). Cả 2 bên tạo cùng đường dẫn file
→ Git không tự merge được (`add/add` conflict).

**Cách xử lý**: Không xóa hẳn bên nào — **hợp nhất thủ công**:
- Giữ toàn bộ logic thật (gọi LLM, xử lý lỗi, build citation, graceful degradation) từ nhánh `Hieu`
- Lấy đúng type signature (`AgentState`, `AnalystUpdate`, `WriterUpdate` TypedDict) và field
  `retry_count`/`errors` từ bản của Hoàng — vì `routing.py` cần đọc đúng các key này
- File `schemas/research.py`: 2 bên định nghĩa giống hệt field/type, bản của Hoàng có thêm
  `description=` cho từng field (hữu ích cho LLM structured output) → giữ nguyên bản của Hoàng

```powershell
git add app/agents/analyst/agent.py app/agents/writer/agent.py app/schemas/research.py
git commit -m "merge: integrate Hieu real implementation with Hoang's AgentState typing"
git push origin Backend-demo
```

### 3.2. `mypy` báo lỗi ở `routing.py` và `factory.py` (không liên quan code Analyst/Writer)

```
app\graph\routing.py:31: error: Incompatible return value type (got "str", expected "Literal['researcher', 'writer']")
app\tools\llm\factory.py:81: error: Incompatible return value type ...
```

**Nguyên nhân**: Lỗi type hint có sẵn trong code của Hoàng/Dũng, chỉ lộ ra khi `mypy` quét toàn bộ
`app/` với đầy đủ code thật (trước đó Analyst/Writer còn là stub đơn giản nên chưa "đào sâu" tới).

**Xử lý**: Không tự sửa file người khác — báo lại đúng người phụ trách (Hoàng, Dũng) kèm log lỗi.

### 3.3. Thiếu dependency: `aiosqlite`, `langgraph-checkpoint-sqlite`

```
ModuleNotFoundError: No module named 'aiosqlite'
ModuleNotFoundError: No module named 'langgraph.checkpoint.sqlite'
```

**Nguyên nhân**: `app/graph/build.py` (Hoàng) dùng `SqliteSaver` checkpointer, cần 2 package này,
nhưng chưa được thêm vào `requirements.txt` chung.

```powershell
pip install aiosqlite langgraph-checkpoint-sqlite
pip freeze | findstr /i "aiosqlite langgraph-checkpoint-sqlite"
# thêm 2 dòng version vào requirements.txt
```

### 3.4. Test cũ của Analyst fail sau merge: `TypeError: 'AnalystOutput' object is not subscriptable`

**Nguyên nhân**: Sau khi hợp nhất, `run_analyst`/`run_writer` trả về **object** `AnalystOutput`/
`WriterOutput` thật (đúng kiểu `AnalystUpdate`/`WriterUpdate` mà Hoàng định nghĩa), không còn trả
`dict` như code gốc của Hieu (`.model_dump()`). Test cũ viết `result["analysis"]["status"]`
(kiểu dict) không còn đúng — phải sửa thành `result["analysis"].status` (truy cập bằng dấu chấm).

**Xử lý**: Cập nhật lại assertion trong `tests/test_agents.py` cho khớp kiểu trả về mới.

### 3.5. Test end-to-end lỗi thiếu API key khi chạy qua `pytest`

```
ValidationError: API key required for Gemini Developer API... input_value={'google_api_key': None...}
```

**Nguyên nhân**: `pytest` không tự động đọc file `.env` như lúc chạy script thường (`python
scratch_test.py` có gọi `load_dotenv()` thủ công, còn `pytest` thì không).

**Xử lý**: Tạo `tests/conftest.py`:
```python
from dotenv import load_dotenv
load_dotenv()
```
`pytest` tự động chạy file này trước mọi test cùng thư mục.

### 3.6. Test end-to-end bị treo/chạy chậm vì gọi LLM thật không giới hạn

**Vấn đề**: 3 test trong `test_graph.py` (`test_graph_execution_single_pass_end_to_end`,
`test_graph_execution_with_retry_loop`, `test_graph_sqlite_state_persistence`) chỉ mock
`invoke_with_resilience` của Orchestrator, KHÔNG mock của Analyst/Writer — khiến test gọi Gemini
API thật, có thể treo lâu hoặc tốn quota, và **chắc chắn fail trên CI** (CI dùng
`GEMINI_API_KEY=mock-gemini-key-for-ci`, không gọi API thật được).

**Xử lý tạm thời** (để verify các test khác không bị chặn):
```powershell
pytest tests/ -v `
  --deselect tests/test_graph.py::test_graph_execution_single_pass_end_to_end `
  --deselect tests/test_graph.py::test_graph_execution_with_retry_loop `
  --deselect tests/test_graph.py::test_graph_sqlite_state_persistence
```
**Cần xử lý triệt để** (đã báo Hoàng, đang chờ quyết định): mock thêm
`app.agents.analyst.agent.invoke_with_resilience` và tương ứng cho Writer trong `test_graph.py`.

### 3.7. Lỗi vặt khác gặp trong lúc setup (tham khảo, xem thêm `TESTING.md`)

- `ModuleNotFoundError: pydantic_core._pydantic_core` / `cygrpc` / `uuid_utils._uuid_utils` —
  do project đặt ở đường dẫn có dấu tiếng Việt/khoảng trắng, gây lỗi ngầm với compiled binary.
  → Đã chuyển project sang đường dẫn không dấu (`D:\code\DoAnTotNghiep\...`).
- `pip's dependency resolver` conflict giữa `langgraph==0.2.60` (cũ) và `langchain-core` 1.x mới
  → nâng `langgraph` lên `>=1.0`.
- Lệnh cmd (`rmdir /s /q`, `copy`, `type nul >`) không chạy được trên PowerShell — dùng
  `Remove-Item -Recurse -Force`, `Copy-Item`, `New-Item` thay thế.
- `ruff`/`mypy` chưa cài (không nằm trong `requirements.txt` chính) → cài riêng qua
  `requirements-dev.txt`.

---

## 4. Hướng dẫn chạy test đầy đủ (cho người sau)

### 4.1. Setup môi trường (xem chi tiết ở `docs/TESTING.md`)
```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
copy .env.example .env    # rồi điền GEMINI_API_KEY thật
```

### 4.2. Lint, format, type check
```powershell
ruff format app/
ruff check app/
mypy app/ --ignore-missing-imports
```

### 4.3. Chạy toàn bộ test (trừ 3 test end-to-end gọi LLM thật, tránh treo/tốn quota)
```powershell
pytest tests/ -v `
  --deselect tests/test_graph.py::test_graph_execution_single_pass_end_to_end `
  --deselect tests/test_graph.py::test_graph_execution_with_retry_loop `
  --deselect tests/test_graph.py::test_graph_sqlite_state_persistence
```
Kỳ vọng: 29/29 test pass.

### 4.4. Chạy riêng 3 test end-to-end (CHỈ khi cố ý muốn test thật với Gemini API)
```powershell
pytest tests/test_graph.py -v
```
⚠️ Sẽ gọi API Gemini thật (Analyst/Writer chưa được mock trong 3 test này) — tốn quota, có thể
chậm. Chỉ chạy khi cần kiểm tra pipeline end-to-end thật sự, không chạy thường xuyên.

### 4.5. Test nhanh 1 file cụ thể
```powershell
pytest tests/test_agents.py -v      # Analyst + Writer
pytest tests/test_factory.py -v     # LLM Factory (Dũng)
pytest tests/test_orchestrator.py -v
pytest tests/test_routing.py -v
pytest tests/test_state.py -v
```

---

## 5. Trạng thái hiện tại của nhánh `Backend-demo`

| Phần | Trạng thái |
|---|---|
| Schemas (`schemas/research.py`) | ✅ Merge xong, thống nhất |
| Analyst Agent | ✅ Code thật, đã test với LLM thật + unit test |
| Writer Agent | ✅ Code thật, đã test với LLM thật + unit test |
| Orchestrator / Graph / Routing / State (Hoàng) | ✅ Merge xong, 27/29 unit test pass |
| Researcher Agent (Cường) | ⏳ Chưa xong — có thể cần stub tạm để demo end-to-end |
| LLM Factory (Dũng) | ✅ Đã merge, `test_factory.py` pass — Analyst/Writer nên chuyển sang
  dùng `LLMFactory`/`invoke_with_resilience` thật thay vì bản `_get_temp_model`/`_invoke_temp` tạm |
| 3 test end-to-end trong `test_graph.py` | ⚠️ Cần Hoàng mock thêm Analyst/Writer, hiện đang lỗi/treo khi chạy |
| mypy lỗi ở `routing.py`, `factory.py` | ⚠️ Đã báo Hoàng/Dũng, chưa fix |

## 6. Việc cần làm tiếp theo

- [ ] Hoàng sửa 3 test end-to-end (mock Analyst/Writer)
- [ ] Hoàng/Dũng sửa 5 lỗi mypy ở `routing.py`, `factory.py`
- [ ] Hieu refactor Analyst/Writer dùng `LLMFactory` thật thay cho bản tạm
- [ ] Tạo stub Researcher (nếu Cường chưa xong kịp) để test pipeline đầu-cuối
- [ ] Sau khi ổn định trên `Backend-demo`, mở 1 PR duy nhất `Backend-demo → main`