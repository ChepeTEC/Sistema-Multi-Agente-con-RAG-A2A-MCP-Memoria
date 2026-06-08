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


def exploding_rag_factory():
    raise RuntimeError("RAG no debio instanciarse")


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

    def test_web_route_does_not_instantiate_rag(self):
        web_agent = FakeWebSearchAgent()
        orchestrator = OrchestratorAgent(
            web_search_agent=web_agent,
            rag_agent_factory=exploding_rag_factory,
            llm_client=FakeDecisionLLM("web"),
        )

        result = orchestrator.answer("Cuales son las noticias recientes de Gemini?")

        self.assertEqual(result["agent_selected"], "web")
        self.assertEqual(result["answer"], "Respuesta desde Web.")
        self.assertEqual(web_agent.calls[0]["question"], "Cuales son las noticias recientes de Gemini?")

    def test_can_route_to_web_even_if_rag_cannot_load(self):
        web_agent = FakeWebSearchAgent()
        orchestrator = OrchestratorAgent(
            web_search_agent=web_agent,
            rag_agent_factory=exploding_rag_factory,
            llm_client=FakeDecisionLLM("web"),
        )

        result = orchestrator.answer("Busca en internet informacion actual sobre Gemini API.")

        self.assertEqual(result["agent_selected"], "web")
        self.assertEqual(result["trace"]["delegated_agent"], "WebSearchAgent")

    def test_academic_questions_are_forced_to_rag_even_if_gemini_says_web(self):
        questions = [
            "Que es el descenso del gradiente?",
            "Que problema presenta la funcion ReLU y como lo resuelve Leaky ReLU?",
            "Que es una red neuronal artificial?",
            "Que es una funcion de activacion?",
            "Que es backpropagation?",
        ]

        for question in questions:
            with self.subTest(question=question):
                rag_agent = FakeRAGAgent()
                orchestrator = OrchestratorAgent(
                    rag_agent=rag_agent,
                    web_search_agent=FakeWebSearchAgent(),
                    llm_client=FakeDecisionLLM("web"),
                )

                result = orchestrator.answer(question)

                self.assertEqual(result["agent_selected"], "rag")
                self.assertEqual(rag_agent.questions, [question])

    def test_explicit_current_or_web_questions_are_forced_to_web(self):
        questions = [
            "Cuales son las noticias recientes sobre Google Gemini?",
            "Busca la documentacion oficial de Tavily.",
            "Que cambios recientes ha anunciado OpenAI?",
            "Busca en internet informacion actual sobre Gemini API.",
        ]

        for question in questions:
            with self.subTest(question=question):
                web_agent = FakeWebSearchAgent()
                orchestrator = OrchestratorAgent(
                    rag_agent=FakeRAGAgent(),
                    web_search_agent=web_agent,
                    llm_client=FakeDecisionLLM("rag"),
                )

                result = orchestrator.answer(question)

                self.assertEqual(result["agent_selected"], "web")
                self.assertEqual(web_agent.calls[0]["question"], question)

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
