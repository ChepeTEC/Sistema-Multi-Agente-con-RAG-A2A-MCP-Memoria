import os
from dotenv import load_dotenv
from google import genai


load_dotenv()


class GeminiClient:
    """
    Cliente simple para generar respuestas usando Gemini con el SDK nuevo.
    """

    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        self.model_name = os.getenv("RAG_LLM_MODEL", "gemini-2.5-flash")

        if not api_key:
            raise ValueError("Falta GOOGLE_API_KEY en el archivo .env")

        self.client = genai.Client(api_key=api_key)

    def generate(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )

        if not response or not response.text:
            return "No fue posible generar una respuesta con el modelo."

        return response.text.strip()