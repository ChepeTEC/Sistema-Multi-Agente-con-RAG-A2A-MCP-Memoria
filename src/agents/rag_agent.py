from src.tools.rag_tool import RAGTool
from src.rag.preprocessors import clean_text
from src.llm.gemini_client import GeminiClient


class RAGAgent:
    """
    Agente especializado en responder preguntas usando los apuntes del curso.

    Recupera fragmentos relevantes con RAGTool y usa un LLM para generar
    una respuesta fundamentada únicamente en esos fragmentos.
    """

    def __init__(self):
        self.rag_tool = RAGTool()
        self.llm = GeminiClient()

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
                "chunks": [],
                "agent": "RAGAgent"
            }

        clean_chunks = self._clean_retrieved_chunks(retrieved_chunks)
        sources = self._build_unique_sources(clean_chunks)
        prompt = self._build_prompt(question, clean_chunks)
        generated_answer = self.llm.generate(prompt)
        generated_answer = self._remove_llm_sources(generated_answer)

        final_answer = (
            f"{generated_answer}\n\n"
            f"Fuentes consultadas:\n"
            f"{self._format_sources(sources)}"
        )

        return {
            "answer": final_answer,
            "sources": sources,
            "chunks": clean_chunks,
            "agent": "RAGAgent"
        }
    def _remove_llm_sources(self, answer: str) -> str:
        """
        Elimina secciones de fuentes que el LLM pueda agregar aunque el prompt
        le indique no hacerlo. Las fuentes oficiales se agregan después desde
        los metadatos recuperados por el sistema.
        """
        source_markers = [
            "\nFuentes:",
            "\n**Fuentes:**",
            "\nFuente:",
            "\n**Fuente:**",
            "\nReferencias:",
            "\n**Referencias:**",
            "\nCitas:",
            "\n**Citas:**",
        ]

        cleaned_answer = answer.strip()

        for marker in source_markers:
            position = cleaned_answer.find(marker)

            if position != -1:
                cleaned_answer = cleaned_answer[:position].strip()
                break

        return cleaned_answer

    def _clean_retrieved_chunks(self, chunks: list[dict]) -> list[dict]:
        """
        Limpia el texto recuperado para pasarlo al LLM.
        """
        cleaned_chunks = []

        for chunk in chunks:
            cleaned_chunks.append({
                "text": clean_text(chunk["text"]),
                "metadata": chunk["metadata"],
                "distance": chunk.get("distance")
            })

        return cleaned_chunks

    def _build_unique_sources(self, chunks: list[dict]) -> list[dict]:
        """
        Construye una lista de fuentes sin repetir archivo + página + sección.
        """
        unique_sources = []
        seen = set()

        for chunk in chunks:
            metadata = chunk["metadata"]

            source_key = (
                metadata.get("source", ""),
                metadata.get("page", ""),
                metadata.get("section", "")
            )

            if source_key in seen:
                continue

            seen.add(source_key)

            unique_sources.append({
                "file": metadata.get("source", "desconocido"),
                "author": metadata.get("author", "desconocido"),
                "date": metadata.get("date", "desconocida"),
                "week": metadata.get("week", "desconocida"),
                "topic": metadata.get("topic", "desconocido"),
                "section": metadata.get("section", ""),
                "page": metadata.get("page", "desconocida"),
                "version": metadata.get("version", "desconocida"),
                "distance": chunk.get("distance")
            })

        return unique_sources

    def _build_prompt(self, question: str, chunks: list[dict]) -> str:
        """
        Construye el prompt que recibirá Gemini.
        """
        context = self._format_context(chunks)

        return f"""
Eres un agente RAG académico para un curso de Inteligencia Artificial.

Tu tarea es responder la pregunta del usuario usando únicamente el contexto recuperado desde los apuntes del curso.

Reglas:
- No inventes información.
- No uses conocimiento externo.
- Si el contexto no contiene suficiente información, dilo claramente.
- Redacta una respuesta clara, ordenada y breve.
- No copies fragmentos completos literalmente si no es necesario.
- Puedes resumir y reorganizar las ideas.
- No agregues una sección de fuentes.
- No escribas "Fuentes:" ni cites fragmentos al final.
- Solo redacta la respuesta principal.
- Las fuentes serán agregadas automáticamente por el sistema.

Pregunta del usuario:
{question}

Contexto recuperado:
{context}

Respuesta:
""".strip()

    def _format_context(self, chunks: list[dict]) -> str:
        """
        Formatea los chunks recuperados para incluirlos como contexto del LLM.
        """
        context_parts = []

        for index, chunk in enumerate(chunks, start=1):
            metadata = chunk["metadata"]

            source = metadata.get("source", "desconocido")
            page = metadata.get("page", "desconocida")
            section = metadata.get("section", "")

            header = f"[Fragmento {index} | Archivo: {source} | Página: {page}"

            if section:
                header += f" | Sección: {section}"

            header += "]"

            context_parts.append(
                f"{header}\n{chunk['text']}"
            )

        return "\n\n".join(context_parts)

    def _format_sources(self, sources: list[dict]) -> str:
        """
        Formatea las fuentes para mostrarlas al usuario.
        """
        lines = []

        for index, source in enumerate(sources, start=1):
            section = source.get("section")

            if section:
                lines.append(
                    f"{index}. {source['file']} | página {source['page']} | "
                    f"semana {source['week']} | sección: {section}"
                )
            else:
                lines.append(
                    f"{index}. {source['file']} | página {source['page']} | "
                    f"semana {source['week']}"
                )

        return "\n".join(lines)