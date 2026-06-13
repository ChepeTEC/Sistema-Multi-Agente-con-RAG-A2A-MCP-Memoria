from src.config.settings import settings
from src.rag.loaders import load_all_pdfs
from src.rag.preprocessors import preprocess_documents
from src.rag.splitters import split_documents
from src.rag.embeddings import EmbeddingModel
from src.rag.vector_db import ChromaVectorStore


def main():
    print("Iniciando ingesta de apuntes...")

    settings.NOTES_DIR.mkdir(parents=True, exist_ok=True)
    settings.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    settings.VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Leyendo PDFs desde: {settings.NOTES_DIR}")
    documents = load_all_pdfs(settings.NOTES_DIR)
    print(f"Páginas cargadas: {len(documents)}")

    print("Limpiando texto...")
    cleaned_documents = preprocess_documents(documents)
    print(f"Páginas limpias: {len(cleaned_documents)}")

    print("Dividiendo documentos en chunks...")
    chunks = split_documents(
        cleaned_documents,
        chunk_size=800,
        chunk_overlap=150
    )
    print(f"Chunks generados: {len(chunks)}")

    print(f"Cargando modelo de embeddings: {settings.EMBEDDING_MODEL}")
    embedding_model = EmbeddingModel(settings.EMBEDDING_MODEL)

    texts = [chunk["text"] for chunk in chunks]

    print("Generando embeddings...")
    embeddings = embedding_model.embed_documents(texts)

    print("Guardando en ChromaDB...")
    vector_store = ChromaVectorStore(
        persist_dir=settings.VECTOR_DB_DIR,
        collection_name=settings.COLLECTION_NAME
    )

    print("Recreando coleccion vectorial...")
    vector_store.reset_collection()

    vector_store.add_chunks(chunks, embeddings)

    print("Ingesta completada correctamente.")
    print(f"Base vectorial guardada en: {settings.VECTOR_DB_DIR}")


if __name__ == "__main__":
    main()
