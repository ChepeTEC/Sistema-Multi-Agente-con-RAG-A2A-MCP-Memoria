from time import perf_counter

from src.config.settings import settings
from src.llm.base import LLMClient
from src.llm.gemini_client import GeminiClient
from src.observability.langfuse_client import langfuse_tracer


class SummarizerAgent:
    """
    Agente especializado en resumir historial conversacional de una sesion.

    No consulta RAG ni Web Search. Usa solo el contexto conversacional que el
    orquestador obtiene desde MemoryTool.
    """

    AGENT_NAME = "SummarizerAgent"

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client or GeminiClient(
            model=settings.SUMMARIZER_LLM_MODEL
        )

    def answer(
        self,
        question: str,
        conversation_context: str | None = None,
    ) -> dict:
        question = question.strip() if question else ""
        conversation_context = (conversation_context or "").strip()

        if not question:
            raise ValueError("La pregunta no puede estar vacia.")

        trace = langfuse_tracer.create_trace(
            name="summarizer_agent_answer",
            input_data={
                "question": question,
                "has_conversation_context": bool(conversation_context),
            },
            metadata={"agent": self.AGENT_NAME}
        )

        try:
            if not conversation_context:
                result = {
                    "agent": self.AGENT_NAME,
                    "answer": (
                        "Todavia no hay suficiente historial en esta sesion "
                        "para generar un resumen."
                    ),
                    "sources": [],
                    "trace": {
                        "has_conversation_context": False,
                        "turns_used": 0,
                    },
                }
                langfuse_tracer.update_trace_output(trace, result)
                return result

            started_at = perf_counter()
            prompt = self._build_prompt(question, conversation_context)
            llm_result = self.llm_client.generate(
                prompt=prompt,
                instructions=self._build_instructions(),
            )
            duration_ms = round((perf_counter() - started_at) * 1000, 2)

            answer = str(llm_result.get("text", "")).strip()
            result = {
                "agent": self.AGENT_NAME,
                "answer": answer,
                "sources": [],
                "trace": {
                    "has_conversation_context": True,
                    "turns_used": self._count_turns(conversation_context),
                    "duration_ms": duration_ms,
                    "llm": {
                        "provider": llm_result.get("provider", "unknown"),
                        "model": llm_result.get("model", "unknown"),
                        "response_id": llm_result.get("response_id"),
                        "duration_ms": llm_result.get("duration_ms", duration_ms),
                    },
                },
            }

            langfuse_tracer.create_generation(
                trace=trace,
                name="summarizer_generation",
                model=llm_result.get("model", getattr(self.llm_client, "model", "gemini")),
                prompt=prompt,
                response=answer,
                metadata={"agent": self.AGENT_NAME}
            )
            langfuse_tracer.update_trace_output(trace, result)
            return result

        except Exception as exc:
            langfuse_tracer.create_span(
                trace=trace,
                name="summarizer_agent_error",
                input_data={"question": question},
                output_data={"error": str(exc)},
                metadata={"agent": self.AGENT_NAME}
            )
            langfuse_tracer.update_trace_output(
                trace,
                {"error": str(exc), "agent": self.AGENT_NAME}
            )
            raise

        finally:
            langfuse_tracer.close_trace(trace)
            langfuse_tracer.flush()

    @staticmethod
    def _build_instructions() -> str:
        return (
            "Eres el agente resumidor de un sistema multi-agente academico. "
            "Resume exclusivamente el historial conversacional proporcionado. "
            "No inventes preguntas, respuestas, fuentes ni conclusiones. "
            "Si el usuario pide un formato especifico, respetalo cuando sea posible. "
            "Responde en espanol con una sintesis clara y breve."
        )

    @staticmethod
    def _build_prompt(question: str, conversation_context: str) -> str:
        return (
            "Historial reciente de la sesion:\n"
            f"{conversation_context}\n\n"
            "Solicitud actual del usuario:\n"
            f"{question}\n\n"
            "Resumen:"
        )

    @staticmethod
    def _count_turns(conversation_context: str) -> int:
        return conversation_context.count("[Turno ")
