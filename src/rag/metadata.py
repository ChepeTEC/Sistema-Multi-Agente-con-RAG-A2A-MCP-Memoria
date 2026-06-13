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
    improved_author = extract_author_from_text_v2(text)

    if improved_author:
        return improved_author

    return None

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


def extract_author_from_text_v2(text: str) -> str | None:
    lines = [
        clean_text(line)
        for line in text.splitlines()
        if line and line.strip()
    ]

    ignore_keywords = [
        "apunte",
        "apuntes",
        "abstract",
        "cartago",
        "clase",
        "costa rica",
        "curso",
        "escuela",
        "fecha",
        "inteligencia artificial",
        "instituto",
        "introduccion",
        "overfitting",
        "profesor",
        "quiz",
        "regresion",
        "regresión",
        "logistica",
        "logística",
        "respuesta",
        "respuestas",
        "resumen",
        "semana",
        "tecnologico",
        "underfitting",
    ]

    def is_name_candidate(value: str) -> bool:
        value = re.sub(r"^(?:\d+(?:st|nd|rd|th)?\s+)+", "", value.strip(), flags=re.I)
        value = value.strip(" -:,.;")
        lower = value.lower()

        if not value or any(keyword in lower for keyword in ignore_keywords):
            return False

        if re.match(r"^[IVXLCDM]+(?:-[A-Z])?\.\s+", value):
            return False

        if "@" in value or any(char.isdigit() for char in value):
            return False

        if "," in value or ":" in value or len(value) > 80:
            return False

        words = value.split()
        if not 2 <= len(words) <= 6:
            return False

        lowercase_particles = {"de", "del", "la", "las", "los", "y"}
        capitalized_words = 0

        for word in words:
            clean_word = word.strip(" -.,;:")

            if clean_word.lower() in lowercase_particles:
                continue

            if len(clean_word) < 2 or not clean_word[0].isupper():
                return False

            capitalized_words += 1

        return capitalized_words >= 2

    def candidate_from_line(line: str) -> str | None:
        normalized = re.sub(r"\s+", " ", line).strip()
        normalized = re.sub(r"\b\d+(?:st|nd|rd|th)\b", " ", normalized, flags=re.I)
        normalized = re.split(
            r"\b(?:escuela|instituto|tecnologico|profesor|curso|fecha|carnet|carne|carne:)\b",
            normalized,
            maxsplit=1,
            flags=re.I,
        )[0]
        normalized = re.split(r"\d{4,}|@|,", normalized, maxsplit=1)[0]
        normalized = normalized.strip(" -:,.;")

        if is_name_candidate(normalized):
            return normalized

        name_pattern = (
            r"\b[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ´`'\u0300-\u036f]+"
            r"(?:\s+[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ´`'\u0300-\u036f]+){1,5}\b"
        )

        for match in re.finditer(name_pattern, line):
            candidate = match.group(0).strip(" -:,.;")

            if is_name_candidate(candidate):
                return candidate

        return None

    for line in lines[:25]:
        candidate = candidate_from_line(line)

        if candidate:
            return normalize_author_name(candidate)

    return None


def normalize_author_name(author: str) -> str:
    replacements = {
        "Jośe": "José",
        "Ferńandez": "Fernández",
        "Ingenieŕia": "Ingeniería",
        "Guilĺen": "Guillén",
    }

    normalized = author

    for source, target in replacements.items():
        normalized = normalized.replace(source, target)

    return normalized


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
