# Splitters se encarga de partir el texto en fragmentos más pequeños para que el modelo pueda procesarlos (chunks)

"""

PDF completo
   ↓
texto extraído
   ↓
splitter
   ↓
chunk 1
chunk 2
chunk 3
chunk 4
   ↓
embeddings
   ↓
ChromaDB

"""

from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_documents(
    documents: list[dict],
    chunk_size: int = 800,
    chunk_overlap: int = 150
) -> list[dict]:
    
    # Divide los documentos en fragmentos pequeños para RAG.
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""]
    )

    chunks = []

    for doc in documents:
        split_texts = splitter.split_text(doc["text"])

        for index, chunk_text in enumerate(split_texts):
            metadata = doc["metadata"].copy()
            metadata["chunk_index"] = index
            metadata["chunk_size"] = chunk_size
            metadata["chunk_overlap"] = chunk_overlap

            chunks.append({
                "text": chunk_text,
                "metadata": metadata
            })

    return chunks