"""
PHASE 2 TEST - Smart Chunking Validation

Tests:
1. Chunking by document type
2. Code block preservation
3. Q&A pair integrity
4. Chunk size distribution
5. Metadata preservation

Run after Phase 1 to validate chunking quality.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from src.ingestion.multi_format_extractor import MultiFormatExtractor
    from src.ingestion.document_classifier import DocumentClassifier
    from src.ingestion.faq_parser import parse_faq_file
    from src.preprocessing.smart_chunker import SmartChunker
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure all Phase 1 and Phase 2 files are installed")
    sys.exit(1)


def load_all_documents():
    """Load and classify all documents from Phase 1"""
    print("\n📥 Loading documents from Phase 1...")
    
    data_dir = Path("data/raw/mk")
    extractor = MultiFormatExtractor()
    classifier = DocumentClassifier()
    
    all_documents = []
    
    # Extract PDFs
    pdf_files = list(data_dir.glob("*.pdf"))
    for pdf_file in pdf_files:
        docs = extractor.extract_document(str(pdf_file))
        all_documents.extend(docs)
    
    # Extract DOCX - special handling for FAQ
    docx_files = list(data_dir.glob("*.docx"))
    for docx_file in docx_files:
        filename = docx_file.name.lower()
        
        # Use FAQ parser for FAQ file
        if 'faq' in filename or 'прашања' in filename or 'често' in filename:
            print(f"  Using FAQ parser for: {docx_file.name}")
            docs = parse_faq_file(str(docx_file))
        else:
            docs = extractor.extract_document(str(docx_file))
        
        all_documents.extend(docs)
    
    # Classify all
    classified_docs = classifier.classify_batch(all_documents)
    
    print(f"✓ Loaded {len(classified_docs)} documents")
    print(f"  FAQ documents: {sum(1 for d in classified_docs if d.get('classification', {}).get('type') == 'faq')}")
    
    return classified_docs


def test_chunking():
    """Test smart chunking"""
    print("\n" + "="*70)
    print("TEST 1: SMART CHUNKING")
    print("="*70)
    
    # Load documents
    documents = load_all_documents()
    
    # Chunk them
    chunker = SmartChunker(
        target_chunk_size=1000,
        max_chunk_size=1500,
        min_chunk_size=300
    )
    
    print("\n🔄 Chunking documents...")
    chunks = chunker.chunk_documents(documents)
    
    print(f"\n✓ Created {len(chunks)} chunks from {len(documents)} documents")
    
    # Show stats
    stats = chunker.get_stats()
    print(f"\n📊 Chunking Stats:")
    print(f"  Pages merged: {stats['pages_merged']}")
    print(f"  Code blocks preserved: {stats['code_blocks_preserved']}")
    print(f"  Q&A pairs kept intact: {stats['qa_pairs_kept']}")
    
    return chunks


def test_chunk_types(chunks):
    """Test chunk type distribution"""
    print("\n" + "="*70)
    print("TEST 2: CHUNK TYPE DISTRIBUTION")
    print("="*70)
    
    from collections import Counter
    
    types = Counter(c.get('type') for c in chunks)
    
    print(f"\nChunks by type:")
    for chunk_type, count in types.items():
        print(f"  {chunk_type}: {count}")
    
    return types


def test_code_preservation(chunks):
    """Test if code blocks are preserved correctly"""
    print("\n" + "="*70)
    print("TEST 3: CODE BLOCK PRESERVATION")
    print("="*70)
    
    code_chunks = [c for c in chunks if c.get('metadata', {}).get('has_code')]
    complete_code = [c for c in code_chunks if c.get('metadata', {}).get('complete_code')]
    incomplete_code = len(code_chunks) - len(complete_code)
    
    print(f"\nCode-containing chunks: {len(code_chunks)}")
    print(f"  Complete code blocks: {len(complete_code)} ({len(complete_code)/len(code_chunks)*100:.1f}%)")
    print(f"  Incomplete blocks: {incomplete_code} ({incomplete_code/len(code_chunks)*100:.1f}%)")
    
    # Show examples
    print(f"\n--- Example: Complete Code Chunk ---")
    if complete_code:
        example = complete_code[0]
        print(f"Source: {example['source']}")
        print(f"Pages: {example.get('pages', [])}")
        print(f"Text preview (first 400 chars):")
        print(example['text'][:400])
        print("...")
    
    if incomplete_code > 0:
        print(f"\n--- Example: Incomplete Code Chunk ---")
        incomplete_chunks = [c for c in code_chunks if not c.get('metadata', {}).get('complete_code')]
        if incomplete_chunks:
            example = incomplete_chunks[0]
            print(f"Source: {example['source']}")
            print(f"Pages: {example.get('pages', [])}")
            print(f"Text preview (first 400 chars):")
            print(example['text'][:400])
            print("...")
            print("⚠️  This chunk has incomplete code - may need manual review")


def test_faq_integrity(chunks):
    """Test if FAQ Q&A pairs are kept intact"""
    print("\n" + "="*70)
    print("TEST 4: FAQ Q&A PAIR INTEGRITY")
    print("="*70)
    
    faq_chunks = [c for c in chunks if c.get('type') == 'faq_chunk']
    
    print(f"\nFAQ chunks: {len(faq_chunks)}")
    
    # Show first 2 examples
    for i, chunk in enumerate(faq_chunks[:2], 1):
        print(f"\n--- FAQ Chunk {i} ---")
        meta = chunk.get('metadata', {})
        print(f"Question: {meta.get('question', '')[:150]}...")
        print(f"Answer: {meta.get('answer', '')[:150]}...")
        print(f"Total length: {meta.get('char_count')} chars")


def test_chunk_sizes(chunks):
    """Test chunk size distribution"""
    print("\n" + "="*70)
    print("TEST 5: CHUNK SIZE DISTRIBUTION")
    print("="*70)
    
    sizes = [len(c.get('text', '')) for c in chunks]
    
    avg_size = sum(sizes) / len(sizes)
    min_size = min(sizes)
    max_size = max(sizes)
    
    print(f"\nChunk sizes:")
    print(f"  Average: {avg_size:.0f} chars")
    print(f"  Min: {min_size} chars")
    print(f"  Max: {max_size} chars")
    
    # Size categories
    tiny = sum(1 for s in sizes if s < 300)
    small = sum(1 for s in sizes if 300 <= s < 800)
    medium = sum(1 for s in sizes if 800 <= s < 1500)
    large = sum(1 for s in sizes if s >= 1500)
    
    print(f"\n  Distribution:")
    print(f"    Tiny (<300): {tiny} ({tiny/len(sizes)*100:.1f}%)")
    print(f"    Small (300-800): {small} ({small/len(sizes)*100:.1f}%)")
    print(f"    Medium (800-1500): {medium} ({medium/len(sizes)*100:.1f}%)")
    print(f"    Large (1500+): {large} ({large/len(sizes)*100:.1f}%)")
    
    # Warnings
    if tiny > len(sizes) * 0.2:
        print(f"\n⚠️  Warning: {tiny} chunks are very small - may need adjustment")


def test_metadata_preservation(chunks):
    """Test if metadata is preserved correctly"""
    print("\n" + "="*70)
    print("TEST 6: METADATA PRESERVATION")
    print("="*70)
    
    # Check if essential metadata exists
    with_classification = sum(1 for c in chunks if 'classification' in c)
    with_source = sum(1 for c in chunks if 'source' in c)
    with_metadata = sum(1 for c in chunks if 'metadata' in c)
    
    print(f"\nMetadata coverage:")
    print(f"  Has classification: {with_classification}/{len(chunks)} ({with_classification/len(chunks)*100:.1f}%)")
    print(f"  Has source: {with_source}/{len(chunks)} ({with_source/len(chunks)*100:.1f}%)")
    print(f"  Has metadata: {with_metadata}/{len(chunks)} ({with_metadata/len(chunks)*100:.1f}%)")
    
    # Show example
    print(f"\n--- Example Chunk Metadata ---")
    if chunks:
        chunk = chunks[0]
        print(f"Chunk ID: {chunk.get('chunk_id')}")
        print(f"Type: {chunk.get('type')}")
        print(f"Source: {chunk.get('source')}")
        print(f"Classification: {chunk.get('classification', {})}")
        print(f"Metadata: {chunk.get('metadata', {})}")


def validate_phase2(chunks):
    """Validate Phase 2 completion criteria"""
    print("\n" + "="*70)
    print("PHASE 2 VALIDATION")
    print("="*70)
    
    # Criteria
    criteria = {
        "Total chunks created": len(chunks) > 0,
        "Average chunk size 800-1500": 800 <= sum(len(c.get('text', '')) for c in chunks)/len(chunks) <= 1500,
        "Code chunks have metadata": all(c.get('metadata', {}).get('has_code') is not None for c in chunks if 'code' in c.get('text', '').lower()),
        "FAQ chunks intact": all(c.get('metadata', {}).get('is_qa_pair') for c in chunks if c.get('type') == 'faq_chunk'),
        "All chunks have IDs": all('chunk_id' in c for c in chunks),
        "All chunks have classification": all('classification' in c for c in chunks),
    }
    
    print("\n✓ Validation Criteria:")
    all_pass = True
    for criterion, passed in criteria.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {criterion}")
        if not passed:
            all_pass = False
    
    return all_pass


def main():
    """Run all Phase 2 tests"""
    print("\n" + "="*70)
    print(" PHASE 2 TEST SUITE - Smart Chunking")
    print("="*70)
    
    print("\nThis will test:")
    print("1. Smart chunking by document type")
    print("2. Chunk type distribution")
    print("3. Code block preservation")
    print("4. FAQ Q&A pair integrity")
    print("5. Chunk size distribution")
    print("6. Metadata preservation")
    
    input("\nPress Enter to start testing...")
    
    try:
        # Run tests
        chunks = test_chunking()
        test_chunk_types(chunks)
        test_code_preservation(chunks)
        test_faq_integrity(chunks)
        test_chunk_sizes(chunks)
        test_metadata_preservation(chunks)
        
        # Validate
        passed = validate_phase2(chunks)
        
        # Summary
        print("\n" + "="*70)
        print(" PHASE 2 TEST SUMMARY")
        print("="*70)
        
        if passed:
            print("\n✅ ALL TESTS PASSED")
            print("\nNext steps:")
            print("1. Review chunk examples above")
            print("2. Verify code blocks are complete")
            print("3. Check chunk sizes are appropriate")
            print("4. Proceed to Phase 3 - Vector Store Integration")
        else:
            print("\n⚠️  SOME CRITERIA NOT MET")
            print("\nReview the validation results above")
        
        print("\n" + "="*70)
        
        # Return chunks for inspection
        return chunks
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    chunks = main()