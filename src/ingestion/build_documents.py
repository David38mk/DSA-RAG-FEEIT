import json
from pathlib import Path
from collections import Counter

from src.ingestion.pdf_slides_parser import extract_pdf_slides
from src.ingestion.pdf_book_parser import extract_pdf_book
from src.preprocessing.cleaner import clean_slide_text, clean_book_text
from src.preprocessing.language import detect_language
from src.preprocessing.text_splitter import split_book_text
from src.preprocessing.book_filters import is_junk_page
from src.preprocessing.slide_splitter import split_slide_text
from src.preprocessing.slide_filters import is_slide_title


SLIDES_DIR = Path("data/raw/mk")
BOOK_PATH = Path("data/raw/en/Data-Structures-and-Algorithms-in-Java-6th-Edition.pdf")
OUTPUT_PATH = Path("data/processed/documents.json")


def process_slides():
    documents = []

    for pdf_file in SLIDES_DIR.glob("*.pdf"):
        slides = extract_pdf_slides(str(pdf_file))

        for slide in slides:
            cleaned = clean_slide_text(slide["text"])
            if not cleaned:
                continue

            language = "mk"

            chunks = split_slide_text(cleaned)

            for chunk_id, chunk in enumerate(chunks):
                if is_slide_title(chunk):
                    continue
                documents.append({
                    "text": chunk,
                    "metadata": {
                        "source": slide["source"],
                        "type": "slide",
                        "slide_number": slide["slide_number"],
                        "chunk": chunk_id,
                        "language": language,
                        "domain": "academic"
                    }
                })

    return documents


def process_book():
    documents = []
    pages = extract_pdf_book(str(BOOK_PATH))

    for page in pages:
        cleaned = clean_book_text(page["text"])
        if not cleaned:
            continue

        if is_junk_page(cleaned):
            continue

        chunks = split_book_text(cleaned)

        for chunk_id, chunk in enumerate(chunks):
            language = detect_language(chunk)

            documents.append({
                "text": chunk,
                "metadata": {
                    "source": page["source"],
                    "type": "book",
                    "page": page["page"],
                    "chunk": chunk_id,
                    "language": language,
                    "domain": "theory"
                }
            })

    return documents


def main():
    all_documents = []

    all_documents.extend(process_slides())
    all_documents.extend(process_book())

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_documents, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(all_documents)} documents to {OUTPUT_PATH}")
    types = Counter(d["metadata"]["type"] for d in all_documents)
    print("Document types:", types)


if __name__ == "__main__":
    main()

