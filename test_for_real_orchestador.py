

from src.agents.orchestrator_agent import OrchestratorAgent


def print_sources(sources: list[dict]) -> None:
    print("\nFuentes recuperadas:")

    if not sources:
        print("- No se encontraron fuentes.")
        return

    for index, source in enumerate(sources, start=1):
        # Fuentes del RAGAgent: PDFs/apuntes del curso
        if "file" in source:
            file = source.get("file", "desconocido")
            page = source.get("page", "desconocida")
            week = source.get("week", "desconocida")
            section = source.get("section", "")

            if section:
                print(f"{index}. {file} | página {page} | semana {week} | sección: {section}")
            else:
                print(f"{index}. {file} | página {page} | semana {week}")

        # Fuentes del WebSearchAgent: resultados web
        else:
            title = source.get("title", "sin título")
            url = source.get("url", source.get("source", "sin URL"))
            score = source.get("score")

            if score is not None:
                print(f"{index}. {title} | {url} | score: {score}")
            else:
                print(f"{index}. {title} | {url}")


def print_trace(trace: dict) -> None:
    print("\nTrace interno del orquestador:")
    print("-" * 70)

    if not trace:
        print("- No se encontró trace interno.")
        return

    print(f"Pregunta: {trace.get('question')}")
    print(f"Orquestador: {trace.get('orchestrator')}")
    print(f"Agente seleccionado: {trace.get('agent_selected')}")
    print(f"Modelo de decisión: {trace.get('decision_model')}")
    print(f"Proveedor: {trace.get('decision_provider')}")
    print(f"Duración decisión ms: {trace.get('decision_duration_ms')}")
    print(f"Duración total ms: {trace.get('total_duration_ms')}")
    print(f"Agente delegado: {trace.get('delegated_agent')}")


def main() -> None:
    """
    Prueba real del OrchestratorAgent.

    Este archivo usa el orquestador completo, no mocks. Sirve para demostrar:
    - entrada del usuario
    - decisión del orquestador
    - agente seleccionado
    - respuesta final
    - fuentes recuperadas
    - trazas en Langfuse
    """

    orchestrator = OrchestratorAgent()

    print("Prueba real del OrchestratorAgent")
    print("-" * 70)

    question = input("Pregunta para el OrchestratorAgent: ")

    result = orchestrator.answer(question)

    print("\nAgente seleccionado:")
    print(result.get("agent_selected", "desconocido"))

    print("\nRazón de decisión:")
    print(result.get("decision_reason", "No disponible"))

    print("\nRespuesta generada:")
    print("-" * 70)
    print(result.get("answer", "No se generó respuesta."))

    print_sources(result.get("sources", []))
    print_trace(result.get("trace", {}))

    print("\nRevisar en Langfuse:")
    print("- orchestrator_request")

    selected_agent = result.get("agent_selected")

    if selected_agent == "rag":
        print("- rag_agent_answer")
        print("- rag_retrieval")
        print("- gemini_generation")
    elif selected_agent == "web":
        print("- agent_response con delegado WebSearchAgent")
    else:
        print("- revisar agent_response para ver qué agente fue delegado")


if __name__ == "__main__":
    main()