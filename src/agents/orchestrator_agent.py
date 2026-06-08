from time import perf_counter
from collections.abc import Callable
from src.agents.rag_agent import RAGAgent
from src.agents.web_search_agent import WebSearchAgent
from src.config.settings import settings
from src.llm.base import LLMClient
from src.llm.gemini_client import GeminiClient
from src.observability.langfuse_client import langfuse_tracer


class OrchestratorAgent:
    """
    Routes user questions to the most appropriate specialized agent.

    The routing decision is delegated to Gemini. The orchestrator only
    normalizes the model output and applies the course policy fallback:
    when the decision is ambiguous, prefer RAG.
    """

    AGENT_NAME = "OrchestratorAgent"
    VALID_AGENTS = {"rag", "web"}

    def __init__(
        self,
        rag_agent: RAGAgent | None = None,
        web_search_agent: WebSearchAgent | None = None,
        llm_client: LLMClient | None = None,
        rag_agent_factory: Callable[[], RAGAgent] | None = None,
        web_search_agent_factory: Callable[[], WebSearchAgent] | None = None,
    ):
        self.rag_agent = rag_agent
        self.web_search_agent = web_search_agent
        self.rag_agent_factory = rag_agent_factory or RAGAgent
        self.web_search_agent_factory = web_search_agent_factory or WebSearchAgent
        self.llm_client = llm_client or GeminiClient(
            model=settings.ORCHESTRATOR_LLM_MODEL
        )

    def answer(self, question: str) -> dict:
        question = question.strip() if question else ""

        trace = langfuse_tracer.create_trace(
            name="orchestrator_request",
            input_data={"question": question},
            metadata={"agent": self.AGENT_NAME}
        )

        try:
            if not question:
                langfuse_tracer.create_span(
                    trace=trace,
                    name="input_validation",
                    input_data={"question": question},
                    output_data={"valid": False, "error": "La pregunta no puede estar vacia."},
                    metadata={"agent": self.AGENT_NAME}
                )
                raise ValueError("La pregunta no puede estar vacia.")

            langfuse_tracer.create_span(
                trace=trace,
                name="input_validation",
                input_data={"question": question},
                output_data={"valid": True},
                metadata={"agent": self.AGENT_NAME}
            )

            total_started_at = perf_counter()
            decision_data = self._decide_agent(question)
            agent_selected = decision_data["agent_selected"]
            decision_reason = self._build_decision_reason(agent_selected)

            langfuse_tracer.create_span(
                trace=trace,
                name="routing_decision",
                input_data={
                    "question": question,
                    "valid_agents": sorted(self.VALID_AGENTS),
                },
                output_data={
                    "agent_selected": agent_selected,
                    "decision_reason": decision_reason,
                    "raw_decision": decision_data["raw_decision"],
                },
                metadata={
                    "agent": self.AGENT_NAME,
                    "decision_model": decision_data["model"],
                    "decision_provider": decision_data["provider"],
                    "decision_response_id": decision_data["response_id"],
                    "decision_duration_ms": decision_data["duration_ms"],
                }
            )

            if agent_selected == "web":
                delegated_agent_name = "WebSearchAgent"
                agent_result = self._get_web_search_agent().answer(
                    question=question,
                    justification=decision_reason,
                )
            else:
                delegated_agent_name = "RAGAgent"
                agent_result = self._get_rag_agent().answer(question)

            langfuse_tracer.create_span(
                trace=trace,
                name="agent_response",
                input_data={
                    "question": question,
                    "delegated_agent": delegated_agent_name,
                },
                output_data={
                    "answer_preview": agent_result.get("answer", "")[:1000],
                    "sources_count": len(agent_result.get("sources", [])),
                    "chunks_count": len(agent_result.get("chunks", [])),
                },
                metadata={
                    "agent": self.AGENT_NAME,
                    "delegated_agent": agent_result.get("agent", delegated_agent_name),
                    "sources": agent_result.get("sources", []),
                }
            )

            total_duration_ms = round((perf_counter() - total_started_at) * 1000, 2)

            result = {
                "agent_selected": agent_selected,
                "decision_reason": decision_reason,
                "answer": agent_result.get("answer", ""),
                "sources": agent_result.get("sources", []),
                "trace": {
                    "question": question,
                    "orchestrator": self.AGENT_NAME,
                    "agent_selected": agent_selected,
                    "decision_model": decision_data["model"],
                    "decision_provider": decision_data["provider"],
                    "decision_response_id": decision_data["response_id"],
                    "raw_decision": decision_data["raw_decision"],
                    "decision_duration_ms": decision_data["duration_ms"],
                    "total_duration_ms": total_duration_ms,
                    "delegated_agent": agent_result.get("agent"),
                    "delegated_trace": agent_result.get("trace", {}),
                },
            }

            langfuse_tracer.update_trace_output(trace, result)
            return result

        except Exception as exc:
            langfuse_tracer.create_span(
                trace=trace,
                name="orchestrator_error",
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

    def _decide_agent(self, question: str) -> dict:
        decision_started_at = perf_counter()
        llm_result = self.llm_client.generate(
            prompt=self._build_decision_prompt(question),
            instructions=self._build_decision_instructions(),
        )
        measured_duration_ms = round((perf_counter() - decision_started_at) * 1000, 2)

        raw_decision = str(llm_result.get("text", "")).strip()
        agent_selected = self._select_agent(question, raw_decision)

        return {
            "agent_selected": agent_selected,
            "raw_decision": raw_decision,
            "provider": llm_result.get("provider", "unknown"),
            "model": llm_result.get("model", "unknown"),
            "response_id": llm_result.get("response_id"),
            "duration_ms": llm_result.get("duration_ms", measured_duration_ms),
        }

    @staticmethod
    def _build_decision_instructions() -> str:
        return (
            "Eres el clasificador de un sistema multi-agente academico. "
            "Debes decidir que agente debe responder la pregunta del usuario. "
            "Elige rag para conceptos de IA, redes neuronales, funciones de "
            "activacion, descenso del gradiente, backpropagation, transformers, "
            "RAG, embeddings y cualquier tema que pueda responderse con apuntes "
            "o documentos del curso. Elige web solo si el usuario pide de forma "
            "explicita actualidad, noticias, internet, paginas web, documentacion "
            "oficial actual o informacion reciente. Si existe duda, elige rag. "
            "Responde exclusivamente con una palabra: rag o web."
        )

    @staticmethod
    def _build_decision_prompt(question: str) -> str:
        return (
            "Pregunta del usuario:\n"
            f"{question}\n\n"
            "Agente a utilizar:"
        )

    @classmethod
    def _normalize_decision(cls, raw_decision: str) -> str:
        decision = raw_decision.strip().lower()

        if decision in cls.VALID_AGENTS:
            return decision

        # Defensive fallback required by the routing policy: when in doubt, use RAG.
        return "rag"

    @classmethod
    def _select_agent(cls, question: str, raw_decision: str) -> str:
        question_lower = question.lower()

        web_signals = [
            "actual",
            "actualidad",
            "busca",
            "buscar",
            "documentacion oficial",
            "esta semana",
            "hoy",
            "internet",
            "noticia",
            "noticias",
            "reciente",
            "recientes",
            "web",
        ]
        academic_signals = [
            "activacion",
            "activación",
            "backpropagation",
            "descenso del gradiente",
            "embedding",
            "embeddings",
            "funcion de activacion",
            "función de activación",
            "gradiente",
            "leaky relu",
            "rag",
            "red neuronal",
            "redes neuronales",
            "relu",
            "transformer",
            "transformers",
        ]

        has_web_signal = any(signal in question_lower for signal in web_signals)
        has_academic_signal = any(signal in question_lower for signal in academic_signals)

        if has_web_signal:
            return "web"

        if has_academic_signal:
            return "rag"

        return cls._normalize_decision(raw_decision)

    def _get_rag_agent(self) -> RAGAgent:
        if self.rag_agent is None:
            self.rag_agent = self.rag_agent_factory()

        return self.rag_agent

    def _get_web_search_agent(self) -> WebSearchAgent:
        if self.web_search_agent is None:
            self.web_search_agent = self.web_search_agent_factory()

        return self.web_search_agent

    @staticmethod
    def _build_decision_reason(agent_selected: str) -> str:
        if agent_selected == "web":
            return (
                "Gemini clasifico la pregunta como una consulta que requiere "
                "informacion externa, reciente o disponible en internet."
            )

        return (
            "Gemini clasifico la pregunta como una consulta que puede responderse "
            "con los apuntes o documentos del curso, o como una consulta ambigua "
            "donde la politica indica preferir RAG."
        )
