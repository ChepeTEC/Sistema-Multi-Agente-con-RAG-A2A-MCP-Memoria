from typing import Any

from src.memory.conversational_memory import ConversationalMemory


class MemoryTool:
    """
    Tool for reading and updating temporal conversational memory.
    """

    TOOL_NAME = "MemoryTool"

    def __init__(
        self,
        memory: ConversationalMemory | None = None,
        max_context_turns: int = 4,
        max_summary_turns: int = 12,
        answer_preview_chars: int = 500,
    ):
        self.memory = memory or ConversationalMemory()
        self.max_context_turns = max_context_turns
        self.max_summary_turns = max_summary_turns
        self.answer_preview_chars = answer_preview_chars

    def get_context(self, session_id: str, limit: int | None = None) -> dict[str, Any]:
        turns = self.memory.get_recent_turns(
            session_id=session_id,
            limit=limit if limit is not None else self.max_context_turns,
        )

        return self._build_context(session_id, turns)

    def get_summary_context(self, session_id: str) -> dict[str, Any]:
        turns = self.memory.get_recent_turns(
            session_id=session_id,
            limit=self.max_summary_turns,
        )

        return self._build_context(session_id, turns)

    def _build_context(self, session_id: str, turns) -> dict[str, Any]:
        return {
            "session_id": session_id,
            "turns_count": len(turns),
            "has_context": bool(turns),
            "formatted_context": self._format_turns(turns),
            "turns": [
                {
                    "question": turn.question,
                    "answer": turn.answer,
                    "agent_selected": turn.agent_selected,
                    "sources_count": len(turn.sources),
                    "created_at": turn.created_at,
                }
                for turn in turns
            ],
        }

    def save_turn(
        self,
        session_id: str,
        question: str,
        answer: str,
        agent_selected: str,
        sources: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        turn = self.memory.add_turn(
            session_id=session_id,
            question=question,
            answer=answer,
            agent_selected=agent_selected,
            sources=sources,
        )

        return {
            "session_id": session_id,
            "question": turn.question,
            "agent_selected": turn.agent_selected,
            "sources_count": len(turn.sources),
            "created_at": turn.created_at,
        }

    def _format_turns(self, turns) -> str:
        if not turns:
            return ""

        formatted_turns = []

        for index, turn in enumerate(turns, start=1):
            answer_preview = turn.answer[:self.answer_preview_chars].strip()
            formatted_turns.append(
                f"[Turno {index} | Agente: {turn.agent_selected}]\n"
                f"Usuario: {turn.question}\n"
                f"Asistente: {answer_preview}"
            )

        return "\n\n".join(formatted_turns)
