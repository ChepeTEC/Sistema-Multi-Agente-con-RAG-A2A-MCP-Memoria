# Archivo que se encarga del procesamiento de los datos para el RAG
# Es decir limpia y prepara los datos para ser utilizados por el modelo
import re
import unicodedata


def fix_broken_accents(text: str) -> str:
    """
    Corrige de forma general problemas comunes de extracción de PDFs,
    especialmente tildes separadas como:
    Qu ́e -> Qué
    definici ́on -> definición
    t ́ecnicas -> técnicas
    """

    # Algunos PDFs extraen la tilde como comilla aguda.
    text = text.replace("´", "\u0301")
    text = text.replace("`", "\u0300")

    # Corrige casos donde hay una letra, espacios y luego un acento combinante.
    # Ejemplo: "e ́" -> "é"
    text = re.sub(
        r"([A-Za-zÁÉÍÓÚáéíóúÑñÜü])\s+([\u0300-\u036f])",
        r"\1\2",
        text
    )

    # Normaliza letra + acento para convertirlo en un solo carácter.
    text = unicodedata.normalize("NFC", text)

    # Algunos PDFs usan una i sin punto. La cambiamos por i normal.
    text = text.replace("ı", "i")

    # Reaplica normalización después de corregir caracteres.
    text = unicodedata.normalize("NFC", text)

    return text


def clean_text(text: str) -> str:
    """
    Limpia texto extraído de PDFs.
    """

    if not text:
        return ""

    text = text.replace("\x00", " ")
    text = text.replace("\n", " ")
    text = text.replace("\t", " ")

    text = fix_broken_accents(text)

    # Normalización general de Unicode.
    text = unicodedata.normalize("NFKC", text)

    # Elimina espacios repetidos.
    text = re.sub(r"\s+", " ", text)

    # Corrige espacios antes de signos de puntuación.
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)

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