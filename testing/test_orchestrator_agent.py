import unittest
from unittest.mock import patch

from src.agents.orchestrator_agent import OrchestratorAgent
from src.config.settings import settings
from src.memory.conversational_memory import ConversationalMemory
from src.tools.memory_tool import MemoryTool


class FakeDecisionLLM:
    def __init__(self, decision: str):
        self.decision = decision
        self.calls = []

    def generate(self, prompt: str, instructions: str | None = None) -> dict:
        self.calls.append({
            "prompt": prompt,
            "instructions": instructions,
        })
        return {
            "text": self.decision,
            "provider": "gemini",
            "model": "gemini-test",
            "response_id": "decision-response",
            "duration_ms": 7.5,
        }


class FakeRAGAgent:
    def __init__(self):
        self.questions = []
        self.conversation_contexts = []

    def answer(self, question: str, conversation_context: str | None = None) -> dict:
        self.questions.append(question)
        self.conversation_contexts.append(conversation_context)
        return {
            "agent": "RAGAgent",
            "answer": "Respuesta desde RAG.",
            "sources": [
                {
                    "file": "apuntes.pdf",
                    "page": 3,
                }
            ],
            "chunks": [],
        }


class FakeWebSearchAgent:
    def __init__(self):
        self.calls = []

    def answer(
        self,
        question: str,
        justification: str,
        conversation_context: str | None = None,
    ) -> dict:
        self.calls.append({
            "question": question,
            "justification": justification,
            "conversation_context": conversation_context,
        })
        return {
            "agent": "WebSearchAgent",
            "answer": "Respuesta desde Web.",
            "sources": [
                {
                    "title": "Fuente web",
                    "url": "https://example.com",
                }
            ],
            "trace": {
                "query": question,
                "urls": ["https://example.com"],
            },
        }


class FakeSummarizerAgent:
    def __init__(self):
        self.calls = []

    def answer(
        self,
        question: str,
        conversation_context: str | None = None,
    ) -> dict:
        self.calls.append({
            "question": question,
            "conversation_context": conversation_context,
        })
        return {
            "agent": "SummarizerAgent",
            "answer": "Resumen desde memoria.",
            "sources": [],
            "trace": {
                "has_conversation_context": bool(conversation_context),
            },
        }


class FakeTransactionalAgent:
    def __init__(self):
        self.calls = []

    def answer(
        self,
        question: str,
        conversation_context: str | None = None,
    ) -> dict:
        self.calls.append({
            "question": question,
            "conversation_context": conversation_context,
        })
        return {
            "agent": "TransactionalAgent",
            "answer": "Respuesta desde MCP transaccional.",
            "sources": ["PostgreSQL Database via MCP"],
            "trace": {
                "duration_ms": 12.5,
            },
        }


class FakeHistoricalMemoryTool:
    TOOL_NAME = "HistoricalMemoryTool"

    def __init__(self, formatted_context: str = ""):
        self.formatted_context = formatted_context
        self.search_calls = []
        self.saved_turns = []

    def search_context(
        self,
        query: str,
        session_id: str | None = None,
        limit: int | None = None,
    ) -> dict:
        self.search_calls.append({
            "query": query,
            "session_id": session_id,
            "limit": limit,
        })
        return {
            "query": query,
            "session_id": session_id,
            "scope": "global",
            "matches_count": 1 if self.formatted_context else 0,
            "has_context": bool(self.formatted_context),
            "formatted_context": self.formatted_context,
            "turns": [],
        }

    def save_turn(
        self,
        session_id: str,
        question: str,
        answer: str,
        agent_selected: str,
        sources: list | None = None,
    ) -> dict:
        self.saved_turns.append({
            "session_id": session_id,
            "question": question,
            "answer": answer,
            "agent_selected": agent_selected,
            "sources": sources or [],
        })
        return {
            "id": len(self.saved_turns),
            "session_id": session_id,
            "question": question,
            "agent_selected": agent_selected,
            "sources_count": len(sources or []),
            "created_at": "2026-06-18T00:00:00+00:00",
        }


class FailingHistoricalMemoryTool(FakeHistoricalMemoryTool):
    def search_context(
        self,
        query: str,
        session_id: str | None = None,
        limit: int | None = None,
    ) -> dict:
        raise RuntimeError("historical search unavailable")

    def save_turn(
        self,
        session_id: str,
        question: str,
        answer: str,
        agent_selected: str,
        sources: list | None = None,
    ) -> dict:
        raise RuntimeError("historical save unavailable")


