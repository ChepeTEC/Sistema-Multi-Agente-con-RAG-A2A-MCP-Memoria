import unittest
from unittest.mock import patch

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

class FakeLangfuseTracer:
    def __init__(self):
        self.calls = []
        self.trace = {"observation": object(), "closed": False}

    def create_trace(self, **kwargs):
        self.calls.append(("create_trace", kwargs))
        return self.trace

    def create_span(self, **kwargs):
        self.calls.append(("create_span", kwargs))
        return object()

    def create_generation(self, **kwargs):
        self.calls.append(("create_generation", kwargs))
        return object()

    def update_trace_output(self, trace, output_data):
        self.calls.append(("update_trace_output", {"trace": trace, "output_data": output_data}))

    def close_trace(self, trace):
        self.calls.append(("close_trace", {"trace": trace}))

    def flush(self):
        self.calls.append(("flush", {}))


class FailingWebSearchTool:
    def search(self, **kwargs):
        raise RuntimeError("web search unavailable")

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

    def test_search_query_does_not_include_conversation_history(self):
        tool = FakeWebSearchTool()
        llm_client = FakeLLMClient()
        agent = WebSearchAgent(
            web_search_tool=tool,
            llm_client=llm_client,
        )
        long_context = "[Turno 1]\n" + ("historial conversacional " * 80)

        agent.answer(
            question="Costa Rica va a jugar en el mundial de futbol del 2026?",
            justification="El usuario solicito informacion reciente.",
            conversation_context=long_context,
        )

        self.assertEqual(
            tool.kwargs["query"],
            "Costa Rica va a jugar en el mundial de futbol del 2026?",
        )
        self.assertNotIn("historial conversacional", tool.kwargs["query"])
        self.assertLessEqual(len(tool.kwargs["query"]), agent.MAX_SEARCH_QUERY_CHARS)
        self.assertIn("historial conversacional", llm_client.kwargs["prompt"])

    def test_search_query_is_truncated_to_tool_limit(self):
        tool = FakeWebSearchTool()
        agent = WebSearchAgent(
            web_search_tool=tool,
            llm_client=FakeLLMClient(),
        )
        long_question = " ".join(["consulta"] * 100)

        agent.answer(
            question=long_question,
            justification="El usuario solicito informacion reciente.",
        )

        self.assertLessEqual(len(tool.kwargs["query"]), agent.MAX_SEARCH_QUERY_CHARS)
        self.assertTrue(tool.kwargs["query"].startswith("consulta consulta"))

    def test_records_langfuse_trace_span_generation_and_output(self):
        tracer = FakeLangfuseTracer()
        agent = WebSearchAgent(
            web_search_tool=FakeWebSearchTool(),
            llm_client=FakeLLMClient(),
        )

        with patch("src.agents.web_search_agent.langfuse_tracer", tracer):
            result = agent.answer(
                question="Busca informacion reciente",
                justification="El usuario solicito una busqueda web justificada.",
            )

        call_names = [name for name, _ in tracer.calls]
        self.assertIn("create_trace", call_names)
        self.assertIn("create_span", call_names)
        self.assertIn("create_generation", call_names)
        self.assertIn("update_trace_output", call_names)
        self.assertIn("close_trace", call_names)
        self.assertIn("flush", call_names)

        search_span = next(
            kwargs for name, kwargs in tracer.calls
            if name == "create_span" and kwargs["name"] == "web_search_tool_call"
        )
        self.assertEqual(search_span["output_data"]["results_count"], 1)
        self.assertEqual(search_span["metadata"]["urls"], ["https://example.com/article"])

        generation = next(kwargs for name, kwargs in tracer.calls if name == "create_generation")
        self.assertEqual(generation["name"], "web_search_generation")
        self.assertEqual(generation["model"], "test-model")
        self.assertIn("Fuente 1", generation["prompt"])
        self.assertEqual(generation["response"], result["answer"])

    def test_records_langfuse_error_span_when_search_fails(self):
        tracer = FakeLangfuseTracer()
        agent = WebSearchAgent(
            web_search_tool=FailingWebSearchTool(),
            llm_client=FakeLLMClient(),
        )

        with patch("src.agents.web_search_agent.langfuse_tracer", tracer):
            with self.assertRaisesRegex(RuntimeError, "web search unavailable"):
                agent.answer(
                    question="Busca informacion reciente",
                    justification="El usuario solicito una busqueda web justificada.",
                )

        error_span = next(
            kwargs for name, kwargs in tracer.calls
            if name == "create_span" and kwargs["name"] == "web_search_agent_error"
        )
        self.assertIn("web search unavailable", error_span["output_data"]["error"])
        self.assertIn("close_trace", [name for name, _ in tracer.calls])
        self.assertIn("flush", [name for name, _ in tracer.calls])

if __name__ == "__main__":
    unittest.main()
