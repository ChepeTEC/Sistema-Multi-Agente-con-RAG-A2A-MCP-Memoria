# Archivo que se encarga del procesamiento de los datos para el RAG
# Es decir limpia y prepara los datos para ser utilizados por el modelo

import re
import unicodedata

def clean_text(text: str) -> str:

    # Limpia el texto extraido de los PDFs, NO se eliminan tildes.

    text = text.replace("\x00", " ")

    text = text.replace("\n", " ")

    text = text.replace("\t", " ")

    text = unicodedata.normalize("NFKC", text)

    text = re.sub(r"\s+", " ", text)

    return text.strip()

def preprocess_documents(documents: list[dict]) -> list[dict]:

    # Aplica limpieza a cada página extraída.

    cleaned_documents = []

    for doc in documents:

        cleaned = clean_text(doc["text"])

        if cleaned:

            cleaned_documents.append({

                "text": cleaned,

                "metadata": doc["metadata"]

            })

    return cleaned_documents