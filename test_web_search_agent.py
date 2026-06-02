import unittest

from src.agents.web_search_agent import WebSearchAgent


class FakeWebSearchTool:
    def search(self, **kwargs):
        self.kwargs = kwargs
        return {
            "query": kwargs["query"],
            "justification": kwargs["justification"],
            "provider": "tavily",
            "request_id": "test-request",
            "results": [
                {
                    "title": "Fuente de prueba",
                    "url": "https://example.com/article",
                    "content": "Contenido de prueba.",
                    "score": 0.91,
                    "published_date": None
                }
            ],
            "duration_ms": 12.5
        }


class FakeLLMClient:
    def generate(self, **kwargs):
        self.kwargs = kwargs
        return {
            "text": "Respuesta redactada por el LLM. [Fuente 1]",
            "provider": "gemini",
            "model": "test-model",
            "response_id": "test-response",
            "duration_ms": 4.2
        }


class WebSearchAgentTests(unittest.TestCase):
    def test_answer_returns_sources_and_trace(self):
        tool = FakeWebSearchTool()
        llm_client = FakeLLMClient()
        agent = WebSearchAgent(
            web_search_tool=tool,
            llm_client=llm_client
        )

        result = agent.answer(
            question="Informacion reciente",
            justification="El usuario solicito buscar en internet."
        )

        self.assertEqual(result["agent"], "WebSearchAgent")
        self.assertEqual(
            result["answer"],
            "Respuesta redactada por el LLM. [Fuente 1]"
        )
        self.assertEqual(result["sources"][0]["url"], "https://example.com/article")
        self.assertEqual(result["trace"]["search"]["provider"], "tavily")
        self.assertEqual(result["trace"]["llm"]["provider"], "gemini")
        self.assertEqual(result["trace"]["llm"]["model"], "test-model")
        self.assertEqual(result["trace"]["urls"], ["https://example.com/article"])
        self.assertEqual(
            result["trace"]["justification"],
            "El usuario solicito buscar en internet."
        )
        self.assertIn("Fuente 1", llm_client.kwargs["prompt"])


if __name__ == "__main__":
    unittest.main()
