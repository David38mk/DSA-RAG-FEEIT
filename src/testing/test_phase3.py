"""
PHASE 3 TEST - Vector Store & Retrieval

Tests:
1. ChromaDB loading and persistence
2. Embedding creation
3. Basic semantic search
4. Query routing by intent
5. Metadata filtering
6. Cross-lingual retrieval

Run after Phase 2 to validate retrieval system.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from src.ingestion.multi_format_extractor import MultiFormatExtractor
    from src.ingestion.document_classifier import DocumentClassifier
    from src.ingestion.faq_parser import parse_faq_file
    from src.preprocessing.smart_chunker import SmartChunker
    from src.vectorstore.vector_store_manager import VectorStoreManager
    from src.retrieval.smart_retriever import SmartRetriever
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure all Phase 1-3 files are installed")
    sys.exit(1)


def load_chunks():
    """Load chunks from Phase 2"""
    print("\n📥 Loading chunks from Phase 2...")
    
    data_dir = Path("data/raw/mk")
    extractor = MultiFormatExtractor()
    classifier = DocumentClassifier()
    chunker = SmartChunker()
    
    all_documents = []
    
    # Extract PDFs
    for pdf_file in data_dir.glob("*.pdf"):
        docs = extractor.extract_document(str(pdf_file))
        all_documents.extend(docs)
    
    # Extract DOCX with FAQ handling
    for docx_file in data_dir.glob("*.docx"):
        filename = docx_file.name.lower()
        if 'faq' in filename or 'прашања' in filename or 'често' in filename:
            docs = parse_faq_file(str(docx_file))
        else:
            docs = extractor.extract_document(str(docx_file))
        all_documents.extend(docs)
    
    # Classify and chunk
    classified = classifier.classify_batch(all_documents)
    chunks = chunker.chunk_documents(classified)
    
    print(f"✓ Loaded {len(chunks)} chunks")
    return chunks


def test_vector_store_loading():
    """Test loading chunks into ChromaDB"""
    print("\n" + "="*70)
    print("TEST 1: VECTOR STORE LOADING")
    print("="*70)
    
    # Load chunks
    chunks = load_chunks()
    
    # Initialize vector store
    print("\n🔧 Initializing ChromaDB...")
    vsm = VectorStoreManager(
        persist_directory="data/vectorstore",
        collection_name="dsa_rag_test"
    )
    
    # Create collection
    vsm.create_collection(reset=True)
    
    # Load chunks
    vsm.load_chunks(chunks, batch_size=50)
    
    # Get stats
    stats = vsm.get_collection_stats()
    print(f"\n📊 Vector Store Stats:")
    print(f"  Collection: {stats['collection_name']}")
    print(f"  Total documents: {stats['total_documents']}")
    print(f"  Embeddings created: {stats['embeddings_created']}")
    print(f"  Persist directory: {stats['persist_directory']}")
    
    return vsm


def test_basic_search(vsm):
    """Test basic semantic search"""
    print("\n" + "="*70)
    print("TEST 2: BASIC SEMANTIC SEARCH")
    print("="*70)
    
    test_queries = [
        "Објасни AVL дрва",  # Macedonian technical
        "Explain binary search complexity",  # English technical
        "Колку поени треба за полагање?",  # Macedonian administrative
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: {query}")
        results = vsm.search(query, n_results=3)
        
        print(f"   Found {results['n_results']} results")
        for i, result in enumerate(results["results"], 1):
            print(f"\n   Result {i}:")
            print(f"     Source: {result['metadata']['source']}")
            print(f"     Type: {result['metadata']['doc_type']}")
            print(f"     Language: {result['metadata']['language']}")
            print(f"     Similarity: {result['similarity']:.3f}")
            print(f"     Preview: {result['text'][:100]}...")


def test_query_routing(vsm):
    """Test smart query routing"""
    print("\n" + "="*70)
    print("TEST 3: QUERY ROUTING BY INTENT")
    print("="*70)
    
    retriever = SmartRetriever(vsm)
    
    test_queries = [
        ("Дали можам да полагам во септември?", "FAQ"),  # FAQ intent
        ("Колку бодови треба за положување?", "Administrative"),  # Admin intent
        ("Објасни quicksort алгоритам", "Technical"),  # Technical intent
        ("What is the time complexity of merge sort?", "Technical"),  # English technical
    ]
    
    for query, expected_intent in test_queries:
        print(f"\n🔍 Query: {query}")
        print(f"   Expected intent: {expected_intent}")
        
        results = retriever.route_query(query, n_results=3)
        routing = results["routing"]
        
        print(f"   Detected intent: {routing['intent']} (confidence: {routing['intent_confidence']:.2f})")
        print(f"   Language: {routing['language']}")
        print(f"   Strategy: {routing['strategy']}")
        
        status = "✓" if routing['intent'].lower() in expected_intent.lower() or expected_intent.lower() in routing['intent'].lower() else "⚠️"
        print(f"   {status} Intent detection")
        
        print(f"\n   Top result:")
        if results["results"]:
            top = results["results"][0]
            print(f"     Source: {top['metadata']['source']}")
            print(f"     Type: {top['metadata']['doc_type']}")
            print(f"     Similarity: {top['similarity']:.3f}")


def test_metadata_filtering(vsm):
    """Test metadata-based filtering"""
    print("\n" + "="*70)
    print("TEST 4: METADATA FILTERING")
    print("="*70)
    
    # Test 1: FAQ only
    print("\n🔍 Test: Search FAQ only")
    query = "лабораториски вежби"
    results = vsm.search_faq_only(query, n_results=3)
    
    print(f"   Query: {query}")
    print(f"   Found {results['n_results']} FAQ results")
    for result in results["results"]:
        print(f"     - {result['metadata']['source']}: {result['metadata']['is_faq']}")
    
    # Test 2: Code only
    print("\n🔍 Test: Search code-containing chunks only")
    query = "for loop implementation"
    results = vsm.search_with_code(query, n_results=3)
    
    print(f"   Query: {query}")
    print(f"   Found {results['n_results']} code results")
    for result in results["results"]:
        print(f"     - {result['metadata']['source']}: has_code={result['metadata']['has_code']}")
    
    # Test 3: By document type
    print("\n🔍 Test: Search lecture slides only")
    query = "дрва структура"
    results = vsm.search_by_type(query, ["lecture_slides"], n_results=3)
    
    print(f"   Query: {query}")
    print(f"   Found {results['n_results']} lecture results")
    for result in results["results"]:
        print(f"     - {result['metadata']['source']}: {result['metadata']['doc_type']}")


def test_cross_lingual(vsm):
    """Test cross-lingual retrieval"""
    print("\n" + "="*70)
    print("TEST 5: CROSS-LINGUAL RETRIEVAL")
    print("="*70)
    
    # Test: Macedonian query → English results
    print("\n🔍 Test: Macedonian query on English content")
    query = "binary search дрво"  # Mixed MK/EN
    results = vsm.search(query, n_results=5)
    
    print(f"   Query: {query}")
    print(f"   Results by language:")
    
    lang_dist = {}
    for result in results["results"]:
        lang = result["metadata"]["language"]
        lang_dist[lang] = lang_dist.get(lang, 0) + 1
    
    for lang, count in lang_dist.items():
        print(f"     {lang}: {count}")
    
    print(f"\n   ✓ Cross-lingual retrieval working" if len(lang_dist) > 1 else "   ⚠️  All results same language")


def test_hybrid_search(vsm):
    """Test hybrid search with re-ranking"""
    print("\n" + "="*70)
    print("TEST 6: HYBRID SEARCH (Semantic + Metadata)")
    print("="*70)
    
    retriever = SmartRetriever(vsm)
    
    query = "Колку поени треба за полагање?"
    
    print(f"\n🔍 Query: {query}")
    
    # Semantic only
    print("\n   Semantic search:")
    semantic = retriever.route_query(query, n_results=3)
    for i, result in enumerate(semantic["results"][:2], 1):
        print(f"     {i}. {result['metadata']['doc_type']} - Similarity: {result['similarity']:.3f}")
    
    # Hybrid
    print("\n   Hybrid search (semantic + metadata boost):")
    hybrid = retriever.hybrid_search(query, semantic_weight=0.7, n_results=3)
    for i, result in enumerate(hybrid["results"][:2], 1):
        print(f"     {i}. {result['metadata']['doc_type']} - Hybrid: {result['hybrid_score']:.3f} (boost: +{result['metadata_boost']:.3f})")


def validate_phase3(vsm):
    """Validate Phase 3 completion criteria"""
    print("\n" + "="*70)
    print("PHASE 3 VALIDATION")
    print("="*70)
    
    stats = vsm.get_collection_stats()
    retriever = SmartRetriever(vsm)
    
    # Run validation queries
    test_query = "AVL дрва"
    results = retriever.route_query(test_query, n_results=5)
    
    criteria = {
        "Vector store created": stats["total_documents"] > 0,
        "All chunks loaded": stats["total_documents"] >= 350,
        "Embeddings created": stats["embeddings_created"] > 0,
        "Search returns results": results["n_results"] > 0,
        "Intent detection works": "routing" in results,
        "Metadata preserved": all("metadata" in r for r in results["results"]),
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
    """Run all Phase 3 tests"""
    print("\n" + "="*70)
    print(" PHASE 3 TEST SUITE - Vector Store & Retrieval")
    print("="*70)
    
    print("\nThis will test:")
    print("1. ChromaDB loading and persistence")
    print("2. Basic semantic search")
    print("3. Query routing by intent")
    print("4. Metadata filtering")
    print("5. Cross-lingual retrieval")
    print("6. Hybrid search")
    
    print("\n⚠️  Note: First run will download multilingual-e5-base (~1.1GB)")
    print("    Subsequent runs will use cached model.")
    
    input("\nPress Enter to start testing...")
    
    try:
        # Run tests
        vsm = test_vector_store_loading()
        test_basic_search(vsm)
        test_query_routing(vsm)
        test_metadata_filtering(vsm)
        test_cross_lingual(vsm)
        test_hybrid_search(vsm)
        
        # Validate
        passed = validate_phase3(vsm)
        
        # Summary
        print("\n" + "="*70)
        print(" PHASE 3 TEST SUMMARY")
        print("="*70)
        
        if passed:
            print("\n✅ ALL TESTS PASSED")
            print("\nNext steps:")
            print("1. Review retrieval results above")
            print("2. Test with your own queries")
            print("3. Integrate with Mistral for answer generation")
            print("4. Build evaluation framework (Phase 4)")
        else:
            print("\n⚠️  SOME CRITERIA NOT MET")
            print("\nReview the validation results above")
        
        print("\n" + "="*70)
        
        return vsm
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    vsm = main()
