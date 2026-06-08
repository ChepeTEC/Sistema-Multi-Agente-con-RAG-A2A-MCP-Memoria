# Se encarga en traducir el texto a vectores para que ChromaDB pueda así buscar el significado, no solo por las palabras


from sentence_transformers import SentenceTransformer


class EmbeddingModel:
    def __init__(self, model_name: str):
        try:
            self.model = SentenceTransformer(model_name)
        except Exception as exc:
            raise RuntimeError(
                "No se pudo cargar el modelo de embeddings "
                f"'{model_name}'. Descargue/cachee el modelo de HuggingFace "
                "antes de usar RAG o revise la conexion a internet."
            ) from exc

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=True
        ).tolist()

    def embed_query(self, query: str) -> list[float]:
        return self.model.encode(
            query,
            convert_to_numpy=True
        ).tolist()
