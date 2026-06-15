from src.agents.rag_agent import RAGAgent


def main():
    agent = RAGAgent()

    question = input("Pregunta: ")

    result = agent.answer(question)

    print("\nRespuesta del RAGAgent:\n")
    print(result["answer"])


if __name__ == "__main__":
    main()