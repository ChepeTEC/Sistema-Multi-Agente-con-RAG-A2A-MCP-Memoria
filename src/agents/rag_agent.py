from src.tools.rag_tool import RAGTool


class RAGAgent:
    """
    Agente especializado en responder preguntas usando los apuntes del curso.

    Este agente usa RAGTool para recuperar fragmentos relevantes.
    Por ahora genera una respuesta extractiva simple, sin LLM externo.
    """

    def __init__(self):
        self.rag_tool = RAGTool()

    def answer(self, question: str, n_results: int = 5) -> dict:
        if not question or not question.strip():
            raise ValueError("La pregunta no puede estar vacía.")

        retrieved_chunks = self.rag_tool.search_notes(
            query=question,
            n_results=n_results
        )

        if not retrieved_chunks:
            return {
                "answer": "No encontré información relevante en los apuntes.",
                "sources": [],
                "chunks": []
            }

        context_parts = []
        sources = []

        for index, chunk in enumerate(retrieved_chunks, start=1):
            metadata = chunk["metadata"]

            source = {
                "file": metadata.get("source", "desconocido"),
                "page": metadata.get("page", "desconocida"),
                "distance": chunk.get("distance")
            }

            sources.append(source)

            context_parts.append(
                f"[Fuente {index}: {source['file']}, página {source['page']}]\n"
                f"{chunk['text']}"
            )

        answer = self._build_simple_answer(question, context_parts, sources)

        return {
            "answer": answer,
            "sources": sources,
            "chunks": retrieved_chunks
        }

    def _build_simple_answer(
        self,
        question: str,
        context_parts: list[str],
        sources: list[dict]
    ) -> str:
        """
        Construye una respuesta simple usando los fragmentos recuperados.
        Reemplazar esta parte por una llamada a un LLM!
        """

        main_context = context_parts[0]

        source_lines = []
        for index, source in enumerate(sources, start=1):
            source_lines.append(
                f"{index}. {source['file']} - página {source['page']}"
            )

        sources_text = "\n".join(source_lines)

        answer = (
            f"Pregunta: {question}\n\n"
            f"Según los apuntes recuperados, la información más relevante es:\n\n"
            f"{main_context[:1200]}\n\n"
            f"Fuentes consultadas:\n{sources_text}"
        )

        return answer