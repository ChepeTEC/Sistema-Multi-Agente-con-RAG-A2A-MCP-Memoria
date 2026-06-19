from pathlib import Path
from uuid import uuid4

from src.memory.historical_memory import HistoricalMemory
from src.tools.historical_memory_tool import HistoricalMemoryTool


def _test_db_path() -> Path:
    base_dir = Path("historical-memory-runtime-tests")
    base_dir.mkdir(exist_ok=True)
    return base_dir / f"history-test-{uuid4().hex}.sqlite3"


def test_historical_memory_persists_and_searches_across_reopen():
    db_path = _test_db_path()
    tool = HistoricalMemoryTool(memory=HistoricalMemory(db_path=db_path))

    saved = tool.save_turn(
        session_id="session-a",
        question="Qué es una CNN?",
        answer="Una CNN usa convoluciones para procesar imagenes.",
        agent_selected="rag",
        sources=[{"file": "cnn.pdf"}],
    )

    reopened = HistoricalMemoryTool(memory=HistoricalMemory(db_path=db_path))
    context = reopened.search_context("que pregunte anteriormente sobre cnn")

    assert saved["id"] == 1
    assert context["matches_count"] == 1
    assert "Qué es una CNN?" in context["formatted_context"]
    assert context["turns"][0]["agent_selected"] == "rag"


def test_historical_memory_filters_by_session():
    tool = HistoricalMemoryTool(memory=HistoricalMemory(db_path=_test_db_path()))
    tool.save_turn(
        session_id="session-a",
        question="Qué es pooling?",
        answer="Pooling reduce la dimension espacial.",
        agent_selected="rag",
    )
    tool.save_turn(
        session_id="session-b",
        question="Qué es fraude transaccional?",
        answer="Es actividad sospechosa en transacciones.",
        agent_selected="transactional",
    )

    session_context = tool.search_context(
        "fraude transaccional",
        session_id="session-b",
    )
    other_session_context = tool.search_context(
        "fraude transaccional",
        session_id="session-a",
    )

    assert session_context["matches_count"] == 1
    assert "fraude transaccional" in session_context["formatted_context"]
    assert other_session_context["matches_count"] == 0


def test_historical_memory_summary_roundtrip():
    tool = HistoricalMemoryTool(memory=HistoricalMemory(db_path=_test_db_path()))

    saved = tool.save_summary("session-a", "Se hablaron temas de CNN y pooling.")
    loaded = tool.get_summary("session-a")

    assert saved["summary_chars"] > 0
    assert loaded is not None
    assert loaded["summary"] == "Se hablaron temas de CNN y pooling."
