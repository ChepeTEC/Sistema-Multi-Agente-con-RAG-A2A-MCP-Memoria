import json
from pathlib import Path
from uuid import uuid4

from src.agents.orchestrator_agent import OrchestratorAgent
from src.memory.conversational_memory import ConversationalMemory
from src.memory.historical_memory import HistoricalMemory
from src.tools.historical_memory_tool import HistoricalMemoryTool
from src.tools.memory_tool import MemoryTool


DATASET_PATH = Path(__file__).resolve().parents[1] / "evaluation" / "functional_questions.json"
REQUIRED_COUNTS = {
    "rag_factual": 10,
    "rag_comparison": 5,
    "follow_up_memory": 5,
    "out_of_scope": 5,
    "web_search": 5,
    "transactional_mcp": 5,
}


class EvaluationDecisionLLM:
    def generate(self, prompt: str, instructions: str | None = None) -> dict:
        return {
            "text": "rag",
            "provider": "test",
            "model": "evaluation-decision-model",
            "response_id": "evaluation-decision",
            "duration_ms": 1.0,
        }


class EvaluationRAGAgent:
    OUT_OF_SCOPE_SIGNALS = [
        "receta",
        "diagnostico",
        "loteria",
        "formula 1",
        "contrasena",
        "profesor",
        "nota promedio",
        "mejor nota",
        "comida",
        "tierra es plana",
    ]

    def __init__(self):
        self.calls = []

    def answer(self, question: str, conversation_context: str | None = None) -> dict:
        self.calls.append({
            "question": question,
            "conversation_context": conversation_context or "",
        })
        question_lower = question.lower()
        if any(signal in question_lower for signal in self.OUT_OF_SCOPE_SIGNALS):
            return {
                "agent": "RAGAgent",
                "answer": "No encontre informacion suficiente en los apuntes para responder sin inventar fuentes.",
                "sources": [],
                "chunks": [],
                "trace": {"tool": "RAGTool", "out_of_scope": True},
            }

        return {
            "agent": "RAGAgent",
            "answer": "Respuesta basada en apuntes del curso con evidencia recuperada.",
            "sources": [
                {
                    "file": "apuntes-evaluacion.pdf",
                    "author": "Estudiante Demo",
                    "page": 1,
                    "week": "evaluacion",
                    "section": "tema evaluado",
                }
            ],
            "chunks": [{"text": "fragmento recuperado", "metadata": {"source": "apuntes-evaluacion.pdf"}}],
            "trace": {"tool": "RAGTool", "out_of_scope": False},
        }


class EvaluationWebSearchAgent:
    def __init__(self):
        self.calls = []

    def answer(
        self,
        question: str,
        justification: str,
        conversation_context: str | None = None,
    ) -> dict:
        self.calls.append({
            "question": question,
            "justification": justification,
            "conversation_context": conversation_context or "",
        })
        return {
            "agent": "WebSearchAgent",
            "answer": "Respuesta basada en resultados web actuales. [Fuente 1]",
            "sources": [
                {
                    "title": "Fuente web de evaluacion",
                    "url": "https://example.com/evaluacion",
                    "score": 0.9,
                    "published_date": "2026-06-19",
                }
            ],
            "trace": {
                "query": question,
                "justification": justification,
                "urls": ["https://example.com/evaluacion"],
                "search": {"provider": "test-web", "duration_ms": 1.0},
                "llm": {"provider": "test", "model": "evaluation-web-model"},
            },
        }


class EvaluationSummarizerAgent:
    def __init__(self):
        self.calls = []

    def answer(self, question: str, conversation_context: str | None = None) -> dict:
        self.calls.append({
            "question": question,
            "conversation_context": conversation_context or "",
        })
        return {
            "agent": "SummarizerAgent",
            "answer": "Resumen generado usando la memoria disponible.",
            "sources": [],
            "trace": {
                "has_conversation_context": bool(conversation_context),
                "turns_used": (conversation_context or "").count("Usuario:"),
            },
        }


class EvaluationTransactionalAgent:
    def __init__(self):
        self.calls = []

    def answer(self, question: str, conversation_context: str | None = None) -> dict:
        tool_name = "create_fraud_case" if "crea un caso" in question.lower() else "search_transactions"
        if "patrones sospechosos" in question.lower():
            tool_name = "get_fraud_case_summary"
        if "riesgo del comercio" in question.lower():
            tool_name = "get_merchant_risk_score"

        self.calls.append({
            "question": question,
            "conversation_context": conversation_context or "",
            "tool_name": tool_name,
        })
        return {
            "agent": "TransactionalAgent",
            "answer": "Analisis transaccional realizado mediante MCP con datos ficticios anonimizados.",
            "sources": ["PostgreSQL Database via MCP"],
            "trace": {
                "access_path": "mcp",
                "mcp_tools": [
                    {
                        "name": tool_name,
                        "args": {"justificacion": "Evaluacion funcional con consulta acotada."},
                        "result_preview": "datos ficticios anonimizados",
                    }
                ],
            },
        }


def load_cases() -> list[dict]:
    return json.loads(DATASET_PATH.read_text(encoding="utf-8"))


