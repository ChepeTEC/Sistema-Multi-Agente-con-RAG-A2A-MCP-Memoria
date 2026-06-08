import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.server import app


class FakeOrchestrator:
    def answer(self, question: str) -> dict:
        return {
            "agent_selected": "rag",
            "decision_reason": "Prueba de endpoint.",
            "answer": f"Respuesta para: {question}",
            "sources": [],
            "trace": {
                "question": question,
                "decision_model": "gemini-test",
                "total_duration_ms": 1.0,
            },
        }


class FailingOrchestrator:
    def answer(self, question: str) -> dict:
        raise RuntimeError(
            "No se pudo cargar el modelo de embeddings "
            "'sentence-transformers/all-MiniLM-L6-v2'."
        )


class ApiServerTests(unittest.TestCase):
    def test_chat_endpoint_delegates_to_orchestrator(self):
        client = TestClient(app)

        with patch("src.api.server.get_orchestrator", return_value=FakeOrchestrator()):
            response = client.post(
                "/api/chat",
                json={"question": "Que es IA?"},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["agent_selected"], "rag")
        self.assertEqual(data["answer"], "Respuesta para: Que es IA?")
        self.assertEqual(data["trace"]["decision_model"], "gemini-test")

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
