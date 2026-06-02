from time import perf_counter
from typing import Any

from src.config.settings import settings


class WebSearchTool:
    """Controlled web search access through Tavily."""

    def __init__(
        self,
        api_key: str | None = None,
        client: Any | None = None
    ):
        self.api_key = api_key or settings.TAVILY_API_KEY

        if client is not None:
            self.client = client
            return

        if not self.api_key:
            raise ValueError(
                "TAVILY_API_KEY no esta configurada. "
                "Agreguela al archivo .env antes de usar WebSearchTool."
            )

        try:
            from tavily import TavilyClient
        except ImportError as exc:
            raise RuntimeError(
                "La dependencia tavily-python no esta instalada. "
                "Ejecute: pip install -r requirements.txt"
            ) from exc

        self.client = TavilyClient(api_key=self.api_key)

    def search(
        self,
        query: str,
        justification: str,
        max_results: int = 5,
        search_depth: str = "basic"
    ) -> dict:
        query = query.strip() if query else ""
        justification = justification.strip() if justification else ""

        if not query:
            raise ValueError("La consulta web no puede estar vacia.")

        if not justification:
            raise ValueError("La busqueda web requiere una justificacion.")

        if not 1 <= max_results <= 10:
            raise ValueError("max_results debe estar entre 1 y 10.")

        if search_depth not in {"basic", "advanced"}:
            raise ValueError("search_depth debe ser 'basic' o 'advanced'.")

        started_at = perf_counter()
        response = self.client.search(
            query=query,
            max_results=max_results,
            search_depth=search_depth,
            include_answer=False
        )
        duration_ms = round((perf_counter() - started_at) * 1000, 2)

        return {
            "query": query,
            "justification": justification,
            "provider": "tavily",
            "request_id": response.get("request_id"),
            "results": [
                self._normalize_result(result)
                for result in response.get("results", [])
            ],
            "duration_ms": duration_ms
        }

    @staticmethod
    def _normalize_result(result: dict) -> dict:
        return {
            "title": result.get("title", ""),
            "url": result.get("url", ""),
            "content": result.get("content", ""),
            "score": result.get("score"),
            "published_date": result.get("published_date")
        }
