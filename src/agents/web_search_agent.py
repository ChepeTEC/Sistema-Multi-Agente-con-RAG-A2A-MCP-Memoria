from time import perf_counter

from src.config.settings import settings
from src.llm.base import LLMClient
from src.llm.gemini_client import GeminiClient
from src.observability.langfuse_client import langfuse_tracer
from src.tools.web_search_tool import WebSearchTool


class WebSearchAgent:
    """
    Specialized agent for controlled internet searches.

    The orchestrator must provide a justification for each search.
    """

    AGENT_NAME = "WebSearchAgent"
    MAX_SEARCH_QUERY_CHARS = 380

    def __init__(
        self,
        web_search_tool: WebSearchTool | None = None,
        llm_client: LLMClient | None = None
    ):
        self.web_search_tool = web_search_tool or WebSearchTool()
        self.llm_client = llm_client or GeminiClient(
            model=settings.WEB_SEARCH_LLM_MODEL
        )

    def answer(
        self,
        question: str,
        justification: str,
        max_results: int = 5,
        search_depth: str = "basic",
        conversation_context: str | None = None,
    ) -> dict:
        started_at = perf_counter()
        trace = langfuse_tracer.create_trace(
            name="web_search_agent_answer",
            input_data={
                "question": question,
                "justification": justification,
                "max_results": max_results,
                "search_depth": search_depth,
                "has_conversation_context": bool(conversation_context),
            },
            metadata={"agent": self.AGENT_NAME},
        )

        try:
            search_query = self._build_search_query(question, conversation_context)
            search_data = self.web_search_tool.search(
                query=search_query,
                justification=justification,
                max_results=max_results,
                search_depth=search_depth
            )

            sources = [
                {
                    "title": result["title"],
                    "url": result["url"],
                    "score": result["score"],
                    "published_date": result["published_date"]
                }
                for result in search_data["results"]
            ]

            langfuse_tracer.create_span(
                trace=trace,
                name="web_search_tool_call",
                input_data={
                    "query": search_query,
                    "justification": justification,
                    "max_results": max_results,
                    "search_depth": search_depth,
                },
                output_data={
                    "provider": search_data["provider"],
                    "request_id": search_data["request_id"],
                    "results_count": len(search_data["results"]),
                    "duration_ms": search_data["duration_ms"],
                    "sources": sources,
                },
                metadata={
                    "agent": self.AGENT_NAME,
                    "tool": "WebSearchTool",
                    "provider": search_data["provider"],
                    "urls": [source["url"] for source in sources],
                },
            )

            llm_data = self._generate_answer(
                question=question,
                results=search_data["results"],
                conversation_context=conversation_context,
            )
            duration_ms = round((perf_counter() - started_at) * 1000, 2)

            result = {
                "agent": self.AGENT_NAME,
                "answer": llm_data["text"],
                "sources": sources,
                "trace": {
                    "query": search_data["query"],
                    "original_question": question,
                    "has_conversation_context": bool(conversation_context),
                    "justification": search_data["justification"],
                    "urls": [source["url"] for source in sources],
                    "duration_ms": duration_ms,
                    "search": {
                        "provider": search_data["provider"],
                        "request_id": search_data["request_id"],
                        "duration_ms": search_data["duration_ms"]
                    },
                    "llm": {
                        "provider": llm_data["provider"],
                        "model": llm_data["model"],
                        "response_id": llm_data["response_id"],
                        "duration_ms": llm_data["duration_ms"]
                    }
                },
                "results": search_data["results"]
            }

            langfuse_tracer.create_generation(
                trace=trace,
                name="web_search_generation",
                model=llm_data.get("model", getattr(self.llm_client, "model", "gemini")),
                prompt=llm_data.get("prompt", ""),
                response=llm_data["text"],
                metadata={
                    "agent": self.AGENT_NAME,
                    "provider": llm_data.get("provider"),
                    "response_id": llm_data.get("response_id"),
                    "sources": sources,
                    "duration_ms": llm_data.get("duration_ms"),
                },
            )
            langfuse_tracer.update_trace_output(trace, result)
            return result

        except Exception as exc:
            langfuse_tracer.create_span(
                trace=trace,
                name="web_search_agent_error",
                input_data={
                    "question": question,
                    "justification": justification,
                },
                output_data={"error": str(exc)},
                metadata={"agent": self.AGENT_NAME},
            )
            langfuse_tracer.update_trace_output(
                trace,
                {"error": str(exc), "agent": self.AGENT_NAME},
            )
            raise

        finally:
            langfuse_tracer.close_trace(trace)
            langfuse_tracer.flush()

    def _build_search_query(
        self,
        question: str,
        conversation_context: str | None = None,
    ) -> str:
        del conversation_context

        normalized_question = " ".join((question or "").split())

        if len(normalized_question) <= self.MAX_SEARCH_QUERY_CHARS:
            return normalized_question

        return normalized_question[:self.MAX_SEARCH_QUERY_CHARS].rsplit(" ", 1)[0].strip()

    def _generate_answer(
        self,
        question: str,
        results: list[dict],
        conversation_context: str | None = None,
    ) -> dict:
        prompt = self._build_generation_prompt(
            question=question,
            results=results,
            conversation_context=conversation_context,
        )
        llm_result = self.llm_client.generate(
            prompt=prompt,
            instructions=self._build_generation_instructions(),
        )

        return {
            **llm_result,
            "prompt": prompt,
        }

    def _build_generation_prompt(
        self,
        question: str,
        results: list[dict],
        conversation_context: str | None = None,
    ) -> str:
        formatted_results = []
        for index, result in enumerate(results, start=1):
            formatted_results.append(
                f"[Fuente {index}]\n"
                f"Titulo: {result['title']}\n"
                f"URL: {result['url']}\n"
                f"Fecha: {result['published_date'] or 'No disponible'}\n"
                f"Contenido: {result['content']}"
            )

        context = "\n\n".join(formatted_results)
        memory_section = ""
        cleaned_conversation_context = (conversation_context or "").strip()

        if cleaned_conversation_context:
            memory_section = (
                "Historial reciente de la conversacion:\n"
                f"{cleaned_conversation_context}\n\n"
            )

        return (
            f"{memory_section}"
            f"Pregunta del usuario:\n{question}\n\n"
            f"Resultados obtenidos por la herramienta de busqueda:\n"
            f"{context or 'No se encontraron resultados.'}"
        )

    @staticmethod
    def _build_generation_instructions() -> str:
        return (
            "Responde en espanol usando exclusivamente los resultados web "
            "proporcionados. Incluye citas inline con el formato [Fuente N]. "
            "No inventes datos ni fuentes. Si los resultados no permiten "
            "responder, indicalo claramente. Usa el historial reciente solo "
            "para resolver referencias conversacionales, no como fuente."
        )
