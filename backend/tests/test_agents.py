import pytest
from app.schemas.research import AnalystOutput, Finding, WriterOutput, Citation


# --- Test schema validation ---
def test_analyst_output_valid_confidence_range():
    output = AnalystOutput(
        status="complete",
        confidence_score=0.9,
        verified_findings=[],
        conclusions=["test"],
        insights=[],
    )
    assert 0.0 <= output.confidence_score <= 1.0


def test_analyst_output_rejects_invalid_confidence():
    with pytest.raises(ValueError):
        AnalystOutput(
            status="complete",
            confidence_score=1.5,
            verified_findings=[],
            conclusions=[],
            insights=[],
        )


# --- Test run_analyst với mock LLM (không gọi API thật) ---
@pytest.mark.asyncio
async def test_run_analyst_detects_conflict(mocker):
    from app.agents.analyst.agent import run_analyst

    mock_result = AnalystOutput(
        status="needs_more_research",
        confidence_score=0.6,
        verified_findings=[],
        conclusions=[],
        insights=[],
        conflicts=["Tăng trưởng GDP: Nguồn A 6.5%, Nguồn B 4.2%"],
    )

    # Mock CẢ bước tạo model lẫn bước gọi model
    mocker.patch("app.agents.analyst.agent._get_temp_model", return_value=None)
    mocker.patch(
        "app.agents.analyst.agent._invoke_temp",
        return_value=mock_result,
    )

    state = {
        "findings": [
            {"claim": "GDP tăng 6.5%", "evidence": "...", "source_url": "https://a.com", "source_title": "A"},
            {"claim": "GDP tăng 4.2%", "evidence": "...", "source_url": "https://b.com", "source_title": "B"},
        ]
    }
    result = await run_analyst(state)

    assert result["analysis"]["status"] == "needs_more_research"
    assert len(result["analysis"]["conflicts"]) > 0

def test_run_analyst_empty_findings_returns_fallback():
    from app.agents.analyst.agent import run_analyst
    import asyncio

    result = asyncio.run(run_analyst({"findings": []}))
    assert result["analysis"]["status"] == "needs_more_research"
    assert result["analysis"]["confidence_score"] == 0.0


# --- Test writer: warning block chèn đúng khi có conflict ---
def test_apply_warning_block_inserts_warning():
    from app.agents.writer.agent import _apply_warning_block

    analysis = {
        "status": "needs_more_research",
        "conflicts": ["Mâu thuẫn số liệu X"],
        "limitations": ["Thiếu nguồn kiểm chứng"],
    }
    content, warnings = _apply_warning_block("Nội dung báo cáo gốc", analysis)

    assert "⚠️ Cảnh báo" in content
    assert "Mâu thuẫn số liệu X" in content
    assert len(warnings) == 2


def test_apply_warning_block_skips_when_complete():
    from app.agents.writer.agent import _apply_warning_block

    analysis = {"status": "complete", "conflicts": []}
    content, warnings = _apply_warning_block("Nội dung gốc", analysis)

    assert "⚠️ Cảnh báo" not in content
    assert warnings == []


def test_build_citations_dedupes_by_url():
    from app.agents.writer.agent import _build_citations

    findings = [
        Finding(claim="A", evidence="e1", source_url="https://x.com", source_title="X"),
        Finding(claim="B", evidence="e2", source_url="https://x.com", source_title="X"),
        Finding(claim="C", evidence="e3", source_url="https://y.com", source_title="Y"),
    ]
    citations = _build_citations(findings)

    assert len(citations) == 2  # dedupe theo source_url
    assert citations[0].id == 1
    assert citations[1].id == 2