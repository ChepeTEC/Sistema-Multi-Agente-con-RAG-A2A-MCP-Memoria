import re
from src.rag.preprocessors import clean_text
from pathlib import Path


def extract_metadata_from_filename(pdf_path: Path) -> dict:
    """
    Extrae metadatos desde nombres tipo:
    2_SEMANA_AI_20260224_1.pdf
    1_SEMANA_IA_20260219_2.pdf
    """

    filename = pdf_path.name

    pattern = (
        r"^(?P<week>\d+)_SEMANA_"
        r"(?P<course_tag>AI|IA)_"
        r"(?P<date>\d{8})_"
        r"(?P<version>\d+)\.pdf$"
    )

    match = re.match(pattern, filename, re.IGNORECASE)

    if not match:
        return {
            "source": filename,
            "file_path": str(pdf_path),
            "week": None,
            "course_tag": None,
            "date": None,
            "version": None,
        }

    raw_date = match.group("date")
    formatted_date = f"{raw_date[0:4]}-{raw_date[4:6]}-{raw_date[6:8]}"

    return {
        "source": filename,
        "file_path": str(pdf_path),
        "week": int(match.group("week")),
        "course_tag": match.group("course_tag").upper(),
        "date": formatted_date,
        "version": int(match.group("version")),
    }


def extract_author_from_text(text: str) -> str | None:

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    ignore_keywords = [
        "apuntes",
        "inteligencia artificial",
        "escuela",
        "tecnológico",
        "instituto",
        "profesor",
        "curso",
        "fecha",
        "resumen",
        "abstract",
    ]

    for line in lines[:15]:
        lower = line.lower()

        if any(keyword in lower for keyword in ignore_keywords):
            continue

        # Heurística simple: una línea con 2 a 5 palabras parece nombre.
        words = line.split()
        if 2 <= len(words) <= 5 and not any(char.isdigit() for char in line):
            return line

    return None


def extract_topic_from_text(text: str) -> str:
    """
    Intenta inferir tema principal desde título, resumen o introducción.
    Si no encuentra algo claro, usa Inteligencia Artificial.
    """

    lowered = text.lower()

    topic_keywords = {
        "Inteligencia Artificial": ["inteligencia artificial", "ia"],
        "Machine Learning": ["machine learning", "aprendizaje automático"],
        "Aprendizaje Supervisado": ["aprendizaje supervisado"],
        "Aprendizaje No Supervisado": ["aprendizaje no supervisado"],
        "Redes Neuronales": ["redes neuronales", "red neuronal"],
        "Búsqueda": ["búsqueda", "busqueda", "backtracking"],
        "Algoritmos Genéticos": ["algoritmos genéticos", "algoritmos geneticos"],
        "RAG": ["rag", "retrieval augmented generation"],
    }

    for topic, keywords in topic_keywords.items():
        if any(keyword in lowered for keyword in keywords):
            return topic

    return "Inteligencia Artificial"


def extract_section_from_text(text: str) -> str | None:
    """
    Intenta encontrar una sección o subsección dentro del texto del chunk.

    Busca encabezados tipo:
    I. INTRODUCCIÓN
    I-A. ¿Qué es Inteligencia?
    III-B. Preprocesamiento textual
    1. Inteligencia Artificial
    """

    text = clean_text(text)

    patterns = [
        r"\b[IVXLCDM]+-[A-Z]\.\s+[^.]{3,120}",
        r"\b[IVXLCDM]+\.\s+[^.]{3,120}",
        r"\b\d+\.\s+[^.]{3,120}",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            section = match.group(0).strip()
            section = re.sub(r"\s+", " ", section)
            section = section.strip(" -:;,.")

            # Si el encabezado contiene una pregunta, cortamos al cerrar pregunta.
            if "?" in section:
                section = section[: section.find("?") + 1]

            # Si aparece una oración explicativa después del título, la removemos.
            sentence_starters = [
                " Se ",
                " El ",
                " La ",
                " Los ",
                " Las ",
                " Por lo tanto",
                " Basado en",
                " Aunque",
            ]

            for starter in sentence_starters:
                pos = section.find(starter)
                if pos > 8:
                    section = section[:pos].strip()
                    break

            return section[:100]

    return None


def enrich_document_metadata(base_metadata: dict, page_text: str) -> dict:
    """
    Agrega autor y tema principal usando texto de la página.
    """

    metadata = base_metadata.copy()

    metadata["author"] = extract_author_from_text(page_text)
    metadata["topic"] = extract_topic_from_text(page_text)

    return metadata