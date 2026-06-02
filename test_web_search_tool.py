import unittest

from src.tools.web_search_tool import WebSearchTool


class FakeTavilyClient:
    def search(self, **kwargs):
        self.kwargs = kwargs
        return {
            "request_id": "test-request",
            "results": [
                {
                    "title": "Fuente de prueba",
                    "url": "https://example.com/article",
                    "content": "Contenido de prueba.",
                    "score": 0.91
                }
            ]
        }


class WebSearchToolTests(unittest.TestCase):
    def setUp(self):
        self.client = FakeTavilyClient()
        self.tool = WebSearchTool(client=self.client)

    def test_search_normalizes_results_and_preserves_justification(self):
        result = self.tool.search(
            query=" noticias de agentes ",
            justification=" El usuario solicito informacion reciente. ",
            max_results=3
        )

        self.assertEqual(result["query"], "noticias de agentes")
        self.assertEqual(
            result["justification"],
            "El usuario solicito informacion reciente."
        )
        self.assertEqual(result["provider"], "tavily")
        self.assertEqual(result["results"][0]["title"], "Fuente de prueba")
        self.assertEqual(self.client.kwargs["max_results"], 3)
        self.assertFalse(self.client.kwargs["include_answer"])

    def test_search_rejects_missing_justification(self):
        with self.assertRaisesRegex(ValueError, "justificacion"):
            self.tool.search(query="consulta", justification="")

    def test_search_rejects_invalid_max_results(self):
        with self.assertRaisesRegex(ValueError, "max_results"):
            self.tool.search(
                query="consulta",
                justification="prueba",
                max_results=11
            )


if __name__ == "__main__":
    unittest.main()
