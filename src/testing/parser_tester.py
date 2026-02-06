from src.ingestion.pdf_slides_parser import extract_pdf_slides

slides = extract_pdf_slides("data/raw/mk/PSAA_Auditoriski_01.pdf")

print(slides[0])