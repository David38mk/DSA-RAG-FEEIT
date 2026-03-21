from src.preprocessing.smart_chunker import SmartChunker
from src.ingestion.faq_parser import parse_faq_file

# Parse FAQ
pairs = parse_faq_file('data/raw/mk/Често поставувани прашања.docx')

# Chunk them
chunker = SmartChunker()
chunks = chunker._chunk_faq(pairs, "FAQ.docx")

# Find syllabus chunk
for chunk in chunks:
    if 'сиже' in chunk['text']:
        print("="*70)
        print("SYLLABUS CHUNK FOUND")
        print("="*70)
        print(f"Length: {len(chunk['text'])} chars")
        print(f"Complete: {chunk['metadata'].get('complete', True)}")
        print(f"\nFull text:")
        print(chunk['text'])
        print("="*70)
        
        # Check if URL is present
        if 'feit.ukim.edu.mk' in chunk['text']:
            print("✓ URL present in chunk")
        else:
            print("✗ URL MISSING - chunk was truncated!")