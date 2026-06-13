import unittest

from src.agents.rag_agent import RAGAgent
from src.rag.metadata import extract_author_from_text


class FakeRAGTool:
    def search_notes(self, query: str, n_results: int = 5) -> list[dict]:
        return [
            {
                "text": (
                    "Apuntes Semana 6 Clase 1 Inteligencia Artificial\n"
                    "Roberto José Garita Mata\n"
                    "Escuela de Ingenieria en Computacion\n"
                ),
                "metadata": {
                    "source": "6_SEMANA_AI_20260324_1.pdf",
                    "author": "Roberto José Garita Mata",
                    "page": 1,
                    "week": 6,
                    "date": "2026-03-24",
                    "section": "",
                    "chunk_index": 0,
                },
                "distance": None,
            },
            {
                "text": (
                    "Se va a comenzar con las preguntas del Quiz 2. "
                    "I. QUIZ2 1) Describa que es overfitting y underfitting."
                ),
                "metadata": {
                    "source": "6_SEMANA_AI_20260324_1.pdf",
                    "author": "Roberto José Garita Mata",
                    "page": 1,
                    "week": 6,
                    "date": "2026-03-24",
                    "section": "I. QUIZ2",
                    "chunk_index": 1,
                },
                "distance": 0.1,
            },
            {
                "text": (
                    "Apuntes de Clase - Regresión Logística\n"
                    "David Blanco Láscarez\n"
                    "Escuela de Ingeniería en Computación\n"
                    "I. RESPUESTASQUIZ2"
                ),
                "metadata": {
                    "source": "6_SEMANA_AI_20260324_2.pdf",
                    "author": "David Blanco Láscarez",
                    "page": 1,
                    "week": 6,
                    "date": "2026-03-24",
                    "section": "I. RESPUESTASQUIZ2",
                    "chunk_index": 0,
                },
                "distance": None,
            },
        ]


class RagAuthorLookupTests(unittest.TestCase):
    def test_rejects_locations_and_sections_as_author(self):
        self.assertIsNone(extract_author_from_text("Cartago, Costa Rica"))
        self.assertIsNone(extract_author_from_text("I-A. Overfitting y underfitting"))

    def test_answers_quien_hizo_apunte_quiz_2_with_multiple_documents(self):
        agent = RAGAgent.__new__(RAGAgent)
        agent.rag_tool = FakeRAGTool()
        agent.llm = None

        result = agent.answer("¿Quién hizo el apunte del quiz 2?")

        self.assertIn("varios documentos relacionados con Quiz 2", result["answer"])
        self.assertIn("Roberto José Garita Mata", result["answer"])
        self.assertIn("6_SEMANA_AI_20260324_1.pdf", result["answer"])
        self.assertIn("David Blanco Láscarez", result["answer"])
        self.assertIn("6_SEMANA_AI_20260324_2.pdf", result["answer"])

    def test_context_includes_critical_metadata(self):
        agent = RAGAgent.__new__(RAGAgent)
        context = agent._format_context(FakeRAGTool().search_notes("quiz 2"))

        self.assertIn("Autor: Roberto José Garita Mata", context)
        self.assertIn("Archivo: 6_SEMANA_AI_20260324_1.pdf", context)
        self.assertIn("Pagina: 1", context)
        self.assertIn("Fecha: 2026-03-24", context)
        self.assertIn("Semana: 6", context)


if __name__ == "__main__":
    unittest.main()
