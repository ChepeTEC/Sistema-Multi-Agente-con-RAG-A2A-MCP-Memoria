from time import perf_counter
from typing import Any

from src.config.settings import settings


class GeminiClient:
    """Text generation client backed by the Gemini API."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        client: Any | None = None
    ):
        self.model = (model or settings.RAG_LLM_MODEL).strip()
        self.api_key = (
            api_key
            or settings.GEMINI_API_KEY
            or settings.GOOGLE_API_KEY
        )

        if not self.model:
            raise ValueError("El modelo LLM no puede estar vacio.")

        if client is not None:
            self.client = client
            return

        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY o GOOGLE_API_KEY no esta configurada. "
                "Agreguela al archivo .env antes de usar GeminiClient."
            )

        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError(
                "La dependencia google-genai no esta instalada. "
                "Ejecute: pip install -r requirements.txt"
            ) from exc

        self.client = genai.Client(api_key=self.api_key)

    def generate(
        self,
        prompt: str,
        instructions: str | None = None
    ) -> dict:
        prompt = prompt.strip() if prompt else ""
        instructions = instructions.strip() if instructions else None

        if not prompt:
            raise ValueError("El prompt del LLM no puede estar vacio.")

        try:
            from google.genai import types
        except ImportError as exc:
            raise RuntimeError(
                "La dependencia google-genai no esta instalada. "
                "Ejecute: pip install -r requirements.txt"
            ) from exc

        started_at = perf_counter()
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=instructions
            )
        )
        duration_ms = round((perf_counter() - started_at) * 1000, 2)

        return {
            "text": response.text,
            "provider": "gemini",
            "model": self.model,
            "response_id": getattr(response, "response_id", None),
            "duration_ms": duration_ms
        }
