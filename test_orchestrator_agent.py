import unittest
from unittest.mock import patch

from src.agents.orchestrator_agent import OrchestratorAgent
from src.config.settings import settings


class FakeDecisionLLM:
    def __init__(self, decision: str):
        self.decision = decision
        self.calls = []

    def generate(self, prompt: str, instructions: str | None = None) -> dict:
        self.calls.append({
            "prompt": prompt,
            "instructions": instructions,
        })
        return {
            "text": self.decision,
            "provider": "gemini",
            "model": "gemini-test",
            "response_id": "decision-response",
            "duration_ms": 7.5,
        }


class FakeRAGAgent:
    def __init__(self):
        self.questions = []

    def answer(self, question: str) -> dict:
        self.questions.append(question)
        return {
            "agent": "RAGAgent",
            "answer": "Respuesta desde RAG.",
            "sources": [
                {
                    "file": "apuntes.pdf",
                    "page": 3,
                }
            ],
            "chunks": [],
        }


class FakeWebSearchAgent:
    def __init__(self):
        self.calls = []

    def answer(self, question: str, justification: str) -> dict:
        self.calls.append({
            "question": question,
            "justification": justification,
        })
        return {
            "agent": "WebSearchAgent",
            "answer": "Respuesta desde Web.",
            "sources": [
                {
                    "title": "Fuente web",
                    "url": "https://example.com",
                }
            ],
            "trace": {
                "query": question,
                "urls": ["https://example.com"],
            },
        }


class OrchestratorAgentTests(unittest.TestCase):
    def test_routes_to_rag_when_gemini_selects_rag(self):
        rag_agent = FakeRAGAgent()
        web_agent = FakeWebSearchAgent()
        llm_client = FakeDecisionLLM("rag")
        orchestrator = OrchestratorAgent(
            rag_agent=rag_agent,
            web_search_agent=web_agent,
            llm_client=llm_client,
        )

        result = orchestrator.answer("Que es overfitting segun los apuntes?")

        self.assertEqual(result["agent_selected"], "rag")
        self.assertEqual(result["answer"], "Respuesta desde RAG.")
        self.assertEqual(result["sources"][0]["file"], "apuntes.pdf")
        self.assertEqual(rag_agent.questions, ["Que es overfitting segun los apuntes?"])
        self.assertEqual(web_agent.calls, [])
        self.assertEqual(result["trace"]["decision_model"], "gemini-test")
        self.assertEqual(result["trace"]["decision_duration_ms"], 7.5)
        self.assertEqual(result["trace"]["delegated_agent"], "RAGAgent")
        self.assertIn("exclusivamente", llm_client.calls[0]["instructions"])

    def test_default_decision_client_uses_orchestrator_model(self):
        rag_agent = FakeRAGAgent()
        web_agent = FakeWebSearchAgent()
        llm_client = FakeDecisionLLM("rag")

        with patch(
            "src.agents.orchestrator_agent.GeminiClient",
            return_value=llm_client,
        ) as gemini_client:
            orchestrator = OrchestratorAgent(
                rag_agent=rag_agent,
                web_search_agent=web_agent,
            )

        orchestrator.answer("Que es aprendizaje supervisado?")

        gemini_client.assert_called_once_with(
            model=settings.ORCHESTRATOR_LLM_MODEL
        )
        self.assertEqual(rag_agent.questions, ["Que es aprendizaje supervisado?"])

    def test_routes_to_web_when_gemini_selects_web(self):
        rag_agent = FakeRAGAgent()
        web_agent = FakeWebSearchAgent()
        orchestrator = OrchestratorAgent(
            rag_agent=rag_agent,
            web_search_agent=web_agent,
            llm_client=FakeDecisionLLM("web"),
        )

        result = orchestrator.answer("Cuales son las noticias recientes de Gemini?")

        self.assertEqual(result["agent_selected"], "web")
        self.assertEqual(result["answer"], "Respuesta desde Web.")
        self.assertEqual(result["sources"][0]["url"], "https://example.com")
        self.assertEqual(rag_agent.questions, [])
        self.assertEqual(web_agent.calls[0]["question"], "Cuales son las noticias recientes de Gemini?")
        self.assertIn("internet", web_agent.calls[0]["justification"])
        self.assertEqual(result["trace"]["delegated_agent"], "WebSearchAgent")
        self.assertEqual(result["trace"]["delegated_trace"]["urls"], ["https://example.com"])

    def test_prefers_rag_when_gemini_returns_unexpected_output(self):
        rag_agent = FakeRAGAgent()
        orchestrator = OrchestratorAgent(
            rag_agent=rag_agent,
            web_search_agent=FakeWebSearchAgent(),
            llm_client=FakeDecisionLLM("no estoy seguro"),
        )

        result = orchestrator.answer("Explica aprendizaje supervisado.")

        self.assertEqual(result["agent_selected"], "rag")
        self.assertEqual(result["trace"]["raw_decision"], "no estoy seguro")
        self.assertEqual(rag_agent.questions, ["Explica aprendizaje supervisado."])

    def test_rejects_empty_question(self):
        orchestrator = OrchestratorAgent(
            rag_agent=FakeRAGAgent(),
            web_search_agent=FakeWebSearchAgent(),
            llm_client=FakeDecisionLLM("rag"),
        )

        with self.assertRaisesRegex(ValueError, "pregunta"):
            orchestrator.answer(" ")


if __name__ == "__main__":
    unittest.main()