def build_orchestrator(case_id: str):
    memory_tool = MemoryTool(memory=ConversationalMemory())
    runtime_dir = Path("historical-memory-runtime-tests")
    runtime_dir.mkdir(exist_ok=True)
    db_path = runtime_dir / f"functional-evaluation-{case_id}-{uuid4().hex}.sqlite3"
    historical_tool = HistoricalMemoryTool(
        memory=HistoricalMemory(db_path=db_path)
    )
    agents = {
        "rag": EvaluationRAGAgent(),
        "web": EvaluationWebSearchAgent(),
        "summary": EvaluationSummarizerAgent(),
        "transactional": EvaluationTransactionalAgent(),
    }
    orchestrator = OrchestratorAgent(
        rag_agent=agents["rag"],
        summarizer_agent=agents["summary"],
        web_search_agent=agents["web"],
        transactional_agent=agents["transactional"],
        llm_client=EvaluationDecisionLLM(),
        memory_tool=memory_tool,
        historical_memory_tool=historical_tool,
    )
    return orchestrator, agents, memory_tool, historical_tool


def seed_case_memory(case: dict, memory_tool: MemoryTool, historical_tool: HistoricalMemoryTool) -> None:
    for turn in case.get("setup_turns", []):
        memory_tool.save_turn(
            session_id=case["session_id"],
            question=turn["question"],
            answer=turn["answer"],
            agent_selected=turn["agent_selected"],
        )

    for turn in case.get("setup_historical_turns", []):
        historical_tool.save_turn(
            session_id=turn["session_id"],
            question=turn["question"],
            answer=turn["answer"],
            agent_selected=turn["agent_selected"],
        )


def test_functional_evaluation_dataset_has_required_coverage():
    cases = load_cases()
    counts = {case_type: 0 for case_type in REQUIRED_COUNTS}
    ids = set()

    for case in cases:
        ids.add(case["id"])
        counts[case["type"]] = counts.get(case["type"], 0) + 1
        assert case["text"].strip()
        assert case["expected_agent"] in OrchestratorAgent.VALID_AGENTS
        assert case["success_criteria"]

    assert len(ids) == len(cases)
    for case_type, required_count in REQUIRED_COUNTS.items():
        assert counts[case_type] >= required_count


def test_functional_evaluation_questions_execute_against_orchestrator():
    cases = load_cases()

    for case in cases:
        orchestrator, agents, memory_tool, historical_tool = build_orchestrator(case["id"])
        seed_case_memory(case, memory_tool, historical_tool)

        result = orchestrator.answer(
            question=case["text"],
            session_id=case["session_id"],
        )

        assert result["agent_selected"] == case["expected_agent"], case["id"]
        assert result["answer"].strip(), case["id"]
        assert result["trace"]["delegated_agent"] == result["trace"].get("delegated_agent")

        if case["type"] in {"rag_factual", "rag_comparison"}:
            assert result["trace"]["delegated_agent"] == "RAGAgent", case["id"]
            assert result["sources"], case["id"]
            assert agents["web"].calls == [], case["id"]
            assert agents["transactional"].calls == [], case["id"]

        if case["type"] == "out_of_scope":
            assert result["trace"]["delegated_agent"] == "RAGAgent", case["id"]
            answer_lower = result["answer"].lower()
            assert "no encontre" in answer_lower or "no tengo" in answer_lower or "sin inventar" in answer_lower, case["id"]
            assert not result["sources"], case["id"]

        if case["type"] == "web_search":
            assert result["trace"]["delegated_agent"] == "WebSearchAgent", case["id"]
            assert result["sources"] and result["sources"][0].get("url"), case["id"]
            assert agents["web"].calls[-1]["justification"], case["id"]
            assert result["trace"]["delegated_trace"]["urls"], case["id"]

        if case["type"] == "transactional_mcp":
            assert result["trace"]["delegated_agent"] == "TransactionalAgent", case["id"]
            delegated_trace = result["trace"]["delegated_trace"]
            tool_names = [tool["name"] for tool in delegated_trace["mcp_tools"]]
            assert delegated_trace["access_path"] == "mcp", case["id"]
            assert "execute_sql" not in tool_names, case["id"]
            assert all("justificacion" in tool["args"] for tool in delegated_trace["mcp_tools"]), case["id"]
            assert any("MCP" in str(source) for source in result["sources"]), case["id"]

        if case["type"] == "follow_up_memory":
            if case["expected_tool"] == "MemoryTool":
                assert result["trace"]["memory"]["turns_used"] >= 1, case["id"]
                if case["expected_agent"] == "rag":
                    context = agents["rag"].calls[-1]["conversation_context"]
                    assert "Usuario:" in context and case["setup_turns"][0]["question"] in context, case["id"]
                if case["expected_agent"] == "summary":
                    context = agents["summary"].calls[-1]["conversation_context"]
                    assert "Usuario:" in context and case["setup_turns"][0]["question"] in context, case["id"]

            if case["expected_tool"] == "HistoricalMemoryTool":
                assert result["trace"]["historical_memory"]["queried"], case["id"]
                context = agents["summary"].calls[-1]["conversation_context"]
                expected_question = case["setup_historical_turns"][0]["question"]
                assert expected_question in context, case["id"]


def test_mcp_server_does_not_expose_free_sql_tool():
    from src.mcp import mcp_server

    assert not hasattr(mcp_server, "execute_sql")





