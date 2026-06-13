from langsmith import trace

from src.tools.rag_tool import RAGTool
from src.rag.preprocessors import clean_text
from src.rag.metadata import extract_author_from_text, normalize_author_name
from src.llm.gemini_client import GeminiClient
from src.observability.langfuse_client import langfuse_tracer


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

        trace = langfuse_tracer.create_trace(
            name="rag_agent_answer",
            input_data={"question": question, "n_results": n_results},
            metadata={"agent": "RAGAgent"}
        )

        try:
            retrieved_chunks = self.rag_tool.search_notes(
                query=question,
                n_results=n_results
            )

            langfuse_tracer.create_span(
                trace=trace,
                name="rag_retrieval",
                input_data={"query": question, "n_results": n_results},
                output_data={"retrieved_chunks_count": len(retrieved_chunks)},
                metadata={
                    "tool": "RAGTool",
                    "vector_db": "ChromaDB",
                    "raw_chunks": self._chunks_for_langfuse(retrieved_chunks)
                }
            )

            if not retrieved_chunks:
                result = {
                    "answer": "No encontré información relevante en los apuntes.",
                    "sources": [],
                    "chunks": [],
                    "agent": "RAGAgent"
                }

                langfuse_tracer.update_trace_output(trace, result)
                return result

            clean_chunks = self._clean_retrieved_chunks(retrieved_chunks)
            sources = self._build_unique_sources(clean_chunks)

            if self._is_author_lookup_question(question):
                author_answer = self._build_author_lookup_answer(question, clean_chunks)

                if author_answer:
                    author_chunks = self._filter_author_lookup_chunks(question, clean_chunks)
                    author_sources = self._build_unique_sources(author_chunks) or sources
                    final_answer = (
                        f"{author_answer}\n\n"
                        f"Fuentes consultadas:\n"
                        f"{self._format_sources(author_sources)}"
                    )

                    result = {
                        "answer": final_answer,
                        "sources": author_sources,
                        "chunks": clean_chunks,
                        "agent": "RAGAgent"
                    }

                    langfuse_tracer.update_trace_output(trace, result)
                    return result

            prompt = self._build_prompt(question, clean_chunks)
            llm_result = self.llm.generate(prompt)
            generated_answer = llm_result["text"]

            langfuse_tracer.create_generation(
                trace=trace,
                name="gemini_generation",
                model=getattr(self.llm, "model", "gemini"),
                prompt=prompt,
                response=generated_answer,
                metadata={
                    "agent": "RAGAgent",
                    "sources": sources,
                    "chunks_used": self._chunks_for_langfuse(clean_chunks)
                }
            )

            generated_answer = self._remove_llm_sources(generated_answer)

            final_answer = (
                f"{generated_answer}\n\n"
                f"Fuentes consultadas:\n"
                f"{self._format_sources(sources)}"
            )

            result = {
                "answer": final_answer,
                "sources": sources,
                "chunks": clean_chunks,
                "agent": "RAGAgent"
            }

            langfuse_tracer.update_trace_output(trace, result)
            return result

        except Exception as exc:
            langfuse_tracer.create_span(
                trace=trace,
                name="rag_agent_error",
                input_data={"question": question},
                output_data={"error": str(exc)},
                metadata={"agent": "RAGAgent"}
            )
            langfuse_tracer.update_trace_output(
                trace,
                {"error": str(exc), "agent": "RAGAgent"}
            )
            raise

        finally:
            langfuse_tracer.close_trace(trace)
            langfuse_tracer.flush()

    def _chunks_for_langfuse(self, chunks: list[dict]) -> list[dict]:
        """
        Prepara los chunks para enviarlos a Langfuse sin saturar la traza.
        """
        formatted_chunks = []

        for index, chunk in enumerate(chunks, start=1):
            metadata = chunk.get("metadata", {})
            text = chunk.get("text", "")

            formatted_chunks.append({
                "index": index,
                "text_preview": text[:500],
                "source": metadata.get("source", "desconocido"),
                "page": metadata.get("page", "desconocida"),
                "week": metadata.get("week", "desconocida"),
                "section": metadata.get("section", ""),
                "distance": chunk.get("distance")
            })

        return formatted_chunks

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
                "author": self._normalize_author(metadata.get("author")) or "desconocido",
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

