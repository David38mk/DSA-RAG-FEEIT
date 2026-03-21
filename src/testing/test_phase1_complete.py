"""
PHASE 1 COMPLETE TEST - Multi-Format Extraction & Classification

Tests:
1. PDF slides extraction (Auditoriski + PSAA)
2. DOCX extraction (course info + FAQ)
3. Document classification
4. FAQ parsing
5. Data quality validation

Run this to validate entire Phase 1 pipeline.
"""

import sys
from pathlib import Path
from collections import Counter

# Add to path (adjust if needed)
sys.path.insert(0, str(Path(__file__).parent))

try:
    from src.ingestion.multi_format_extractor import MultiFormatExtractor
    from src.ingestion.faq_parser import FAQParser, parse_faq_file
    from src.ingestion.document_classifier import DocumentClassifier
    from src.ingestion.data_validator import DataValidator
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure all Phase 1 files are in the same directory")
    sys.exit(1)


def test_pdf_extraction():
    """Test PDF slide extraction"""
    print("\n" + "="*70)
    print("TEST 1: PDF SLIDE EXTRACTION")
    print("="*70)
    
    # Test files - update these paths!
    test_files = [
        "data/raw/mk/PSAA_Auditoriski_01.pdf",
        "data/raw/mk/[PSAA] #05 - Drva.pdf",
    ]
    
    extractor = MultiFormatExtractor()
    all_pages = []
    
    for pdf_file in test_files:
        if not Path(pdf_file).exists():
            print(f"⚠️  Skipping {pdf_file} - file not found")
            continue
        
        print(f"\nExtracting: {Path(pdf_file).name}")
        pages = extractor.extract_document(pdf_file)
        all_pages.extend(pages)
        print(f"  ✓ Extracted {len(pages)} pages")
        
        # Show first page preview
        if pages:
            first = pages[0]
            print(f"  First page: {first.get('char_count', 0)} chars")
            print(f"  Has code: {first.get('has_code', False)}")
            if first.get('issues'):
                print(f"  Issues: {first['issues']}")
    
    print(f"\n📊 Total pages extracted: {len(all_pages)}")
    
    return all_pages


def test_docx_extraction():
    """Test DOCX extraction"""
    print("\n" + "="*70)
    print("TEST 2: DOCX EXTRACTION (Course Info)")
    print("="*70)
    
    docx_file = "data/raw/mk/Podatoci_za_predmetot.docx"
    
    if not Path(docx_file).exists():
        print(f"❌ File not found: {docx_file}")
        return []
    
    extractor = MultiFormatExtractor()
    sections = extractor.extract_document(docx_file)
    
    print(f"\n✓ Extracted {len(sections)} sections")
    
    for i, section in enumerate(sections[:3], 1):  # Show first 3
        print(f"\n--- Section {i} ---")
        print(f"Header: {section.get('header', 'None')}")
        print(f"Content ({section.get('char_count', 0)} chars):")
        content = section.get('content', '')[:200]
        print(f"  {content}...")
    
    return sections


def test_faq_extraction():
    """Test FAQ Q&A extraction"""
    print("\n" + "="*70)
    print("TEST 3: FAQ EXTRACTION & PARSING")
    print("="*70)
    
    faq_file = "data/raw/mk/Често поставувани прашања.docx"
    
    if not Path(faq_file).exists():
        print(f"❌ File not found: {faq_file}")
        return []
    
    # Parse FAQ
    qa_pairs = parse_faq_file(faq_file)
    
    print(f"\n✓ Extracted {len(qa_pairs)} Q&A pairs")
    
    # Show first 2 pairs
    for i, pair in enumerate(qa_pairs[:2], 1):
        print(f"\n--- Q&A Pair {i} ---")
        print(f"Q: {pair.get('question', '')[:150]}...")
        print(f"A: {pair.get('answer', '')[:150]}...")
        print(f"Combined length: {pair.get('char_count', 0)} chars")
    
    return qa_pairs


