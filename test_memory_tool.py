import unittest

from src.memory.conversational_memory import ConversationalMemory
from src.tools.memory_tool import MemoryTool


class MemoryToolTests(unittest.TestCase):
    def test_formats_recent_turns_for_context(self):
        memory_tool = MemoryTool(memory=ConversationalMemory())

        memory_tool.save_turn(
            session_id="session-a",
            question="Que es RAG?",
            answer="RAG combina recuperacion con generacion.",
            agent_selected="rag",
            sources=[{"file": "apuntes.pdf"}],
        )

        context = memory_tool.get_context("session-a")

        self.assertTrue(context["has_context"])
        self.assertEqual(context["turns_count"], 1)
        self.assertIn("Que es RAG?", context["formatted_context"])
        self.assertIn("RAG combina recuperacion", context["formatted_context"])
        self.assertEqual(context["turns"][0]["sources_count"], 1)

    def test_limits_turns_per_session(self):
        memory_tool = MemoryTool(
            memory=ConversationalMemory(max_turns_per_session=2),
            max_context_turns=2,
        )

        for index in range(3):
            memory_tool.save_turn(
                session_id="session-a",
                question=f"Pregunta {index}",
                answer=f"Respuesta {index}",
                agent_selected="rag",
            )

        context = memory_tool.get_context("session-a")

        self.assertEqual(context["turns_count"], 2)
        self.assertNotIn("Pregunta 0", context["formatted_context"])
        self.assertIn("Pregunta 1", context["formatted_context"])
        self.assertIn("Pregunta 2", context["formatted_context"])

    def test_sessions_are_isolated(self):
        memory_tool = MemoryTool(memory=ConversationalMemory())

        memory_tool.save_turn(
            session_id="session-a",
            question="Pregunta A",
            answer="Respuesta A",
            agent_selected="rag",
        )

        context = memory_tool.get_context("session-b")

        self.assertFalse(context["has_context"])
        self.assertEqual(context["turns_count"], 0)
        self.assertEqual(context["formatted_context"], "")


if __name__ == "__main__":
    unittest.main()
