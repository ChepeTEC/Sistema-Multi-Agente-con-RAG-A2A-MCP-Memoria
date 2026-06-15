import unittest

from src.agents.summarizer_agent import SummarizerAgent


class FakeSummaryLLM:
    def __init__(self):
        self.calls = []

    def generate(self, prompt: str, instructions: str | None = None) -> dict:
        self.calls.append({
            "prompt": prompt,
            "instructions": instructions,
        })
        return {
            "text": "Resumen generado.",
            "provider": "gemini",
            "model": "gemini-summary-test",
            "response_id": "summary-response",
            "duration_ms": 4.2,
        }


class SummarizerAgentTests(unittest.TestCase):
    def test_returns_controlled_message_without_history(self):
        llm_client = FakeSummaryLLM()
        agent = SummarizerAgent(llm_client=llm_client)

        result = agent.answer("Resume lo que hemos hablado.")

        self.assertEqual(result["agent"], "SummarizerAgent")
        self.assertIn("no hay suficiente historial", result["answer"])
        self.assertEqual(result["sources"], [])
        self.assertFalse(result["trace"]["has_conversation_context"])
        self.assertEqual(llm_client.calls, [])

    def test_generates_summary_from_conversation_context(self):
        llm_client = FakeSummaryLLM()
        agent = SummarizerAgent(llm_client=llm_client)
        context = (
            "[Turno 1 | Agente: rag]\n"
            "Usuario: Que es RAG?\n"
            "Asistente: RAG combina recuperacion y generacion."
        )

        result = agent.answer(
            question="Resume esta sesion.",
            conversation_context=context,
        )

        self.assertEqual(result["answer"], "Resumen generado.")
        self.assertTrue(result["trace"]["has_conversation_context"])
        self.assertEqual(result["trace"]["turns_used"], 1)
        self.assertEqual(result["trace"]["llm"]["model"], "gemini-summary-test")
        self.assertIn("Historial reciente", llm_client.calls[0]["prompt"])
        self.assertIn("Resume esta sesion.", llm_client.calls[0]["prompt"])
        self.assertIn("exclusivamente", llm_client.calls[0]["instructions"])

    def test_rejects_empty_question(self):
        agent = SummarizerAgent(llm_client=FakeSummaryLLM())

        with self.assertRaisesRegex(ValueError, "pregunta"):
            agent.answer(" ")


if __name__ == "__main__":
    unittest.main()
