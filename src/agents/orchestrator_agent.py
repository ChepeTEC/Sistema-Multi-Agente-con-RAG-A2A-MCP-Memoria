from time import perf_counter
from collections.abc import Callable
import unicodedata
from src.agents.rag_agent import RAGAgent
from src.agents.summarizer_agent import SummarizerAgent
from src.agents.web_search_agent import WebSearchAgent
from src.config.settings import settings
from src.llm.base import LLMClient
from src.llm.gemini_client import GeminiClient
from src.observability.langfuse_client import langfuse_tracer
from src.tools.historical_memory_tool import HistoricalMemoryTool
from src.tools.memory_tool import MemoryTool
from src.agents.transactional_agent import TransactionalAgent



class OrchestratorAgent:
    """
    Routes user questions to the most appropriate specialized agent.

    The routing decision is delegated to Gemini. The orchestrator only
    normalizes the model output and applies the course policy fallback:
    when the decision is ambiguous, prefer RAG.
    """

    AGENT_NAME = "OrchestratorAgent"
    VALID_AGENTS = {"rag", "summary", "transactional", "web"}

    def __init__(
        self,
        rag_agent: RAGAgent | None = None,
        summarizer_agent: SummarizerAgent | None = None,
        web_search_agent: WebSearchAgent | None = None,
        transactional_agent: TransactionalAgent | None = None,
        llm_client: LLMClient | None = None,
        historical_memory_tool: HistoricalMemoryTool | None = None,
        memory_tool: MemoryTool | None = None,
        rag_agent_factory: Callable[[], RAGAgent] | None = None,
        summarizer_agent_factory: Callable[[], SummarizerAgent] | None = None,
        web_search_agent_factory: Callable[[], WebSearchAgent] | None = None,
        transactional_agent_factory: Callable[[], TransactionalAgent] | None = None
    ):
        self.rag_agent = rag_agent
        self.summarizer_agent = summarizer_agent
        self.web_search_agent = web_search_agent
        self.transactional_agent = transactional_agent
        self.historical_memory_tool = historical_memory_tool or HistoricalMemoryTool()
        self.memory_tool = memory_tool or MemoryTool()
        self.rag_agent_factory = rag_agent_factory or RAGAgent
        self.summarizer_agent_factory = summarizer_agent_factory or SummarizerAgent
        self.web_search_agent_factory = web_search_agent_factory or WebSearchAgent
        self.transactional_agent_factory = transactional_agent_factory or TransactionalAgent
        self.llm_client = llm_client or GeminiClient(
            model=settings.ORCHESTRATOR_LLM_MODEL
        )

    def answer(self, question: str, session_id: str | None = None) -> dict:
        question = question.strip() if question else ""
        session_id = self._normalize_session_id(session_id)

        trace = langfuse_tracer.create_trace(
            name="orchestrator_request",
            input_data={"question": question, "session_id": session_id},
            metadata={"agent": self.AGENT_NAME, "session_id": session_id}
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
                input_data={"question": question, "session_id": session_id},
                output_data={"valid": True},
                metadata={"agent": self.AGENT_NAME}
            )

            total_started_at = perf_counter()
            memory_context = self.memory_tool.get_context(session_id)

            langfuse_tracer.create_span(
                trace=trace,
                name="memory_context_lookup",
                input_data={"session_id": session_id},
                output_data={
                    "turns_count": memory_context["turns_count"],
                    "has_context": memory_context["has_context"],
                },
                metadata={"agent": self.AGENT_NAME, "tool": self.memory_tool.TOOL_NAME}
            )

            conversation_context = memory_context["formatted_context"]
            historical_memory_lookup = self._lookup_historical_memory(
                question=question,
                session_id=session_id,
            )

            if historical_memory_lookup["queried"]:
                langfuse_tracer.create_span(
                    trace=trace,
                    name="historical_memory_lookup",
                    input_data={
                        "question": question,
                        "session_id": session_id,
                    },
                    output_data={
                        "matches_count": historical_memory_lookup["matches_count"],
                        "has_context": historical_memory_lookup["has_context"],
                        "scope": historical_memory_lookup["scope"],
                        "error": historical_memory_lookup["error"],
                    },
                    metadata={
                        "agent": self.AGENT_NAME,
                        "tool": self.historical_memory_tool.TOOL_NAME,
                    }
                )
                conversation_context = self._merge_contexts(
                    conversation_context,
                    historical_memory_lookup["formatted_context"],
                )

            decision_data = self._decide_agent(question, conversation_context)
            agent_selected = decision_data["agent_selected"]
            decision_reason = self._build_decision_reason(agent_selected)

            langfuse_tracer.create_span(
                trace=trace,
                name="routing_decision",
                input_data={
                    "question": question,
                    "session_id": session_id,
                    "memory_turns_count": memory_context["turns_count"],
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

            if agent_selected == "summary":
                summary_memory_context = self.memory_tool.get_summary_context(session_id)
                temporal_summary_context = summary_memory_context["formatted_context"]
                if historical_memory_lookup["queried"]:
                    conversation_context = self._merge_contexts(
                        temporal_summary_context,
                        historical_memory_lookup["formatted_context"],
                    )
                    memory_context = {
                        **summary_memory_context,
                        "turns_count": summary_memory_context["turns_count"],
                    }
                else:
                    memory_context = summary_memory_context
                    conversation_context = temporal_summary_context
                delegated_agent_name = "SummarizerAgent"
                agent_result = self._get_summarizer_agent().answer(
                    question=question,
                    conversation_context=conversation_context,
                )
            elif agent_selected == "web":
                delegated_agent_name = "WebSearchAgent"
                agent_result = self._get_web_search_agent().answer(
                    question=question,
                    justification=decision_reason,
                    conversation_context=conversation_context,
                )
            elif agent_selected == "transactional":
                delegated_agent_name = "TransactionalAgent"
                agent_result = self._get_transactional_agent().answer(
                    question=question,
                    conversation_context=conversation_context,
                )
            else:
                delegated_agent_name = "RAGAgent"
                agent_result = self._get_rag_agent().answer(
                    question=question,
                    conversation_context=conversation_context,
                )

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
            memory_update = self.memory_tool.save_turn(
                session_id=session_id,
                question=question,
                answer=agent_result.get("answer", ""),
                agent_selected=agent_selected,
                sources=agent_result.get("sources", []),
            )
            historical_memory_update = self._save_historical_memory_turn(
                session_id=session_id,
                question=question,
                answer=agent_result.get("answer", ""),
                agent_selected=agent_selected,
                sources=agent_result.get("sources", []),
            )

            langfuse_tracer.create_span(
                trace=trace,
                name="memory_update",
                input_data={
                    "session_id": session_id,
                    "question": question,
                    "agent_selected": agent_selected,
                },
                output_data=memory_update,
                metadata={"agent": self.AGENT_NAME, "tool": self.memory_tool.TOOL_NAME}
            )
            langfuse_tracer.create_span(
                trace=trace,
                name="historical_memory_update",
                input_data={
                    "session_id": session_id,
                    "question": question,
                    "agent_selected": agent_selected,
                },
                output_data=historical_memory_update,
                metadata={
                    "agent": self.AGENT_NAME,
                    "tool": self.historical_memory_tool.TOOL_NAME,
                }
            )

            result = {
                "agent_selected": agent_selected,
                "decision_reason": decision_reason,
                "answer": agent_result.get("answer", ""),
                "sources": agent_result.get("sources", []),
                "trace": {
                    "question": question,
                    "session_id": session_id,
                    "orchestrator": self.AGENT_NAME,
                    "agent_selected": agent_selected,
                    "memory": {
                        "type": "temporal_session",
                        "turns_used": memory_context["turns_count"],
                        "updated": True,
                    },
                    "historical_memory": {
                        "type": "persistent_sqlite",
                        "available": historical_memory_lookup["available"],
                        "queried": historical_memory_lookup["queried"],
                        "matches": historical_memory_lookup["matches_count"],
                        "scope": historical_memory_lookup["scope"],
                        "updated": historical_memory_update["updated"],
                        "turn_id": historical_memory_update.get("id"),
                        "error": (
                            historical_memory_lookup["error"]
                            or historical_memory_update.get("error")
                        ),
                    },
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

    def _decide_agent(self, question: str, conversation_context: str = "") -> dict:
        decision_started_at = perf_counter()
        llm_result = self.llm_client.generate(
            prompt=self._build_decision_prompt(question, conversation_context),
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
            "Elige summary si el usuario pide resumir, sintetizar o listar lo "
            "hablado en la conversacion, sesion actual o historial persistente. "
            "Elige rag para conceptos de IA, redes neuronales, funciones de "
            "activacion, descenso del gradiente, backpropagation, transformers, "
            "RAG, embeddings y cualquier tema que pueda responderse con apuntes "
            "o documentos del curso. Elige transactional si el usuario pregunta "
            "por movimientos de clientes, historial de transacciones, fraude, "
            "comportamiento de gasto, cuentas bancarias, perfiles financieros, "
            "comercios, riesgo o analisis financiero sobre la base transaccional. "
            "Elige web solo si el usuario pide de forma "
            "explicita actualidad, noticias, internet, paginas web, documentacion "
            "oficial actual o informacion reciente. Si existe duda, elige rag. "
            "Responde exclusivamente con una palabra: rag, summary, transactional o web."
        )

    @staticmethod
    def _build_decision_prompt(question: str, conversation_context: str = "") -> str:
        context = conversation_context.strip()

        if context:
            return (
                "Historial reciente de la sesion:\n"
                f"{context}\n\n"
                "Pregunta actual del usuario:\n"
                f"{question}\n\n"
                "Agente a utilizar:"
            )

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
        question_lower = cls._normalize_text(question)

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
        summary_signals = [
            "conversacion",
            "conversación",
            "esta sesion",
            "esta sesión",
            "hemos hablado",
            "hemos visto",
            "preguntas realizadas",
            "preguntas anteriores",
            "preguntas pasadas",
            "que hablamos",
            "qué hablamos",
            "que hemos hablado",
            "qué hemos hablado",
            "respuesta anterior",
            "sesiones anteriores",
            "historial conversacional",
            "historial de la sesion",
            "historial de la sesión",
            "memoria historica",
            "memoria histórica",
            "otra sesion",
            "otra sesión",
            "otras sesiones",
            "anteriormente",
            "antes",
            "ya habiamos",
            "ya habíamos",
            "resumen de esta sesion",
            "resumen de esta sesión",
            "resume esta sesion",
            "resume esta sesión",
            "resume la sesion",
            "resume la sesión",
            "resume lo que",
            "resumeme",
            "resumí",
            "resumi",
            "sintesis de lo anterior",
            "síntesis de lo anterior",
        ]
        transactional_signals = [
            "analisis financiero",
            "analizar gasto",
            "auditar cliente",
            "auditoria financiera",
            "bancaria",
            "bancario",
            "caso de fraude",
            "casos de fraude",
            "comercio",
            "comercios",
            "comportamiento de gasto",
            "transacción",
            "transacciones",
            "movimiento bancario",
            "movimientos bancarios",
            "actividad bancaria",
            "cuenta bancaria",
            "cuentas bancarias",
            "estado de cuenta",
            "estados de cuenta",
            "financiero",
            "financiera",
            "gasto",
            "gastos",
            "historial de transacciones",
            "últimas transacciones",
            "último movimiento",
            "últimos movimientos",
            "movimiento",
            "revisa mi cuenta",
            "revisa mi transacción",
            "revisa mi transacciones",
            "perfil financiero",
            "riesgo",
            "sospechoso",
            "sospechosa",
            "fraude",
            "transaccion sospechosa",
            "transacción sospechosa",
            "transacciones sospechosas",
            "transaccion",
            "cliente", 
            "clientes",
            "cuenta",
            "numero de cuenta",
            
        ]

        has_web_signal = any(signal in question_lower for signal in web_signals)
        has_academic_signal = any(signal in question_lower for signal in academic_signals)
        has_summary_signal = any(signal in question_lower for signal in summary_signals)
        has_transactional_signal = any(signal in question_lower for signal in transactional_signals)

        if cls._is_historical_memory_request(question):
            return "summary"

        if has_summary_signal:
            return "summary"

        if has_academic_signal:
            return "rag"
        
        if has_transactional_signal:
            return "transactional"

        if has_web_signal:
            return "web"

        return cls._normalize_decision(raw_decision)

    def _get_rag_agent(self) -> RAGAgent:
        if self.rag_agent is None:
            self.rag_agent = self.rag_agent_factory()

        return self.rag_agent

    def _get_summarizer_agent(self) -> SummarizerAgent:
        if self.summarizer_agent is None:
            self.summarizer_agent = self.summarizer_agent_factory()

        return self.summarizer_agent
    
    def _get_transactional_agent(self) -> TransactionalAgent:
        if self.transactional_agent is None:
            self.transactional_agent = self.transactional_agent_factory()

        return self.transactional_agent

    def _get_web_search_agent(self) -> WebSearchAgent:
        if self.web_search_agent is None:
            self.web_search_agent = self.web_search_agent_factory()

        return self.web_search_agent

    def _lookup_historical_memory(self, question: str, session_id: str) -> dict:
        if not self._is_historical_memory_request(question):
            return {
                "available": True,
                "queried": False,
                "matches_count": 0,
                "has_context": False,
                "scope": "none",
                "formatted_context": "",
                "error": None,
            }

        try:
            context = self.historical_memory_tool.search_context(
                query=question,
                session_id=None,
            )
        except Exception as exc:
            return {
                "available": False,
                "queried": True,
                "matches_count": 0,
                "has_context": False,
                "scope": "global",
                "formatted_context": "",
                "error": str(exc),
            }

        return {
            "available": True,
            "queried": True,
            "matches_count": context["matches_count"],
            "has_context": context["has_context"],
            "scope": context["scope"],
            "formatted_context": context["formatted_context"],
            "error": None,
        }

    @classmethod
    def _is_historical_memory_request(cls, question: str) -> bool:
        question_lower = cls._normalize_text(question)
        signals = [
            "anteriormente",
            "antes",
            "historial conversacional",
            "historial de la sesion",
            "memoria historica",
            "pregunte",
            "pregunta anterior",
            "preguntas anteriores",
            "preguntas pasadas",
            "que pregunte",
            "sesiones anteriores",
            "ya habia",
            "ya habiamos",
            "ya consultamos",
            "ya habiamos consultado",
            "hablamos antes",
            "consultamos antes",
            "consultado antes",
            "en otra sesion",
            "en otra sesión",
            "en otras sesiones",
            "otra sesion",
            "otra sesión",
            "otras sesiones",
            "sesion pasada",
            "sesión pasada",
            "sesiones pasadas",
        ]

        return any(signal in question_lower for signal in signals)

    def _save_historical_memory_turn(
        self,
        session_id: str,
        question: str,
        answer: str,
        agent_selected: str,
        sources: list | None = None,
    ) -> dict:
        try:
            update = self.historical_memory_tool.save_turn(
                session_id=session_id,
                question=question,
                answer=answer,
                agent_selected=agent_selected,
                sources=sources,
            )
            return {
                **update,
                "updated": True,
                "error": None,
            }
        except Exception as exc:
            return {
                "id": None,
                "session_id": session_id,
                "question": question,
                "agent_selected": agent_selected,
                "sources_count": len(sources or []),
                "created_at": None,
                "updated": False,
                "error": str(exc),
            }

    @staticmethod
    def _merge_contexts(*contexts: str) -> str:
        cleaned_contexts = [context.strip() for context in contexts if context and context.strip()]
        if not cleaned_contexts:
            return ""

        return "\n\n".join(cleaned_contexts)

    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text.lower())
        return "".join(
            char for char in normalized if not unicodedata.combining(char)
        )

    @staticmethod
    def _build_decision_reason(agent_selected: str) -> str:
        if agent_selected == "summary":
            return (
                "Gemini clasifico la pregunta como una solicitud de resumen "
                "o sintesis del historial conversacional de la sesion."
            )

        if agent_selected == "web":
            return (
                "Gemini clasifico la pregunta como una consulta que requiere "
                "informacion externa, reciente o disponible en internet."
            )

        if agent_selected == "transactional":
            return (
                "Gemini clasifico la pregunta como una consulta financiera o "
                "transaccional que debe resolverse mediante el agente MCP y la "
                "base PostgreSQL transaccional."
            )

        return (
            "Gemini clasifico la pregunta como una consulta que puede responderse "
            "con los apuntes o documentos del curso, o como una consulta ambigua "
            "donde la politica indica preferir RAG."
        )

    @staticmethod
    def _normalize_session_id(session_id: str | None) -> str:
        normalized = (session_id or "default").strip()
        return normalized or "default"
