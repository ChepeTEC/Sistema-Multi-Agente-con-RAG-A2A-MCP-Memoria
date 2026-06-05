import os
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv()


class LangfuseTracer:
    """
    Wrapper sencillo para Langfuse.
    Compatible con versiones nuevas del SDK de Langfuse.

    Si Langfuse no está configurado o falla, el sistema sigue funcionando.
    """

    def __init__(self) -> None:
        self.enabled = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"
        self.client = None

        if not self.enabled:
            return

        try:
            from langfuse import get_client

            public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
            secret_key = os.getenv("LANGFUSE_SECRET_KEY")
            base_url = (
                os.getenv("LANGFUSE_BASE_URL")
                or os.getenv("LANGFUSE_HOST")
                or "https://us.cloud.langfuse.com"
            )

            if not public_key or not secret_key:
                print("[Langfuse] No se encontraron keys. Observabilidad desactivada.")
                self.enabled = False
                return

            os.environ["LANGFUSE_PUBLIC_KEY"] = public_key
            os.environ["LANGFUSE_SECRET_KEY"] = secret_key
            os.environ["LANGFUSE_BASE_URL"] = base_url

            self.client = get_client()

            if hasattr(self.client, "auth_check") and not self.client.auth_check():
                print("[Langfuse] No se pudo autenticar. Revise las keys y el host.")
                self.enabled = False
                self.client = None
                return

            print("[Langfuse] Observabilidad activada.")

        except Exception as exc:
            print(f"[Langfuse] No se pudo inicializar: {exc}")
            self.enabled = False
            self.client = None

    def create_trace(
        self,
        name: str,
        input_data: Any,
        metadata: Optional[dict[str, Any]] = None,
    ):
        if not self.enabled or self.client is None:
            return None

        try:
            context_manager = self.client.start_as_current_observation(
                as_type="span",
                name=name,
            )
            observation = context_manager.__enter__()
            self._safe_update(
                observation,
                input=input_data,
                metadata=metadata or {},
            )
            return {
                "context_manager": context_manager,
                "observation": observation,
                "closed": False,
            }
        except Exception as exc:
            print(f"[Langfuse] Error creando trace: {exc}")
            return None

    def create_span(
        self,
        trace,
        name: str,
        input_data: Any = None,
        output_data: Any = None,
        metadata: Optional[dict[str, Any]] = None,
    ):
        if trace is None or not self.enabled or self.client is None:
            return None

        try:
            with self.client.start_as_current_observation(
                as_type="span",
                name=name,
            ) as span:
                self._safe_update(
                    span,
                    input=input_data,
                    output=output_data,
                    metadata=metadata or {},
                )
                return span
        except Exception as exc:
            print(f"[Langfuse] Error creando span '{name}': {exc}")
            return None

    def create_generation(
        self,
        trace,
        name: str,
        model: str,
        prompt: str,
        response: str,
        metadata: Optional[dict[str, Any]] = None,
    ):
        if trace is None or not self.enabled or self.client is None:
            return None

        try:
            with self.client.start_as_current_observation(
                as_type="generation",
                name=name,
                model=model,
            ) as generation:
                self._safe_update(
                    generation,
                    input=prompt,
                    output=response,
                    metadata=metadata or {},
                )
                return generation
        except Exception as exc:
            print(f"[Langfuse] Error creando generation '{name}': {exc}")
            return None

    def update_trace_output(self, trace, output_data: Any):
        if trace is None:
            return

        try:
            observation = trace.get("observation")
            self._safe_update(observation, output=output_data)
        except Exception as exc:
            print(f"[Langfuse] Error actualizando trace: {exc}")

    def close_trace(self, trace):
        if trace is None or trace.get("closed"):
            return

        try:
            context_manager = trace.get("context_manager")
            context_manager.__exit__(None, None, None)
            trace["closed"] = True
        except Exception as exc:
            print(f"[Langfuse] Error cerrando trace: {exc}")

    def flush(self):
        if not self.enabled or self.client is None:
            return

        try:
            self.client.flush()
        except Exception as exc:
            print(f"[Langfuse] Error haciendo flush: {exc}")

    def _safe_update(self, observation, **kwargs):
        if observation is None:
            return

        clean_kwargs = {
            key: value
            for key, value in kwargs.items()
            if value is not None
        }

        try:
            observation.update(**clean_kwargs)
        except TypeError:
            for key, value in clean_kwargs.items():
                try:
                    observation.update(**{key: value})
                except Exception:
                    pass


langfuse_tracer = LangfuseTracer()