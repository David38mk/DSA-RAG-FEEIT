from src.ingestion.pdf_book_parser import extract_pdf_book

book_content = extract_pdf_book("data/raw/en/Data-Structures-and-Algorithms-in-Java-6th-Edition.pdf")

print(book_content[:500])  # Print the first 500 characters of the book content