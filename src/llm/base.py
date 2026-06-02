from typing import Protocol


class LLMClient(Protocol):
    """Common contract for text generation providers."""

    def generate(
        self,
        prompt: str,
        instructions: str | None = None
    ) -> dict:
        """Generate a text response using provider-specific infrastructure."""
        ...
