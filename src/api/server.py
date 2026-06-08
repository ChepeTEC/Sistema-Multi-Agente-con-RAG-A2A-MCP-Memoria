from functools import lru_cache
import traceback

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.agents.orchestrator_agent import OrchestratorAgent


class ChatRequest(BaseModel):
    question: str


app = FastAPI(title="Sistema Multi-Agente API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def get_orchestrator() -> OrchestratorAgent:
    return OrchestratorAgent()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict:
    try:
        orchestrator = get_orchestrator()
        return orchestrator.answer(request.question)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=build_error_response(exc),
        )


def build_error_response(exc: Exception) -> dict:
    detail = "".join(
        traceback.format_exception(type(exc), exc, exc.__traceback__)
    )
    detail_lower = detail.lower()

    if (
        "embedding" in detail_lower
        or "sentence_transformer" in detail_lower
        or "huggingface" in detail_lower
        or "all-minilm-l6-v2" in detail_lower
    ):
        return {
            "error": True,
            "component": "rag_embeddings",
            "message": (
                "No se pudo cargar el modelo de embeddings. "
                "Descargue/cachee sentence-transformers/all-MiniLM-L6-v2 "
                "antes de usar RAG."
            ),
            "detail": str(exc),
        }

    if "chromadb" in detail_lower or "vector_store" in detail_lower:
        return {
            "error": True,
            "component": "rag_vector_store",
            "message": "No se pudo consultar la base vectorial de RAG.",
            "detail": str(exc),
        }

    return {
        "error": True,
        "component": "backend",
        "message": "Ocurrio un error interno procesando la pregunta.",
        "detail": str(exc),
    }
