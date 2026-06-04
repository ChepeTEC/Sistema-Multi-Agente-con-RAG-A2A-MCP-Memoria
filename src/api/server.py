from functools import lru_cache

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
    orchestrator = get_orchestrator()
    return orchestrator.answer(request.question)
