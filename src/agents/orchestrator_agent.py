from time import perf_counter
from src.agents.rag_agent import RAGAgent
from src.agents.web_search_agent import WebSearchAgent
from src.config.settings import settings
from src.llm.base import LLMClient
from src.llm.gemini_client import GeminiClient


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
    ):
        self.rag_agent = rag_agent or RAGAgent()
        self.web_search_agent = web_search_agent or WebSearchAgent()
        self.llm_client = llm_client or GeminiClient(
            model=settings.ORCHESTRATOR_LLM_MODEL
        )

    def answer(self, question: str) -> dict:
        question = question.strip() if question else ""

        if not question:
            raise ValueError("La pregunta no puede estar vacia.")

        total_started_at = perf_counter()
        decision_data = self._decide_agent(question)
        agent_selected = decision_data["agent_selected"]
        decision_reason = self._build_decision_reason(agent_selected)

        if agent_selected == "web":
            agent_result = self.web_search_agent.answer(
                question=question,
                justification=decision_reason,
            )
        else:
            agent_result = self.rag_agent.answer(question)

        total_duration_ms = round((perf_counter() - total_started_at) * 1000, 2)

        return {
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

    def _decide_agent(self, question: str) -> dict:
        decision_started_at = perf_counter()
        llm_result = self.llm_client.generate(
            prompt=self._build_decision_prompt(question),
            instructions=self._build_decision_instructions(),
        )
        measured_duration_ms = round((perf_counter() - decision_started_at) * 1000, 2)

        raw_decision = str(llm_result.get("text", "")).strip()
        agent_selected = self._normalize_decision(raw_decision)

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
            "Si la pregunta puede responderse con apuntes o documentos del curso, "
            "elige rag. Si requiere informacion externa, reciente o de internet, "
            "elige web. Si existe duda, elige rag. Responde exclusivamente con "
            "una palabra: rag o web."
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
