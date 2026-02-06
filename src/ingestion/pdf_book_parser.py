from pypdf import PdfReader
from pathlib import Path

def extract_pdf_book(pdf_path: str):
    reader = PdfReader(pdf_path)
    pages = []

    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            pages.append({
                "source": Path(pdf_path).name,
                "page": i + 1,
                "text": text.strip(),
                "type": "book"
            })

    return pages
