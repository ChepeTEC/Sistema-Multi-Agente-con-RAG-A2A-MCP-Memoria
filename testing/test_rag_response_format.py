import unittest

from src.agents.rag_agent import RAGAgent
from src.tools.rag_tool import RAGTool


class FakeRAGTool:
    def search_notes(self, query: str, n_results: int = 5) -> list[dict]:
        return [
            {
                "text": "RAG combina recuperacion de documentos con generacion.",
                "metadata": {
                    "source": "13_SEMANA_AI_20260521_1.pdf",
                    "author": "Apuntes del curso",
                    "date": "2026-05-21",
                    "week": 13,
                    "topic": "RAG",
                    "section": "Arquitectura RAG",
                    "page": 4,
                    "version": "1",
                },
                "distance": 0.75,
                "score": 3.25,
            }
        ]


class FakeLLM:
    def __init__(self, text: str):
        self.text = text
        self.prompts = []

    def generate(self, prompt: str) -> dict:
        self.prompts.append(prompt)
        return {"text": self.text}


class RagResponseFormatTests(unittest.TestCase):
    def test_answer_does_not_append_sources_section(self):
        agent = RAGAgent.__new__(RAGAgent)
        agent.rag_tool = FakeRAGTool()
        agent.llm = FakeLLM(
            "RAG reduce alucinaciones al usar evidencia recuperada [Fuente 1]."
        )

        result = agent.answer("Que es RAG?")

        self.assertEqual(
            result["answer"],
            "RAG reduce alucinaciones al usar evidencia recuperada [Fuente 1].",
        )
        self.assertNotIn("Fuentes consultadas", result["answer"])
        self.assertEqual(len(result["sources"]), 1)
        self.assertEqual(result["sources"][0]["score"], 3.25)

    def test_unique_sources_preserve_retrieval_scores(self):
        agent = RAGAgent.__new__(RAGAgent)
        chunks = FakeRAGTool().search_notes("rag")
        chunks.append({
            "text": "Otro fragmento sobre embeddings.",
            "metadata": {
                "source": "13_SEMANA_AI_20260521_2.pdf",
                "author": "Apuntes del curso",
                "date": "2026-05-21",
                "week": 13,
                "topic": "RAG",
                "section": "Embeddings",
                "page": 2,
                "version": "1",
            },
            "distance": None,
            "score": 1.75,
        })

        sources = agent._build_unique_sources(chunks)

        self.assertEqual(sources[0]["score"], 3.25)
        self.assertEqual(sources[1]["score"], 1.75)

    def test_removes_llm_sources_consultadas_section(self):
        agent = RAGAgent.__new__(RAGAgent)
        agent.rag_tool = FakeRAGTool()
        agent.llm = FakeLLM(
            "RAG usa recuperacion [Fuente 1].\n\n"
            "Fuentes consultadas:\n"
            "1. documento.pdf"
        )

        result = agent.answer("Que es RAG?")

        self.assertEqual(result["answer"], "RAG usa recuperacion [Fuente 1].")

    def test_context_uses_source_labels_for_inline_citations(self):
        agent = RAGAgent.__new__(RAGAgent)
        context = agent._format_context(FakeRAGTool().search_notes("rag"))

        self.assertIn("[Fuente 1", context)
        self.assertNotIn("[Fragmento 1", context)
        self.assertNotIn("[Fuente 1 |", context)

    def test_context_reuses_source_number_for_duplicate_source_cards(self):
        agent = RAGAgent.__new__(RAGAgent)
        chunks = FakeRAGTool().search_notes("rag")
        duplicate = chunks[0].copy()
        duplicate["text"] = "Otro texto del mismo archivo, pagina y seccion."

        context = agent._format_context([chunks[0], duplicate])

        self.assertEqual(context.count("[Fuente 1]"), 2)
        self.assertNotIn("[Fuente 2]", context)

    def test_prompt_requires_short_source_citations_only(self):
        agent = RAGAgent.__new__(RAGAgent)
        prompt = agent._build_prompt(
            question="Que es RAG?",
            chunks=FakeRAGTool().search_notes("rag"),
        )

        self.assertIn("cita solo el numero de fuente", prompt)
        self.assertIn("[Fuente N]", prompt)
        self.assertIn("no incluyas Archivo, Pagina", prompt)

    def test_retrieval_query_ignores_memory_for_new_explicit_topic(self):
        agent = RAGAgent.__new__(RAGAgent)
        context = (
            "[Turno 1 | Agente: rag]\n"
            "Usuario: Que es RAG?\n"
            "Asistente: RAG usa embeddings y recuperacion."
        )

        query = agent._build_retrieval_query(
            question="Que es backpropagation segun el curso?",
            conversation_context=context,
        )

        self.assertEqual(query, "Que es backpropagation segun el curso?")

    def test_retrieval_query_uses_recent_user_questions_for_follow_up(self):
        agent = RAGAgent.__new__(RAGAgent)
        context = (
            "[Turno 1 | Agente: rag]\n"
            "Usuario: Que es RAG?\n"
            "Asistente: RAG usa embeddings.\n\n"
            "[Turno 2 | Agente: rag]\n"
            "Usuario: Que es backpropagation?\n"
            "Asistente: Backpropagation ajusta pesos."
        )

        query = agent._build_retrieval_query(
            question="Como se relaciona eso con el descenso del gradiente?",
            conversation_context=context,
        )

        self.assertIn("Que es backpropagation?", query)
        self.assertIn("Como se relaciona eso", query)
        self.assertNotIn("RAG usa embeddings", query)
        self.assertNotIn("Backpropagation ajusta pesos", query)

    def test_rag_tool_returns_real_internal_scores(self):
        tool = RAGTool.__new__(RAGTool)
        chunks = [
            {
                "text": "RAG usa embeddings y recuperacion semantica para responder.",
                "metadata": {
                    "source": "a.pdf",
                    "page": 1,
                    "section": "RAG",
                    "topic": "RAG",
                    "week": 13,
                },
                "distance": 0.5,
            },
            {
                "text": "Texto corto.",
                "metadata": {
                    "source": "b.pdf",
                    "page": 1,
                    "section": "Otros",
                    "topic": "Otros",
                    "week": 1,
                },
                "distance": 2.0,
            },
        ]
        tool.embedding_model = type(
            "FakeEmbeddingModel",
            (),
            {"embed_query": lambda self, query: [0.1]},
        )()
        tool.vector_store = type(
            "FakeVectorStore",
            (),
            {"get_all_chunks": lambda self: chunks},
        )()
        tool._semantic_search = lambda query_embedding, n_results: []

        results = tool.search_notes("Que es RAG?", n_results=2)

        self.assertIn("score", results[0])
        self.assertEqual(
            results[0]["score"],
            round(tool._score_chunk(results[0], tool._build_query_plan("Que es RAG?", 2)), 4),
        )


if __name__ == "__main__":
    unittest.main()
