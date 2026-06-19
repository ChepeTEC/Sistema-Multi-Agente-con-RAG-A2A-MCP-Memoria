from typing import Any

from src.memory.historical_memory import HistoricalMemory, HistoricalTurn


class HistoricalMemoryTool:
    """
    Tool for persistent historical conversational memory.
    """

    TOOL_NAME = "HistoricalMemoryTool"

    def __init__(
        self,
        memory: HistoricalMemory | None = None,
        max_search_results: int = 8,
        answer_preview_chars: int = 700,
    ):
        self.memory = memory or HistoricalMemory()
        self.max_search_results = max_search_results
        self.answer_preview_chars = answer_preview_chars

    def save_turn(
        self,
        session_id: str,
        question: str,
        answer: str,
        agent_selected: str,
        sources: list[Any] | None = None,
    ) -> dict[str, Any]:
        turn = self.memory.add_turn(
            session_id=session_id,
            question=question,
            answer=answer,
            agent_selected=agent_selected,
            sources=sources,
        )

        return {
            "id": turn.id,
            "session_id": turn.session_id,
            "question": turn.question,
            "agent_selected": turn.agent_selected,
            "sources_count": len(turn.sources),
            "created_at": turn.created_at,
        }

    def search_context(
        self,
        query: str,
        session_id: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        turns = self.memory.search_turns(
            query=query,
            session_id=session_id,
            limit=limit if limit is not None else self.max_search_results,
        )

        return self._build_context(
            query=query,
            session_id=session_id,
            turns=turns,
            scope="session" if session_id else "global",
        )

    def recent_context(
        self,
        session_id: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        turns = self.memory.get_recent_turns(
            session_id=session_id,
            limit=limit if limit is not None else self.max_search_results,
        )

        return self._build_context(
            query="",
            session_id=session_id,
            turns=turns,
            scope="session" if session_id else "global",
        )

    def save_summary(self, session_id: str, summary: str) -> dict[str, Any]:
        return self.memory.save_session_summary(session_id=session_id, summary=summary)

    def get_summary(self, session_id: str) -> dict[str, Any] | None:
        return self.memory.get_session_summary(session_id=session_id)

    def _build_context(
        self,
        query: str,
        session_id: str | None,
        turns: list[HistoricalTurn],
        scope: str,
    ) -> dict[str, Any]:
        return {
            "query": query,
            "session_id": session_id,
            "scope": scope,
            "matches_count": len(turns),
            "has_context": bool(turns),
            "formatted_context": self._format_turns(turns),
            "turns": [
                {
                    "id": turn.id,
                    "session_id": turn.session_id,
                    "question": turn.question,
                    "answer": turn.answer[:self.answer_preview_chars],
                    "agent_selected": turn.agent_selected,
                    "sources_count": len(turn.sources),
                    "created_at": turn.created_at,
                }
                for turn in turns
            ],
        }

    def _format_turns(self, turns: list[HistoricalTurn]) -> str:
        if not turns:
            return ""

        formatted_turns = []
        for index, turn in enumerate(turns, start=1):
            answer_preview = turn.answer[:self.answer_preview_chars].strip()
            formatted_turns.append(
                f"[Historial {index} | Sesion: {turn.session_id} | "
                f"Agente: {turn.agent_selected} | Fecha: {turn.created_at}]\n"
                f"Usuario: {turn.question}\n"
                f"Asistente: {answer_preview}"
            )

        return "\n\n".join(formatted_turns)
