from src.ingestion.faq_parser import parse_faq_file

qa = parse_faq_file("data/raw/mk/Често поставувани прашања.docx")
for i, pair in enumerate(qa[:3], 1):
    print(f"\n=== Pair {i} ===")
    print(f"Q: {pair['question'][:150]}")
    print(f"A: {pair['answer'][:150]}")