def test_classification():
    """Test document classification"""
    print("\n" + "="*70)
    print("TEST 4: DOCUMENT CLASSIFICATION")
    print("="*70)
    
    # Test on various file types
    test_docs = []
    
    extractor = MultiFormatExtractor()
    classifier = DocumentClassifier()
    
    # Extract and classify a few documents
    test_files = {
        "data/raw/mk/PSAA_Auditoriski_01.pdf": "lecture_slides",
        "data/raw/mk/[PSAA] #05 - Drva.pdf": "supplementary_slides",
        "data/raw/mk/Podatoci_za_predmetot.docx": "administrative",
        "data/raw/mk/Често поставувани прашања.docx": "faq",
    }
    
    results = []
    
    for filepath, expected_type in test_files.items():
        if not Path(filepath).exists():
            print(f"⚠️  Skipping {filepath} - not found")
            continue
        
        docs = extractor.extract_document(filepath)
        if not docs:
            continue
        
        # Classify first document/page
        doc = docs[0]
        classified = classifier.classify_document(doc)
        
        detected_type = classified["classification"]["type"]
        status = "✓" if detected_type == expected_type else "✗"
        
        print(f"\n{status} {Path(filepath).name}")
        print(f"  Expected: {expected_type}")
        print(f"  Detected: {detected_type}")
        print(f"  Domain: {classified['classification']['domain']}")
        print(f"  Language: {classified['classification']['language']}")
        print(f"  Priority: {classified['retrieval_priority']}")
        print(f"  Has code: {classified['classification'].get('has_code', False)}")
        
        results.append(classified)
    
    return results


def test_full_pipeline():
    """Test complete extraction + classification pipeline"""
    print("\n" + "="*70)
    print("TEST 5: FULL PIPELINE (All Documents)")
    print("="*70)
    
    data_dir = Path("data/raw/mk")
    
    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir}")
        return []
    
    extractor = MultiFormatExtractor()
    classifier = DocumentClassifier()
    
    all_documents = []
    
    # Extract all PDFs
    pdf_files = list(data_dir.glob("*.pdf"))
    print(f"\nFound {len(pdf_files)} PDF files")
    
    for pdf_file in pdf_files:
        docs = extractor.extract_document(str(pdf_file))
        all_documents.extend(docs)
    
    # Extract all DOCX
    docx_files = list(data_dir.glob("*.docx"))
    print(f"Found {len(docx_files)} DOCX files")
    
    for docx_file in docx_files:
        docs = extractor.extract_document(str(docx_file))
        all_documents.extend(docs)
    
    print(f"\n✓ Extracted {len(all_documents)} total documents")
    
    # Classify all
    print("\n📊 Classifying documents...")
    classified_docs = classifier.classify_batch(all_documents)
    
    # Generate reports
    class_report = classifier.get_classification_report(classified_docs)
    
    print("\n--- Classification Report ---")
    print(f"Total documents: {class_report['total_documents']}")
    print(f"\nBy Type:")
    for doc_type, count in class_report['by_type'].items():
        print(f"  {doc_type}: {count}")
    
    print(f"\nBy Domain:")
    for domain, count in class_report['by_domain'].items():
        print(f"  {domain}: {count}")
    
    print(f"\nBy Language:")
    for lang, count in class_report['by_language'].items():
        print(f"  {lang}: {count}")
    
    print(f"\nCode-containing: {class_report['code_containing']}")
    print(f"Math-containing: {class_report['math_containing']}")
    
    return classified_docs


def test_data_quality():
    """Test data quality validation"""
    print("\n" + "="*70)
    print("TEST 6: DATA QUALITY VALIDATION")
    print("="*70)
    
    # Run full pipeline first
    classified_docs = test_full_pipeline()
    
    if not classified_docs:
        print("❌ No documents to validate")
        return
    
    # Validate
    validator = DataValidator()
    results = validator.validate_documents(classified_docs)
    
    # Print report
    validator.print_report(results)
    
    return results


def main():
    """Run all Phase 1 tests"""
    print("\n" + "="*70)
    print(" PHASE 1 COMPLETE TEST SUITE")
    print(" Multi-Format Extraction & Classification")
    print("="*70)
    
    print("\nThis will test:")
    print("1. PDF slide extraction")
    print("2. DOCX course info extraction")
    print("3. FAQ Q&A parsing")
    print("4. Document classification")
    print("5. Full pipeline on all files")
    print("6. Data quality validation")
    
    print("\n⚠️  IMPORTANT: Update file paths in this script if needed!")
    input("\nPress Enter to start testing...")
    
    try:
        # Run tests
        pdf_docs = test_pdf_extraction()
        docx_docs = test_docx_extraction()
        faq_docs = test_faq_extraction()
        classified = test_classification()
        
        # Full pipeline with validation
        validation = test_data_quality()
        
        # Final summary
        print("\n" + "="*70)
        print(" PHASE 1 TEST SUMMARY")
        print("="*70)
        
        if validation and validation.get("validation_passed"):
            print("\n✅ ALL TESTS PASSED")
            print("\nNext steps:")
            print("1. Review the classification report above")
            print("2. Check that document types are correctly identified")
            print("3. Verify FAQ Q&A pairs are properly extracted")
            print("4. Proceed to Phase 2 - Smart Chunking")
        else:
            print("\n⚠️  SOME ISSUES DETECTED")
            print("\nReview the validation report above and fix issues before Phase 2")
        
        print("\n" + "="*70)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
