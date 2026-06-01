# Se encarga de guardar los chunks de los apuntes junto a los embeddings 
# Para luego buscar los chunks más relevantes a una pregunta dada por el usuario

"""
pregunta del usuario
        ↓
embedding de la pregunta
        ↓
vector_db.py busca en ChromaDB
        ↓
devuelve los fragmentos más parecidos
"""
from pathlib import Path
import chromadb


class ChromaVectorStore:
    def __init__(self, persist_dir: Path, collection_name: str):
        self.client = chromadb.PersistentClient(path=str(persist_dir))
        self.collection = self.client.get_or_create_collection(
            name=collection_name
        )

    def _sanitize_metadata(self, metadata: dict) -> dict:
        """
        ChromaDB solo acepta metadata con valores str, int, float o bool.
        Aquí convertimos None a string vacío y cualquier valor raro a string.
        """
        clean_metadata = {}

        for key, value in metadata.items():
            if value is None:
                clean_metadata[key] = ""
            elif isinstance(value, (str, int, float, bool)):
                clean_metadata[key] = value
            else:
                clean_metadata[key] = str(value)

        return clean_metadata

    def add_chunks(
        self,
        chunks: list[dict],
        embeddings: list[list[float]]
    ) -> None:
        ids = []
        documents = []
        metadatas = []

        for index, chunk in enumerate(chunks):
            metadata = chunk["metadata"]

            chunk_id = (
                f"{metadata.get('source', 'unknown')}_"
                f"p{metadata.get('page', 0)}_"
                f"c{metadata.get('chunk_index', index)}"
            )

            ids.append(chunk_id)
            documents.append(chunk["text"])
            metadatas.append(self._sanitize_metadata(metadata))

        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )

    def search(
        self,
        query_embedding: list[float],
        n_results: int = 5
    ) -> dict:
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )