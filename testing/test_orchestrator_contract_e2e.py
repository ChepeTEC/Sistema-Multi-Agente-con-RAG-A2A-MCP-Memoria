from pathlib import Path
from uuid import uuid4
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.agents.orchestrator_agent import OrchestratorAgent
from src.api.server import app
from src.memory.conversational_memory import ConversationalMemory
from src.memory.historical_memory import HistoricalMemory
from src.tools.historical_memory_tool import HistoricalMemoryTool
from src.tools.memory_tool import MemoryTool


class FakeDecisionLLM:
    def __init__(self):
        self.calls = []

    def generate(self, prompt: str, instructions: str | None = None) -> dict:
        self.calls.append({"prompt": prompt, "instructions": instructions})
        return {
            "text": "rag",
            "provider": "gemini",
            "model": "gemini-e2e-test",
            "response_id": f"decision-{len(self.calls)}",
            "duration_ms": 2.0,
        }


class FakeRAGAgent:
    def __init__(self):
        self.calls = []

    def answer(self, question: str, conversation_context: str | None = None) -> dict:
        self.calls.append({
            "question": question,
            "conversation_context": conversation_context,
        })
        return {
            "agent": "RAGAgent",
            "answer": "RAG respondio usando apuntes del curso.",
            "sources": [{"file": "apuntes.pdf", "page": 1, "section": "RAG"}],
            "chunks": [],
            "trace": {"mode": "e2e"},
        }


class FakeSummarizerAgent:
    def __init__(self):
        self.calls = []

    def answer(self, question: str, conversation_context: str | None = None) -> dict:
        self.calls.append({
            "question": question,
            "conversation_context": conversation_context,
        })
        return {
            "agent": "SummarizerAgent",
            "answer": "Resumen de la sesion generado desde memoria.",
            "sources": [],
            "trace": {
                "has_conversation_context": bool(conversation_context),
                "turns_used": conversation_context.count("[Turno ") if conversation_context else 0,
            },
        }


def _historical_memory_tool() -> HistoricalMemoryTool:
    base_dir = Path("historical-memory-runtime-tests")
    base_dir.mkdir(exist_ok=True)
    db_path = base_dir / f"orchestrator-e2e-{uuid4().hex}.sqlite3"
    return HistoricalMemoryTool(memory=HistoricalMemory(db_path=db_path))


class OrchestratorContractAndE2ETests(unittest.TestCase):
    def test_orchestrator_contract_declares_inputs_outputs_agents_and_restrictions(self):
        contract = OrchestratorAgent.get_contract()

        self.assertEqual(contract["agent_name"], "OrchestratorAgent")
        self.assertEqual(contract["allowed_agents"], ["rag", "summary", "transactional", "web"])
        self.assertIn("question", contract["inputs"])
        self.assertIn("session_id", contract["inputs"])
        self.assertIn("agent_selected", contract["outputs"])
        self.assertIn("answer", contract["outputs"])
        self.assertIn("trace", contract["outputs"])
        self.assertTrue(any("preferir RAG" in item for item in contract["restrictions"]))
        self.assertGreaterEqual(len(contract["example_calls"]), 4)

        contract["allowed_agents"].append("mutated")
        self.assertNotIn("mutated", OrchestratorAgent.get_contract()["allowed_agents"])

    def test_api_chat_runs_end_to_end_through_orchestrator_and_session_memory(self):
        rag_agent = FakeRAGAgent()
        summarizer_agent = FakeSummarizerAgent()
        orchestrator = OrchestratorAgent(
            rag_agent=rag_agent,
            summarizer_agent=summarizer_agent,
            llm_client=FakeDecisionLLM(),
            memory_tool=MemoryTool(memory=ConversationalMemory()),
            historical_memory_tool=_historical_memory_tool(),
        )
        client = TestClient(app)

        with patch("src.api.server.get_orchestrator", return_value=orchestrator):
            first_response = client.post(
                "/api/chat",
                json={"question": "Que es RAG?", "session_id": "e2e-session"},
            )
            second_response = client.post(
                "/api/chat",
                json={"question": "Resume esta sesion.", "session_id": "e2e-session"},
            )

        self.assertEqual(first_response.status_code, 200)
        first_data = first_response.json()
        self.assertEqual(first_data["agent_selected"], "rag")
        self.assertEqual(first_data["trace"]["session_id"], "e2e-session")
        self.assertEqual(first_data["answer"], "RAG respondio usando apuntes del curso.")

        self.assertEqual(second_response.status_code, 200)
        second_data = second_response.json()
        self.assertEqual(second_data["agent_selected"], "summary")
        self.assertEqual(second_data["trace"]["delegated_agent"], "SummarizerAgent")
        self.assertEqual(second_data["trace"]["memory"]["turns_used"], 1)
        self.assertIn("Que es RAG?", summarizer_agent.calls[0]["conversation_context"])
        self.assertIn("RAG respondio usando apuntes", summarizer_agent.calls[0]["conversation_context"])


if __name__ == "__main__":
    unittest.main()