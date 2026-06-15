import unittest

from src.llm.gemini_client import GeminiClient


class FakeModels:
    def generate_content(self, **kwargs):
        self.kwargs = kwargs

        class Response:
            text = "Respuesta de prueba."
            response_id = "gemini-test-response"

        return Response()


class FakeGenaiClient:
    def __init__(self):
        self.models = FakeModels()


class GeminiClientTests(unittest.TestCase):
    def test_generate_uses_injected_client_without_real_api_call(self):
        fake_client = FakeGenaiClient()
        client = GeminiClient(
            model="gemini-test",
            api_key="test-key",
            client=fake_client,
        )

        result = client.generate(
            prompt="Explica IA.",
            instructions="Responde breve.",
        )

        self.assertEqual(result["text"], "Respuesta de prueba.")
        self.assertEqual(result["provider"], "gemini")
        self.assertEqual(result["model"], "gemini-test")
        self.assertEqual(result["response_id"], "gemini-test-response")
        self.assertEqual(fake_client.models.kwargs["model"], "gemini-test")

    def test_rejects_empty_prompt(self):
        client = GeminiClient(
            model="gemini-test",
            api_key="test-key",
            client=FakeGenaiClient(),
        )

        with self.assertRaisesRegex(ValueError, "prompt"):
            client.generate(" ")


if __name__ == "__main__":
    unittest.main()
