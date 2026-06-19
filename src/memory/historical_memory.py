import json
import sqlite3
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any


@dataclass
class HistoricalTurn:
    id: int | None
    session_id: str
    question: str
    answer: str
    agent_selected: str
    sources: list[Any] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class HistoricalMemory:
    """
    SQLite-backed persistent memory for previous conversations.

    This storage is intentionally separate from the temporal in-memory
    conversation context so session continuity can stay fast and small while
    historical recall survives backend restarts.
    """

    def __init__(self, db_path: str | Path | None = None):
        base_dir = Path(__file__).resolve().parents[2]
        self.db_path = Path(db_path) if db_path else base_dir / "data" / "memory" / "history.sqlite3"
        self.fallback_db_path: Path | None = None
        self.initialization_error: str | None = None
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        try:
            self._initialize()
        except sqlite3.Error as exc:
            if db_path is not None:
                raise

            self.initialization_error = str(exc)
            self.fallback_db_path = self.db_path.with_name("history_runtime.sqlite3")
            self.db_path = self.fallback_db_path
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._initialize()

    def add_turn(
        self,
        session_id: str,
        question: str,
        answer: str,
        agent_selected: str,
        sources: list[Any] | None = None,
    ) -> HistoricalTurn:
        normalized_session_id = self._normalize_session_id(session_id)
        created_at = datetime.now(timezone.utc).isoformat()
        sources_json = json.dumps(sources or [], ensure_ascii=False)

        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sessions (id, created_at, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET updated_at = excluded.updated_at;
                """,
                (normalized_session_id, created_at, created_at),
            )
            cursor = conn.execute(
                """
                INSERT INTO turns (
                    session_id, question, answer, agent_selected,
                    sources_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    normalized_session_id,
                    question.strip(),
                    answer.strip(),
                    agent_selected.strip(),
                    sources_json,
                    created_at,
                ),
            )
            turn_id = cursor.lastrowid

        return HistoricalTurn(
            id=turn_id,
            session_id=normalized_session_id,
            question=question.strip(),
            answer=answer.strip(),
            agent_selected=agent_selected.strip(),
            sources=sources or [],
            created_at=created_at,
        )

    def search_turns(
        self,
        query: str,
        session_id: str | None = None,
        limit: int = 8,
    ) -> list[HistoricalTurn]:
        terms = self._search_terms(query)
        if not terms:
            return self.get_recent_turns(session_id=session_id, limit=limit)

        where_parts = []
        params: list[Any] = []

        if session_id:
            where_parts.append("session_id = ?")
            params.append(self._normalize_session_id(session_id))

        searchable = "lower(question || ' ' || answer || ' ' || agent_selected)"
        term_clauses = []
        for term in terms:
            term_clauses.append(f"{searchable} LIKE ?")
            params.append(f"%{term}%")

        where_parts.append("(" + " OR ".join(term_clauses) + ")")
        params.append(max(1, limit))
        where_clause = " AND ".join(where_parts)

        with self._lock, self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, session_id, question, answer, agent_selected,
                       sources_json, created_at
                FROM turns
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ?;
                """,
                params,
            ).fetchall()

        return [self._row_to_turn(row) for row in rows]

    def get_recent_turns(
        self,
        session_id: str | None = None,
        limit: int = 8,
    ) -> list[HistoricalTurn]:
        params: list[Any] = []
        where_clause = ""

        if session_id:
            where_clause = "WHERE session_id = ?"
            params.append(self._normalize_session_id(session_id))

        params.append(max(1, limit))

        with self._lock, self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, session_id, question, answer, agent_selected,
                       sources_json, created_at
                FROM turns
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ?;
                """,
                params,
            ).fetchall()

        return [self._row_to_turn(row) for row in rows]

    def save_session_summary(self, session_id: str, summary: str) -> dict[str, Any]:
        normalized_session_id = self._normalize_session_id(session_id)
        updated_at = datetime.now(timezone.utc).isoformat()

        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO session_summaries (session_id, summary, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    summary = excluded.summary,
                    updated_at = excluded.updated_at;
                """,
                (normalized_session_id, summary.strip(), updated_at),
            )

        return {
            "session_id": normalized_session_id,
            "updated_at": updated_at,
            "summary_chars": len(summary.strip()),
        }

    def get_session_summary(self, session_id: str) -> dict[str, Any] | None:
        normalized_session_id = self._normalize_session_id(session_id)

        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT session_id, summary, updated_at
                FROM session_summaries
                WHERE session_id = ?;
                """,
                (normalized_session_id,),
            ).fetchone()

        if row is None:
            return None

        return {
            "session_id": row["session_id"],
            "summary": row["summary"],
            "updated_at": row["updated_at"],
        }

    def _initialize(self) -> None:
        with self._lock, self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    agent_selected TEXT NOT NULL,
                    sources_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                );

                CREATE INDEX IF NOT EXISTS idx_turns_session_created
                    ON turns(session_id, created_at);

                CREATE INDEX IF NOT EXISTS idx_turns_created
                    ON turns(created_at);

                CREATE TABLE IF NOT EXISTS session_summaries (
                    session_id TEXT PRIMARY KEY,
                    summary TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=MEMORY;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    @staticmethod
    def _normalize_session_id(session_id: str | None) -> str:
        normalized = (session_id or "default").strip()
        return normalized or "default"

    @staticmethod
    def _search_terms(query: str) -> list[str]:
        normalized = HistoricalMemory._normalize_text(query)
        terms = [
            token.strip(".,;:()[]{}!¡\"'")
            for token in normalized.split()
        ]
        ignored = {
            "anterior",
            "anteriormente",
            "antes",
            "consulta",
            "consultado",
            "consultamos",
            "dime",
            "habia",
            "habiamos",
            "historial",
            "pregunte",
            "preguntas",
            "que",
            "quiero",
            "realizadas",
            "sesion",
            "sesiones",
            "sobre",
        }
        return [
            term
            for term in terms
            if len(term) >= 4 and term not in ignored
        ][:6]

    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text.lower())
        ascii_text = "".join(
            char for char in normalized if not unicodedata.combining(char)
        )
        return ascii_text.replace("¿", " ").replace("?", " ").replace("!", " ")

    @staticmethod
    def _row_to_turn(row: sqlite3.Row) -> HistoricalTurn:
        try:
            sources = json.loads(row["sources_json"])
        except json.JSONDecodeError:
            sources = []

        return HistoricalTurn(
            id=row["id"],
            session_id=row["session_id"],
            question=row["question"],
            answer=row["answer"],
            agent_selected=row["agent_selected"],
            sources=sources,
            created_at=row["created_at"],
        )
