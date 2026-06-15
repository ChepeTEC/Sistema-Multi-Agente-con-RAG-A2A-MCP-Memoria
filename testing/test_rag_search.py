from src.tools.rag_tool import RAGTool


def main():
    rag_tool = RAGTool()

    query = input("Escriba una pregunta sobre los apuntes: ")

    results = rag_tool.search_notes(query, n_results=5)

    print("\nFragmentos encontrados:\n")

    for index, result in enumerate(results, start=1):
        metadata = result["metadata"]

        print("=" * 80)
        print(f"Resultado #{index}")
        print(f"Archivo: {metadata.get('source')}")
        print(f"Autor: {metadata.get('author')}")
        print(f"Fecha: {metadata.get('date')}")
        print(f"Semana: {metadata.get('week')}")
        print(f"Tema: {metadata.get('topic')}")
        print(f"Sección: {metadata.get('section')}")
        print(f"Página: {metadata.get('page')}")
        print(f"Versión: {metadata.get('version')}")
        print(f"Distancia: {result.get('distance')}")
        print("-" * 80)
        print(result["text"][:1000])
        print()


if __name__ == "__main__":
    main()