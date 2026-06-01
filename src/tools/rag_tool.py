# Es la herramienta que se encarga de consultar la base vectorial de ChromaDB para encontrar los fragmentos más relevantes a una pregunta dada por el usuario

"""
Flujo:

Pregunta del usuario
   ↓
convertir la pregunta en embedding (vector numerico)
   ↓
buscar en ChromaDB los chunks más parecidos (busca en vector_store/chroma)
   ↓
devolver texto + archivo + página + distancia (devuele los 5 mejores)
"""

from src.config.settings import settings
from src.rag.embeddings import EmbeddingModel
from src.rag.vector_db import ChromaVectorStore


class RAGTool:
    """
    Herramienta para buscar fragmentos relevantes en los apuntes del curso.

    Esta clase NO genera respuestas todavía.
    Solo recupera texto desde ChromaDB usando embeddings.
    """

    def __init__(self):
        self.embedding_model = EmbeddingModel(settings.EMBEDDING_MODEL)

        self.vector_store = ChromaVectorStore(
            persist_dir=settings.VECTOR_DB_DIR,
            collection_name=settings.COLLECTION_NAME
        )

    def search_notes(self, query: str, n_results: int = 5) -> list[dict]:
        """
        Recibe una pregunta, la convierte en embedding y busca
        los fragmentos más parecidos en la base vectorial.
        """

        if not query or not query.strip():
            raise ValueError("La consulta no puede estar vacía.")

        query_embedding = self.embedding_model.embed_query(query)

        results = self.vector_store.search(
            query_embedding=query_embedding,
            n_results=n_results
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        formatted_results = []

        for text, metadata, distance in zip(documents, metadatas, distances):
            formatted_results.append({
                "text": text,
                "metadata": metadata,
                "distance": distance
            })

        return formatted_results


