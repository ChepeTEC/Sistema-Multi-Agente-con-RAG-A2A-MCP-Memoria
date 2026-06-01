from src.tools.rag_tool import RAGTool

from src.tools.rag_tool import RAGTool
from src.rag.preprocessors import clean_text


class RAGAgent:
    """
    Agente especializado en responder preguntas usando los apuntes del curso.

    Usa RAGTool para recuperar fragmentos relevantes desde ChromaDB y
    construye una respuesta fundamentada con fuentes.
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

        clean_chunks = self._clean_retrieved_chunks(retrieved_chunks)
        sources = self._build_unique_sources(clean_chunks)
        answer = self._build_answer(question, clean_chunks, sources)

        return {
            "answer": answer,
            "sources": sources,
            "chunks": clean_chunks
        }

    def _clean_retrieved_chunks(self, chunks: list[dict]) -> list[dict]:
        """
        Limpia el texto recuperado para que no se vea tan crudo.
        """
        cleaned_chunks = []

        for chunk in chunks:
            cleaned_text = clean_text(chunk["text"])

            cleaned_chunks.append({
                "text": cleaned_text,
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

    def _build_answer(
        self,
        question: str,
        chunks: list[dict],
        sources: list[dict]
    ) -> str:
        """
        Construye una respuesta más ordenada a partir de los chunks recuperados.

        Esta versión todavía no usa un LLM externo. Es una respuesta extractiva
        resumida y organizada para el Hito 1.
        """

        relevant_text = self._combine_relevant_text(chunks[:3])
        summary = self._simple_summarize(question, relevant_text)
        sources_text = self._format_sources(sources)

        return (
            f"Pregunta: {question}\n\n"
            f"Respuesta:\n"
            f"{summary}\n\n"
            f"Fuentes consultadas:\n"
            f"{sources_text}"
        )

    def _combine_relevant_text(self, chunks: list[dict]) -> str:
        """
        Une los textos más relevantes recuperados.
        """
        texts = []

        for chunk in chunks:
            text = chunk["text"].strip()

            if text:
                texts.append(text)

        return " ".join(texts)

    def _simple_summarize(self, question: str, text: str) -> str:
        """
        Genera una respuesta básica sin LLM.

        Toma las oraciones más relevantes que contienen términos importantes
        de la pregunta. Si no encuentra coincidencias claras, usa el inicio del
        contexto recuperado.
        """

        question_terms = [
            term.lower()
            for term in question.replace("¿", "").replace("?", "").split()
            if len(term) > 3
        ]

        sentences = self._split_into_sentences(text)
        selected_sentences = []

        for sentence in sentences:
            sentence_lower = sentence.lower()

            if any(term in sentence_lower for term in question_terms):
                selected_sentences.append(sentence.strip())

            if len(selected_sentences) >= 3:
                break

        if not selected_sentences:
            selected_sentences = sentences[:3]

        cleaned_answer = " ".join(selected_sentences)
        cleaned_answer = cleaned_answer.strip()

        if not cleaned_answer:
            return "No fue posible construir una respuesta clara con los fragmentos recuperados."

        return (
            "Según los apuntes recuperados, "
            + cleaned_answer[0].lower()
            + cleaned_answer[1:]
        )

    def _split_into_sentences(self, text: str) -> list[str]:
        """
        Divide texto en oraciones simples.
        """
        raw_sentences = text.replace("\n", " ").split(".")
        sentences = []

        for sentence in raw_sentences:
            sentence = sentence.strip()

            if len(sentence) > 30:
                sentences.append(sentence + ".")

        return sentences

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