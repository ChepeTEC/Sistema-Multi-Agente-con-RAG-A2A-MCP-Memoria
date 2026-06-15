import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.server import app


class FakeOrchestrator:
    def __init__(self):
        self.calls = []

    def answer(self, question: str, session_id: str | None = None) -> dict:
        self.calls.append({"question": question, "session_id": session_id})
        return {
            "agent_selected": "rag",
            "decision_reason": "Prueba de endpoint.",
            "answer": f"Respuesta para: {question}",
            "sources": [],
            "trace": {
                "question": question,
                "session_id": session_id or "default",
                "decision_model": "gemini-test",
                "total_duration_ms": 1.0,
            },
        }


class FailingOrchestrator:
    def answer(self, question: str, session_id: str | None = None) -> dict:
        raise RuntimeError(
            "No se pudo cargar el modelo de embeddings "
            "'sentence-transformers/all-MiniLM-L6-v2'."
        )


class ApiServerTests(unittest.TestCase):
    def test_chat_endpoint_delegates_to_orchestrator(self):
        client = TestClient(app)
        fake_orchestrator = FakeOrchestrator()

        with patch("src.api.server.get_orchestrator", return_value=fake_orchestrator):
            response = client.post(
                "/api/chat",
                json={"question": "Que es IA?", "session_id": "frontend-session"},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["agent_selected"], "rag")
        self.assertEqual(data["answer"], "Respuesta para: Que es IA?")
        self.assertEqual(data["trace"]["session_id"], "frontend-session")
        self.assertEqual(data["trace"]["decision_model"], "gemini-test")
        self.assertEqual(
            fake_orchestrator.calls,
            [{"question": "Que es IA?", "session_id": "frontend-session"}],
        )

    def test_chat_endpoint_keeps_default_session_when_missing(self):
        client = TestClient(app)
        fake_orchestrator = FakeOrchestrator()

        with patch("src.api.server.get_orchestrator", return_value=fake_orchestrator):
            response = client.post(
                "/api/chat",
                json={"question": "Que es IA?"},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["trace"]["session_id"], "default")
        self.assertEqual(
            fake_orchestrator.calls,
            [{"question": "Que es IA?", "session_id": None}],
        )

    def test_chat_endpoint_returns_controlled_json_error(self):
        client = TestClient(app)

        with patch("src.api.server.get_orchestrator", return_value=FailingOrchestrator()):
            response = client.post(
                "/api/chat",
                json={"question": "Que es una funcion de activacion?"},
            )

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertTrue(data["error"])
        self.assertEqual(data["component"], "rag_embeddings")
        self.assertIn("modelo de embeddings", data["message"])
        self.assertIn("sentence-transformers/all-MiniLM-L6-v2", data["detail"])


if __name__ == "__main__":
    unittest.main()
