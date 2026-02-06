from pypdf import PdfReader
from pathlib import Path

def extract_pdf_slides(pdf_path: str):
    reader = PdfReader(pdf_path)
    slides = []

    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            slides.append({
                "source": Path(pdf_path).name,
                "slide_number": i + 1,
                "text": text.strip(),
                "type": "slide"
            })

    return slides
