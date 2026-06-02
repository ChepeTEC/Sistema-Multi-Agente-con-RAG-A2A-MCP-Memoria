import unittest
from types import SimpleNamespace

from src.llm.gemini_client import GeminiClient


class FakeModels:
    def generate_content(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            response_id="test-response",
            text="Respuesta generada."
        )


class FakeGeminiSDKClient:
    def __init__(self):
        self.models = FakeModels()


class GeminiClientTests(unittest.TestCase):
    def test_generate_uses_configured_model(self):
        client = FakeGeminiSDKClient()
        llm_client = GeminiClient(model="test-model", client=client)

        result = llm_client.generate(
            prompt="Pregunta con fuentes.",
            instructions="Responda usando las fuentes."
        )

        self.assertEqual(result["text"], "Respuesta generada.")
        self.assertEqual(result["provider"], "gemini")
        self.assertEqual(result["model"], "test-model")
        self.assertEqual(client.models.kwargs["model"], "test-model")
        self.assertEqual(client.models.kwargs["contents"], "Pregunta con fuentes.")
        self.assertEqual(
            client.models.kwargs["config"].system_instruction,
            "Responda usando las fuentes."
        )

    def test_generate_rejects_empty_prompt(self):
        llm_client = GeminiClient(
            model="test-model",
            client=FakeGeminiSDKClient()
        )

        with self.assertRaisesRegex(ValueError, "prompt"):
            llm_client.generate(prompt="", instructions="Instrucciones.")

    def test_generate_allows_missing_instructions_for_rag(self):
        client = FakeGeminiSDKClient()
        llm_client = GeminiClient(model="test-model", client=client)

        result = llm_client.generate(prompt="Pregunta RAG.")

        self.assertEqual(result["text"], "Respuesta generada.")
        self.assertIsNone(
            client.models.kwargs["config"].system_instruction
        )


if __name__ == "__main__":
    unittest.main()
