from src.agents.rag_agent import RAGAgent

"""
COsillas utiles para el orchestador:

from src.agents.rag_agent import RAGAgent

rag_agent = RAGAgent()
result = rag_agent.answer("¿Qué es inteligencia artificial?")

answer = result["answer"]
sources = result["sources"]
chunks = result["chunks"]

"""
def print_sources(sources: list[dict]) -> None:
    print("\nFuentes recuperadas:")

    if not sources:
        print("- No se encontraron fuentes.")
        return

    for index, source in enumerate(sources, start=1):
        file = source.get("file", "desconocido")
        page = source.get("page", "desconocida")
        week = source.get("week", "desconocida")
        section = source.get("section", "")

        if section:
            print(f"{index}. {file} | página {page} | semana {week} | sección: {section}")
        else:
            print(f"{index}. {file} | página {page} | semana {week}")


def main():
    """
    Archivo de prueba para que el encargado del OrchestratorAgent
    pueda ver cómo consumir el RAGAgent.

    El orquestador solo necesita llamar:

        result = rag_agent.answer(question)

    Y recibirá un diccionario con:
        - answer: respuesta final
        - sources: fuentes usadas
        - chunks: fragmentos recuperados como evidencia interna
    """

    rag_agent = RAGAgent()

    print("Prueba del RAGAgent para integración con OrchestratorAgent")
    print("-" * 70)

    question = input("Pregunta para el RAGAgent: ")

    result = rag_agent.answer(question)

    print("\nRespuesta generada:")
    print("-" * 70)
    print(result.get("answer", "No se generó respuesta."))

    print_sources(result.get("sources", []))

    print("\nInformación para integración:")
    print("-" * 70)
    print(f"Tipo de resultado: {type(result)}")
    print(f"Campos disponibles: {list(result.keys())}")
    print(f"Cantidad de fuentes: {len(result.get('sources', []))}")
    print(f"Cantidad de chunks recuperados: {len(result.get('chunks', []))}")


if __name__ == "__main__":
    main()