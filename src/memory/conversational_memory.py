from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any


@dataclass
class ConversationTurn:
    question: str
    answer: str
    agent_selected: str
    sources: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ConversationalMemory:
    """
    In-memory session storage for short conversational context.

    This implements temporal memory only. It is intentionally small and
    swappable so historical persistent memory can reuse the same tool contract.
    """

    def __init__(self, max_turns_per_session: int = 12):
        if max_turns_per_session < 1:
            raise ValueError("max_turns_per_session debe ser mayor que cero.")

        self.max_turns_per_session = max_turns_per_session
        self._sessions: dict[str, deque[ConversationTurn]] = {}
        self._lock = RLock()

    def add_turn(
        self,
        session_id: str,
        question: str,
        answer: str,
        agent_selected: str,
        sources: list[dict[str, Any]] | None = None,
    ) -> ConversationTurn:
        normalized_session_id = self._normalize_session_id(session_id)
        turn = ConversationTurn(
            question=question.strip(),
            answer=answer.strip(),
            agent_selected=agent_selected.strip(),
            sources=sources or [],
        )

        with self._lock:
            session = self._sessions.setdefault(
                normalized_session_id,
                deque(maxlen=self.max_turns_per_session),
            )
            session.append(turn)

        return turn

    def get_recent_turns(
        self,
        session_id: str,
        limit: int | None = None,
    ) -> list[ConversationTurn]:
        normalized_session_id = self._normalize_session_id(session_id)

        with self._lock:
            turns = list(self._sessions.get(normalized_session_id, []))

        if limit is None:
            return turns

        return turns[-max(0, limit):]

    def clear_session(self, session_id: str) -> None:
        normalized_session_id = self._normalize_session_id(session_id)

        with self._lock:
            self._sessions.pop(normalized_session_id, None)

    @staticmethod
    def _normalize_session_id(session_id: str | None) -> str:
        normalized = (session_id or "default").strip()
        return normalized or "default"
