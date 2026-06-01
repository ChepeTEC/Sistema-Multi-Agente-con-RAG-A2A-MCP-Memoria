# Archivo que se encarga de leer todos los PDFs de los apuntes de clase en data/notes/

from pathlib import Path
from pypdf import PdfReader


def load_pdf_text(pdf_path: Path) -> list[dict]:
    
    # Extrae texto de un PDF y devuelve una lista de páginas con metadatos.
    
    reader = PdfReader(str(pdf_path))
    pages = []

    for page_index, page in enumerate(reader.pages):
        text = page.extract_text() or ""

        if text.strip():
            pages.append({
                "text": text,
                "metadata": {
                    "source": pdf_path.name,
                    "file_path": str(pdf_path),
                    "page": page_index + 1,
                }
            })

    return pages


def load_all_pdfs(notes_dir: Path) -> list[dict]:
    
    # Carga todos los PDFs de la carpeta de apuntes.
    
    pdf_files = sorted(notes_dir.glob("*.pdf"))
    documents = []

    if not pdf_files:
        raise FileNotFoundError(
            f"No se encontraron PDFs en la carpeta: {notes_dir}"
        )

    for pdf_path in pdf_files:
        documents.extend(load_pdf_text(pdf_path))

    return documents