from src.ingestion.multi_format_extractor import extract_pdf
from src.ingestion.document_classifier import classify_document

pages = extract_pdf("data/raw/mk/PSAA_Auditoriski_05.pdf")
code_pages = [p for p in pages if p.get('has_code')]

print(f"Found {len(code_pages)} pages with code")
for p in code_pages[:2]:
    print(f"\nPage {p['page_number']}:")
    print(p['text'][:300])