def exploding_rag_factory():
    raise RuntimeError("RAG no debio instanciarse")


class OrchestratorAgentTests(unittest.TestCase):
    def test_routes_to_rag_when_gemini_selects_rag(self):
        rag_agent = FakeRAGAgent()
        web_agent = FakeWebSearchAgent()
        llm_client = FakeDecisionLLM("rag")
        orchestrator = OrchestratorAgent(
            rag_agent=rag_agent,
            web_search_agent=web_agent,
            llm_client=llm_client,
        )

        result = orchestrator.answer("Que es overfitting segun los apuntes?")

        self.assertEqual(result["agent_selected"], "rag")
        self.assertEqual(result["answer"], "Respuesta desde RAG.")
        self.assertEqual(result["sources"][0]["file"], "apuntes.pdf")
        self.assertEqual(rag_agent.questions, ["Que es overfitting segun los apuntes?"])
        self.assertEqual(web_agent.calls, [])
        self.assertEqual(result["trace"]["decision_model"], "gemini-test")
        self.assertEqual(result["trace"]["decision_duration_ms"], 7.5)
        self.assertEqual(result["trace"]["delegated_agent"], "RAGAgent")
        self.assertIn("exclusivamente", llm_client.calls[0]["instructions"])

    def test_default_decision_client_uses_orchestrator_model(self):
        rag_agent = FakeRAGAgent()
        web_agent = FakeWebSearchAgent()
        llm_client = FakeDecisionLLM("rag")

        with patch(
            "src.agents.orchestrator_agent.GeminiClient",
            return_value=llm_client,
        ) as gemini_client:
            orchestrator = OrchestratorAgent(
                rag_agent=rag_agent,
                web_search_agent=web_agent,
            )

        orchestrator.answer("Que es aprendizaje supervisado?")

        gemini_client.assert_called_once_with(
            model=settings.ORCHESTRATOR_LLM_MODEL
        )
        self.assertEqual(rag_agent.questions, ["Que es aprendizaje supervisado?"])

    def test_routes_to_web_when_gemini_selects_web(self):
        rag_agent = FakeRAGAgent()
        web_agent = FakeWebSearchAgent()
        orchestrator = OrchestratorAgent(
            rag_agent=rag_agent,
            web_search_agent=web_agent,
            llm_client=FakeDecisionLLM("web"),
        )

        result = orchestrator.answer("Cuales son las noticias recientes de Gemini?")

        self.assertEqual(result["agent_selected"], "web")
        self.assertEqual(result["answer"], "Respuesta desde Web.")
        self.assertEqual(result["sources"][0]["url"], "https://example.com")
        self.assertEqual(rag_agent.questions, [])
        self.assertEqual(web_agent.calls[0]["question"], "Cuales son las noticias recientes de Gemini?")
        self.assertIn("internet", web_agent.calls[0]["justification"])
        self.assertEqual(result["trace"]["delegated_agent"], "WebSearchAgent")
        self.assertEqual(result["trace"]["delegated_trace"]["urls"], ["https://example.com"])

    def test_routes_to_transactional_when_gemini_selects_transactional(self):
        transactional_agent = FakeTransactionalAgent()
        orchestrator = OrchestratorAgent(
            rag_agent=FakeRAGAgent(),
            web_search_agent=FakeWebSearchAgent(),
            transactional_agent=transactional_agent,
            llm_client=FakeDecisionLLM("transactional"),
        )

        result = orchestrator.answer("Analiza el perfil financiero del cliente 1.")

        self.assertEqual(result["agent_selected"], "transactional")
        self.assertEqual(result["answer"], "Respuesta desde MCP transaccional.")
        self.assertEqual(result["trace"]["delegated_agent"], "TransactionalAgent")
        self.assertIn("MCP", result["decision_reason"])
        self.assertEqual(
            transactional_agent.calls[0]["question"],
            "Analiza el perfil financiero del cliente 1.",
        )

    def test_transactional_signals_are_forced_to_transactional_before_web(self):
        questions = [
            "Busca las transacciones del cliente 1.",
            "Muestrame los movimientos bancarios del cliente 3.",
            "Analiza el comportamiento de gasto del cliente 3.",
            "Existen patrones sospechosos de fraude?",
            "Cual es el riesgo del comercio Casino Online?",
        ]

        for question in questions:
            with self.subTest(question=question):
                transactional_agent = FakeTransactionalAgent()
                web_agent = FakeWebSearchAgent()
                orchestrator = OrchestratorAgent(
                    rag_agent=FakeRAGAgent(),
                    web_search_agent=web_agent,
                    transactional_agent=transactional_agent,
                    llm_client=FakeDecisionLLM("web"),
                )

                result = orchestrator.answer(question)

                self.assertEqual(result["agent_selected"], "transactional")
                self.assertEqual(result["trace"]["delegated_agent"], "TransactionalAgent")
                self.assertEqual(web_agent.calls, [])
                self.assertEqual(transactional_agent.calls[0]["question"], question)

    def test_transaction_history_request_still_routes_to_transactional(self):
        transactional_agent = FakeTransactionalAgent()
        historical_memory_tool = FakeHistoricalMemoryTool(
            formatted_context="Usuario: Antes hablamos de CNN."
        )
        orchestrator = OrchestratorAgent(
            rag_agent=FakeRAGAgent(),
            summarizer_agent=FakeSummarizerAgent(),
            web_search_agent=FakeWebSearchAgent(),
            transactional_agent=transactional_agent,
            llm_client=FakeDecisionLLM("summary"),
            historical_memory_tool=historical_memory_tool,
        )

        result = orchestrator.answer("Muestrame el historial de transacciones del cliente 1.")

        self.assertEqual(result["agent_selected"], "transactional")
        self.assertEqual(result["trace"]["delegated_agent"], "TransactionalAgent")
        self.assertEqual(historical_memory_tool.search_calls, [])
        self.assertEqual(transactional_agent.calls[0]["question"], "Muestrame el historial de transacciones del cliente 1.")

    def test_previous_transactional_question_routes_to_historical_summary(self):
        transactional_agent = FakeTransactionalAgent()
        summarizer_agent = FakeSummarizerAgent()
        historical_memory_tool = FakeHistoricalMemoryTool(
            formatted_context=(
                "[Historial 1 | Sesion: old | Agente: transactional]\n"
                "Usuario: Existen transacciones sospechosas?\n"
                "Asistente: Se revisaron casos de fraude via MCP."
            )
        )
        orchestrator = OrchestratorAgent(
            rag_agent=FakeRAGAgent(),
            summarizer_agent=summarizer_agent,
            web_search_agent=FakeWebSearchAgent(),
            transactional_agent=transactional_agent,
            llm_client=FakeDecisionLLM("transactional"),
            historical_memory_tool=historical_memory_tool,
        )

        result = orchestrator.answer("Ya habiamos consultado transacciones sospechosas hoy?")

        self.assertEqual(result["agent_selected"], "summary")
        self.assertEqual(result["trace"]["delegated_agent"], "SummarizerAgent")
        self.assertEqual(result["trace"]["historical_memory"]["queried"], True)
        self.assertEqual(result["trace"]["historical_memory"]["matches"], 1)
        self.assertEqual(transactional_agent.calls, [])
        self.assertIn("transacciones sospechosas", summarizer_agent.calls[0]["conversation_context"])

    def test_other_sessions_question_uses_historical_memory(self):
        summarizer_agent = FakeSummarizerAgent()
        historical_memory_tool = FakeHistoricalMemoryTool(
            formatted_context=(
                "[Historial 1 | Sesion: old | Agente: rag]\n"
                "Usuario: Que es una CNN?\n"
                "Asistente: Una CNN es una red neuronal convolucional."
            )
        )
        orchestrator = OrchestratorAgent(
            rag_agent=FakeRAGAgent(),
            summarizer_agent=summarizer_agent,
            web_search_agent=FakeWebSearchAgent(),
            llm_client=FakeDecisionLLM("rag"),
            historical_memory_tool=historical_memory_tool,
        )

        result = orchestrator.answer("que he preguntado en otras sesiones sobre cnn")

        self.assertEqual(result["agent_selected"], "summary")
        self.assertEqual(result["trace"]["historical_memory"]["queried"], True)
        self.assertEqual(result["trace"]["historical_memory"]["scope"], "global")
        self.assertEqual(historical_memory_tool.search_calls[0]["session_id"], None)
        self.assertIn("Que es una CNN?", summarizer_agent.calls[0]["conversation_context"])

    def test_historical_memory_failure_does_not_break_rag_route(self):
        rag_agent = FakeRAGAgent()
        orchestrator = OrchestratorAgent(
            rag_agent=rag_agent,
            summarizer_agent=FakeSummarizerAgent(),
            web_search_agent=FakeWebSearchAgent(),
            llm_client=FakeDecisionLLM("rag"),
            historical_memory_tool=FailingHistoricalMemoryTool(),
        )

        result = orchestrator.answer("Que es una red neuronal?", session_id="session-a")

        self.assertEqual(result["agent_selected"], "rag")
        self.assertEqual(result["answer"], "Respuesta desde RAG.")
        self.assertEqual(result["trace"]["historical_memory"]["updated"], False)
        self.assertIn("historical save unavailable", result["trace"]["historical_memory"]["error"])
        self.assertEqual(rag_agent.questions, ["Que es una red neuronal?"])

    def test_historical_memory_lookup_failure_does_not_break_summary_route(self):
        summarizer_agent = FakeSummarizerAgent()
        orchestrator = OrchestratorAgent(
            rag_agent=FakeRAGAgent(),
            summarizer_agent=summarizer_agent,
            web_search_agent=FakeWebSearchAgent(),
            llm_client=FakeDecisionLLM("rag"),
            historical_memory_tool=FailingHistoricalMemoryTool(),
        )

        result = orchestrator.answer("Que pregunte anteriormente sobre CNN?")

        self.assertEqual(result["agent_selected"], "summary")
        self.assertEqual(result["trace"]["historical_memory"]["queried"], True)
        self.assertEqual(result["trace"]["historical_memory"]["available"], False)
        self.assertIn("historical search unavailable", result["trace"]["historical_memory"]["error"])
        self.assertEqual(summarizer_agent.calls[0]["conversation_context"], "")

    def test_routes_to_summary_when_user_asks_for_session_summary(self):
        memory_tool = MemoryTool(memory=ConversationalMemory())
        memory_tool.save_turn(
            session_id="session-a",
            question="Que es RAG?",
            answer="RAG combina recuperacion con generacion.",
            agent_selected="rag",
        )
        summarizer_agent = FakeSummarizerAgent()
        orchestrator = OrchestratorAgent(
            rag_agent=FakeRAGAgent(),
            summarizer_agent=summarizer_agent,
            web_search_agent=FakeWebSearchAgent(),
            llm_client=FakeDecisionLLM("rag"),
            memory_tool=memory_tool,
        )

        result = orchestrator.answer(
            "Resume lo que hemos hablado en esta sesion.",
            session_id="session-a",
        )

        self.assertEqual(result["agent_selected"], "summary")
        self.assertEqual(result["answer"], "Resumen desde memoria.")
        self.assertEqual(result["sources"], [])
        self.assertEqual(result["trace"]["delegated_agent"], "SummarizerAgent")
        self.assertIn("Que es RAG?", summarizer_agent.calls[0]["conversation_context"])

    def test_summary_route_handles_empty_session_history(self):
        summarizer_agent = FakeSummarizerAgent()
        orchestrator = OrchestratorAgent(
            rag_agent=FakeRAGAgent(),
            summarizer_agent=summarizer_agent,
            web_search_agent=FakeWebSearchAgent(),
            llm_client=FakeDecisionLLM("rag"),
            memory_tool=MemoryTool(memory=ConversationalMemory()),
        )

        result = orchestrator.answer(
            "Resume esta sesion.",
            session_id="empty-session",
        )

        self.assertEqual(result["agent_selected"], "summary")
        self.assertEqual(result["trace"]["memory"]["turns_used"], 0)
        self.assertEqual(summarizer_agent.calls[0]["conversation_context"], "")

    def test_summary_request_with_web_word_still_routes_to_summary(self):
        memory_tool = MemoryTool(memory=ConversationalMemory())
        memory_tool.save_turn(
            session_id="session-a",
            question="Busca informacion actual sobre Tavily.",
            answer="Tavily es una herramienta web.",
            agent_selected="web",
        )
        summarizer_agent = FakeSummarizerAgent()
        orchestrator = OrchestratorAgent(
            rag_agent=FakeRAGAgent(),
            summarizer_agent=summarizer_agent,
            web_search_agent=FakeWebSearchAgent(),
            llm_client=FakeDecisionLLM("web"),
            memory_tool=memory_tool,
        )

        result = orchestrator.answer(
            "Resume esta sesion separando lo que vino de RAG y lo que vino de busqueda web.",
            session_id="session-a",
        )

        self.assertEqual(result["agent_selected"], "summary")
        self.assertEqual(result["trace"]["delegated_agent"], "SummarizerAgent")
        self.assertIn("Tavily", summarizer_agent.calls[0]["conversation_context"])

    def test_summary_agent_receives_extended_session_memory(self):
        memory_tool = MemoryTool(memory=ConversationalMemory())

        for index in range(8):
            memory_tool.save_turn(
                session_id="session-a",
                question=f"Pregunta historica {index}",
                answer=f"Respuesta historica {index}",
                agent_selected="rag" if index < 4 else "web",
            )

        summarizer_agent = FakeSummarizerAgent()
        orchestrator = OrchestratorAgent(
            rag_agent=FakeRAGAgent(),
            summarizer_agent=summarizer_agent,
            web_search_agent=FakeWebSearchAgent(),
            llm_client=FakeDecisionLLM("summary"),
            memory_tool=memory_tool,
        )

        result = orchestrator.answer(
            "Resume esta sesion.",
            session_id="session-a",
        )

        self.assertEqual(result["agent_selected"], "summary")
        self.assertEqual(result["trace"]["memory"]["turns_used"], 8)
        self.assertIn("Pregunta historica 0", summarizer_agent.calls[0]["conversation_context"])
        self.assertIn("Pregunta historica 7", summarizer_agent.calls[0]["conversation_context"])

    def test_web_route_does_not_instantiate_rag(self):
        web_agent = FakeWebSearchAgent()
        orchestrator = OrchestratorAgent(
            web_search_agent=web_agent,
            rag_agent_factory=exploding_rag_factory,
            llm_client=FakeDecisionLLM("web"),
        )

        result = orchestrator.answer("Cuales son las noticias recientes de Gemini?")

        self.assertEqual(result["agent_selected"], "web")
        self.assertEqual(result["answer"], "Respuesta desde Web.")
        self.assertEqual(web_agent.calls[0]["question"], "Cuales son las noticias recientes de Gemini?")

    def test_can_route_to_web_even_if_rag_cannot_load(self):
        web_agent = FakeWebSearchAgent()
        orchestrator = OrchestratorAgent(
            web_search_agent=web_agent,
            rag_agent_factory=exploding_rag_factory,
            llm_client=FakeDecisionLLM("web"),
        )

        result = orchestrator.answer("Busca en internet informacion actual sobre Gemini API.")

        self.assertEqual(result["agent_selected"], "web")
        self.assertEqual(result["trace"]["delegated_agent"], "WebSearchAgent")

    def test_academic_questions_are_forced_to_rag_even_if_gemini_says_web(self):
        questions = [
            "Que es el descenso del gradiente?",
            "Que problema presenta la funcion ReLU y como lo resuelve Leaky ReLU?",
            "Que es una red neuronal artificial?",
            "Que es una funcion de activacion?",
            "Que es backpropagation?",
        ]

        for question in questions:
            with self.subTest(question=question):
                rag_agent = FakeRAGAgent()
                orchestrator = OrchestratorAgent(
                    rag_agent=rag_agent,
                    web_search_agent=FakeWebSearchAgent(),
                    llm_client=FakeDecisionLLM("web"),
                )

                result = orchestrator.answer(question)

                self.assertEqual(result["agent_selected"], "rag")
                self.assertEqual(rag_agent.questions, [question])

    def test_academic_summary_questions_are_forced_to_rag(self):
        rag_agent = FakeRAGAgent()
        summarizer_agent = FakeSummarizerAgent()
        orchestrator = OrchestratorAgent(
            rag_agent=rag_agent,
            summarizer_agent=summarizer_agent,
            web_search_agent=FakeWebSearchAgent(),
            llm_client=FakeDecisionLLM("summary"),
        )

        result = orchestrator.answer("Resume backpropagation segun los apuntes.")

        self.assertEqual(result["agent_selected"], "rag")
        self.assertEqual(rag_agent.questions, ["Resume backpropagation segun los apuntes."])
        self.assertEqual(summarizer_agent.calls, [])

    def test_academic_comparison_with_previous_topic_routes_to_rag(self):
        rag_agent = FakeRAGAgent()
        summarizer_agent = FakeSummarizerAgent()
        orchestrator = OrchestratorAgent(
            rag_agent=rag_agent,
            summarizer_agent=summarizer_agent,
            web_search_agent=FakeWebSearchAgent(),
            llm_client=FakeDecisionLLM("summary"),
        )

        result = orchestrator.answer(
            "Compara lo anterior con RAG: son tecnicas del mismo tipo?"
        )

        self.assertEqual(result["agent_selected"], "rag")
        self.assertEqual(
            rag_agent.questions,
            ["Compara lo anterior con RAG: son tecnicas del mismo tipo?"],
        )
        self.assertEqual(summarizer_agent.calls, [])

    def test_explicit_current_or_web_questions_are_forced_to_web(self):
        questions = [
            "Cuales son las noticias recientes sobre Google Gemini?",
            "Busca la documentacion oficial de Tavily.",
            "Que cambios recientes ha anunciado OpenAI?",
            "Busca en internet informacion actual sobre Gemini API.",
        ]

        for question in questions:
            with self.subTest(question=question):
                web_agent = FakeWebSearchAgent()
                orchestrator = OrchestratorAgent(
                    rag_agent=FakeRAGAgent(),
                    web_search_agent=web_agent,
                    llm_client=FakeDecisionLLM("rag"),
                )

                result = orchestrator.answer(question)

                self.assertEqual(result["agent_selected"], "web")
                self.assertEqual(web_agent.calls[0]["question"], question)

    def test_prefers_rag_when_gemini_returns_unexpected_output(self):
        rag_agent = FakeRAGAgent()
        orchestrator = OrchestratorAgent(
            rag_agent=rag_agent,
            web_search_agent=FakeWebSearchAgent(),
            llm_client=FakeDecisionLLM("no estoy seguro"),
        )

        result = orchestrator.answer("Explica aprendizaje supervisado.")

        self.assertEqual(result["agent_selected"], "rag")
        self.assertEqual(result["trace"]["raw_decision"], "no estoy seguro")
        self.assertEqual(rag_agent.questions, ["Explica aprendizaje supervisado."])

    def test_rejects_empty_question(self):
        orchestrator = OrchestratorAgent(
            rag_agent=FakeRAGAgent(),
            web_search_agent=FakeWebSearchAgent(),
            llm_client=FakeDecisionLLM("rag"),
        )

        with self.assertRaisesRegex(ValueError, "pregunta"):
            orchestrator.answer(" ")

    def test_updates_temporal_memory_after_answer(self):
        memory_tool = MemoryTool(memory=ConversationalMemory())
        orchestrator = OrchestratorAgent(
            rag_agent=FakeRAGAgent(),
            web_search_agent=FakeWebSearchAgent(),
            llm_client=FakeDecisionLLM("rag"),
            memory_tool=memory_tool,
        )

        result = orchestrator.answer(
            "Que es backpropagation?",
            session_id="session-a",
        )
        memory_context = memory_tool.get_context("session-a")

        self.assertEqual(result["trace"]["session_id"], "session-a")
        self.assertEqual(result["trace"]["memory"]["turns_used"], 0)
        self.assertEqual(memory_context["turns_count"], 1)
        self.assertIn("Que es backpropagation?", memory_context["formatted_context"])
        self.assertIn("Respuesta desde RAG.", memory_context["formatted_context"])

    def test_passes_recent_memory_to_rag_on_follow_up(self):
        memory_tool = MemoryTool(memory=ConversationalMemory())
        rag_agent = FakeRAGAgent()
        orchestrator = OrchestratorAgent(
            rag_agent=rag_agent,
            web_search_agent=FakeWebSearchAgent(),
            llm_client=FakeDecisionLLM("rag"),
            memory_tool=memory_tool,
        )

        orchestrator.answer("Que es descenso del gradiente?", session_id="session-a")
        result = orchestrator.answer("Y como se relaciona con eso?", session_id="session-a")

        self.assertEqual(result["trace"]["memory"]["turns_used"], 1)
        self.assertIn("descenso del gradiente", rag_agent.conversation_contexts[1])
        self.assertIn("[Turno 1", rag_agent.conversation_contexts[1])

    def test_does_not_mix_memory_between_sessions(self):
        memory_tool = MemoryTool(memory=ConversationalMemory())
        rag_agent = FakeRAGAgent()
        orchestrator = OrchestratorAgent(
            rag_agent=rag_agent,
            web_search_agent=FakeWebSearchAgent(),
            llm_client=FakeDecisionLLM("rag"),
            memory_tool=memory_tool,
        )

        orchestrator.answer("Que es overfitting?", session_id="session-a")
        result = orchestrator.answer("Y eso?", session_id="session-b")

        self.assertEqual(result["trace"]["session_id"], "session-b")
        self.assertEqual(result["trace"]["memory"]["turns_used"], 0)
        self.assertEqual(rag_agent.conversation_contexts[1], "")


if __name__ == "__main__":
    unittest.main()