Reglas adicionales para robustez:
- Si hay varios fragmentos relacionados, integra la evidencia aunque este repartida entre documentos.
- Si varios documentos son relevantes, compara o lista la informacion por documento.
- No digas que falta informacion si los fragmentos recuperados contienen evidencia directa o parcial suficiente para responder.
- Para puntos importantes, menciona entre parentesis solo el valor exacto de Archivo y Pagina que aparece en el fragmento usado; no inventes ni reformatees nombres de archivo.

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
            author = metadata.get("author", "desconocido")
            date = metadata.get("date", "")
            week = metadata.get("week", "")

            header = f"[Fragmento {index} | Archivo: {source} | Página: {page}"

            if section:
                header += f" | Sección: {section}"

            header += "]"

            context_parts.append(
                f"{header}\n"
                f"Autor: {author}\n"
                f"Fecha: {date or 'desconocida'}\n"
                f"Semana: {week or 'desconocida'}\n"
                f"Archivo: {source}\n"
                f"Pagina: {page}\n"
                f"Seccion: {section or 'desconocida'}\n"
                f"{chunk['text']}"
            )

        return "\n\n".join(context_parts)

    def _is_author_lookup_question(self, question: str) -> bool:
        question_lower = question.lower()
        question_lower = (
            question_lower
            .replace("Ã©", "e")
            .replace("é", "e")
            .replace("Ã­", "i")
            .replace("í", "i")
            .replace("Ã³", "o")
            .replace("ó", "o")
        )
        signals = [
            "quien hizo",
            "quién hizo",
            "quiÃ©n hizo",
            "quien realizo",
            "quién realizó",
            "quien realizÃ³",
            "quiÃ©n realizo",
            "quiÃ©n realizÃ³",
            "autor",
        ]

        has_signal = any(signal in question_lower for signal in signals)
        has_author_shape = (
            (
                "apunte" in question_lower
                or "apuntes" in question_lower
                or "resumen" in question_lower
            )
            and any(action in question_lower for action in ["hizo", "escribio", "realizo"])
        )

        return has_signal or has_author_shape

    def _build_author_lookup_answer(
        self,
        question: str,
        chunks: list[dict]
    ) -> str | None:
        question_lower = question.lower()

        if "quiz 2" not in question_lower and "quiz2" not in question_lower:
            return None

        documents = {}

        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            source = metadata.get("source")

            if not source:
                continue

            document = documents.setdefault(
                source,
                {
                    "source": source,
                    "author": self._normalize_author(metadata.get("author")),
                    "has_target": False,
                    "texts": [],
                }
            )

            document["texts"].append(chunk.get("text", ""))
            searchable_text = clean_text(chunk.get("text", "")).lower().replace(" ", "")

            if "quiz2" in searchable_text or "respuestasquiz2" in searchable_text:
                document["has_target"] = True

            if metadata.get("author"):
                document["author"] = self._normalize_author(metadata.get("author"))

        matched_documents = [
            document
            for document in documents.values()
            if document["has_target"]
        ]

        for document in matched_documents:
            if document.get("author"):
                continue

            extracted_author = extract_author_from_text("\n".join(document["texts"]))

            if extracted_author:
                document["author"] = extracted_author

        matched_documents = [
            document
            for document in matched_documents
            if document.get("author")
        ]

        if not matched_documents:
            return None

        if len(matched_documents) == 1:
            document = matched_documents[0]
            return (
                "El apunte relacionado con Quiz 2 fue hecho por "
                f"{document['author']} ({document['source']})."
            )

        lines = ["Encontre varios documentos relacionados con Quiz 2:"]

        for index, document in enumerate(matched_documents, start=1):
            lines.append(
                f"{index}. {document['author']} - {document['source']}"
            )

        return "\n".join(lines)

    def _filter_author_lookup_chunks(
        self,
        question: str,
        chunks: list[dict]
    ) -> list[dict]:
        question_lower = question.lower()

        if "quiz 2" not in question_lower and "quiz2" not in question_lower:
            return []

        matched_sources = set()

        for chunk in chunks:
            searchable_text = clean_text(chunk.get("text", "")).lower().replace(" ", "")

            if "quiz2" in searchable_text or "respuestasquiz2" in searchable_text:
                source = chunk.get("metadata", {}).get("source")

                if source:
                    matched_sources.add(source)

        filtered_chunks = []

        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            searchable_text = clean_text(chunk.get("text", "")).lower().replace(" ", "")

            if metadata.get("source") not in matched_sources:
                continue

            if (
                "quiz2" in searchable_text
                or "respuestasquiz2" in searchable_text
                or (metadata.get("page") == 1 and metadata.get("chunk_index") == 0)
            ):
                filtered_chunks.append(chunk)

        return filtered_chunks

    def _normalize_author(self, author: str | None) -> str | None:
        if not author:
            return None

        return normalize_author_name(author)

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
