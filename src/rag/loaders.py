from pathlib import Path
from pypdf import PdfReader
from src.rag.metadata import (
    extract_metadata_from_filename,
    enrich_document_metadata,
)


def load_pdf_text(pdf_path: Path) -> list[dict]:
    """
    Extrae texto de un PDF y devuelve una lista de páginas con metadatos.
    """
    reader = PdfReader(str(pdf_path))
    pages = []

    base_metadata = extract_metadata_from_filename(pdf_path)

    first_page_text = ""
    if reader.pages:
        first_page_text = reader.pages[0].extract_text() or ""

    document_metadata = enrich_document_metadata(
        base_metadata=base_metadata,
        page_text=first_page_text,
    )

    for page_index, page in enumerate(reader.pages):
        text = page.extract_text() or ""

        if text.strip():
            metadata = document_metadata.copy()
            metadata["page"] = page_index + 1

            pages.append({
                "text": text,
                "metadata": metadata
            })

    return pages


def load_all_pdfs(notes_dir: Path) -> list[dict]:
    """
    Carga todos los PDFs de la carpeta de apuntes.
    """
    pdf_files = sorted(notes_dir.glob("*.pdf"))
    documents = []

    if not pdf_files:
        raise FileNotFoundError(
            f"No se encontraron PDFs en la carpeta: {notes_dir}"
        )

    for pdf_path in pdf_files:
        documents.extend(load_pdf_text(pdf_path))

    return documents