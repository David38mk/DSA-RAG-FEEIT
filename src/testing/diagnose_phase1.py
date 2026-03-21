"""
DIAGNOSTIC SCRIPT - Debug Phase 1 Classification

Run this to see what's actually happening with document classification.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.ingestion.multi_format_extractor import MultiFormatExtractor
from src.ingestion.document_classifier import DocumentClassifier
from src.ingestion.faq_parser import parse_faq_file


def diagnose_faq():
    """Diagnose FAQ extraction"""
    print("\n" + "="*70)
    print("DIAGNOSING FAQ EXTRACTION")
    print("="*70)
    
    faq_file = "data/raw/mk/Често поставувани прашања.docx"
    
    if not Path(faq_file).exists():
        print(f"❌ FAQ file not found: {faq_file}")
        return
    
    print(f"\n1. Extracting FAQ with parse_faq_file()...")
    qa_pairs = parse_faq_file(faq_file)
    print(f"   Result: {len(qa_pairs)} Q&A pairs")
    
    if qa_pairs:
        print(f"\n   First pair:")
        print(f"   Q: {qa_pairs[0].get('question', '')[:100]}...")
        print(f"   A: {qa_pairs[0].get('answer', '')[:100]}...")
        print(f"   Type: {qa_pairs[0].get('type')}")
    
    print(f"\n2. Extracting FAQ with MultiFormatExtractor()...")
    extractor = MultiFormatExtractor()
    docs = extractor.extract_document(faq_file)
    print(f"   Result: {len(docs)} sections")
    
    if docs:
        print(f"\n   First section:")
        print(f"   Type: {docs[0].get('type')}")
        print(f"   Header: {docs[0].get('header')}")
        print(f"   Content preview: {docs[0].get('content', '')[:100]}...")
    
    print(f"\n3. Classifying FAQ documents...")
    classifier = DocumentClassifier()
    classified = [classifier.classify_document(doc) for doc in docs]
    
    print(f"\n   Classifications:")
    for doc in classified:
        print(f"   - Type: {doc['classification']['type']}, Domain: {doc['classification']['domain']}")


def diagnose_supplementary():
    """Diagnose supplementary slide classification"""
    print("\n" + "="*70)
    print("DIAGNOSING SUPPLEMENTARY SLIDES")
    print("="*70)
    
    test_file = "data/raw/mk/[PSAA] #05 - Drva.pdf"
    
    if not Path(test_file).exists():
        print(f"❌ Test file not found")
        return
    
    extractor = MultiFormatExtractor()
    classifier = DocumentClassifier()
    
    pages = extractor.extract_document(test_file)
    print(f"\n✓ Extracted {len(pages)} pages from {Path(test_file).name}")
    
    # Classify first page
    if pages:
        classified = classifier.classify_document(pages[0])
        print(f"\nFirst page classification:")
        print(f"  Type: {classified['classification']['type']}")
        print(f"  Expected: supplementary_slides")
        print(f"  Match: {classified['classification']['type'] == 'supplementary_slides'}")


def diagnose_all_documents():
    """Get classification breakdown of all documents"""
    print("\n" + "="*70)
    print("FULL DOCUMENT CLASSIFICATION BREAKDOWN")
    print("="*70)
    
    from collections import Counter
    
    data_dir = Path("data/raw/mk")
    extractor = MultiFormatExtractor()
    classifier = DocumentClassifier()
    
    all_docs = []
    
    # Extract all
    for file in data_dir.glob("*"):
        if file.suffix in ['.pdf', '.docx']:
            docs = extractor.extract_document(str(file))
            all_docs.extend(docs)
    
    print(f"\n✓ Loaded {len(all_docs)} total documents")
    
    # Classify
    classified = classifier.classify_batch(all_docs)
    
    # Count by type
    types = Counter(d['classification']['type'] for d in classified)
    
    print(f"\nClassification counts:")
    for doc_type, count in types.items():
        print(f"  {doc_type}: {count}")
    
    # Show FAQ documents
    faq_docs = [d for d in classified if d['classification']['type'] == 'faq']
    print(f"\nFAQ documents found: {len(faq_docs)}")
    if faq_docs:
        for doc in faq_docs[:3]:
            print(f"  - {doc.get('source')}: {doc.get('type')} - {len(doc.get('text', doc.get('content', '')))} chars")


def main():
    print("\n" + "="*70)
    print(" PHASE 1 DIAGNOSTIC TOOL")
    print("="*70)
    
    print("\nThis will diagnose:")
    print("1. FAQ extraction and classification")
    print("2. Supplementary slide classification")
    print("3. Overall document type distribution")
    
    input("\nPress Enter to start...")
    
    try:
        diagnose_faq()
        diagnose_supplementary()
        diagnose_all_documents()
        
        print("\n" + "="*70)
        print(" DIAGNOSTIC COMPLETE")
        print("="*70)
        print("\nReview the output above to identify issues.")
        
    except Exception as e:
        print(f"\n❌ Diagnostic failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()