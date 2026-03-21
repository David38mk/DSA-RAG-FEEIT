"""
REBUILD VECTORSTORE - Complete System Reset

This script:
1. Deletes corrupted ChromaDB
2. Loads ALL documents (Macedonian + English)
3. Chunks them intelligently
4. Creates fresh embeddings
5. Validates results

Run this to fix ChromaDB corruption and embed the English textbook.

Usage: python rebuild_vectorstore.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.ingestion.load_all_documents import load_and_chunk_all


def rebuild_vectorstore():
    """Complete vectorstore rebuild"""
    
    print("\n" + "="*70)
    print(" REBUILD VECTORSTORE - COMPLETE RESET")
    print("="*70)
    
    print("\n⚠️  This will:")
    print("  1. Delete existing vectorstore (if any)")
    print("  2. Load ALL documents (mk/ + en/)")
    print("  3. Create fresh embeddings")
    print("  4. Take 5-10 minutes")
    
    response = input("\nContinue? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Cancelled.")
        return
    
    # Step 1: Delete old vectorstore
    print("\n" + "="*70)
    print("STEP 1: Deleting old vectorstore")
    print("="*70)
    
    vectorstore_path = Path("data/vectorstore")
    if vectorstore_path.exists():
        import shutil
        print(f"\n🗑️  Deleting: {vectorstore_path}")
        shutil.rmtree(vectorstore_path)
        print("✓ Deleted")
    else:
        print("\n✓ No existing vectorstore found")
    
    # Step 2: Load and chunk all documents
    print("\n" + "="*70)
    print("STEP 2: Loading and chunking documents")
    print("="*70)
    
    chunks = load_and_chunk_all()
    
    if not chunks:
        print("\n❌ No chunks created! Check your data/ folder")
        print("   Make sure you have files in:")
        print("   - data/raw/mk/  (Macedonian files)")
        print("   - data/raw/en/  (English textbook)")
        return
    
    print(f"\n✓ Created {len(chunks)} chunks")
    
    # Step 3: Create embeddings
    print("\n" + "="*70)
    print("STEP 3: Creating embeddings (this takes time!)")
    print("="*70)
    
    try:
        from src.vectorstore.vector_store_manager import VectorStoreManager
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("   Make sure vector_store_manager.py is in src/vectorstore/")
        return
    
    print("\n🔧 Initializing VectorStoreManager...")
    print("   This will download multilingual-e5-base if not cached (~1.1GB)")
    
    vsm = VectorStoreManager(
        persist_directory="data/vectorstore",
        collection_name="dsa_rag_test"
    )
    
    print("\n✓ Creating collection...")
    vsm.create_collection(reset=True)
    
    print("\n📥 Loading chunks into vectorstore...")
    print(f"   Processing {len(chunks)} chunks in batches of 50...")
    print("   Estimated time: {:.1f} minutes".format(len(chunks) * 0.15 / 60))
    
    vsm.load_chunks(chunks, batch_size=50)
    
    # Step 4: Validate
    print("\n" + "="*70)
    print("STEP 4: Validating")
    print("="*70)
    
    stats = vsm.get_collection_stats()
    
    print(f"\n✓ Vector store created successfully!")
    print(f"\n📊 Statistics:")
    print(f"   Collection: {stats['collection_name']}")
    print(f"   Total documents: {stats['total_documents']}")
    print(f"   Embeddings created: {stats['embeddings_created']}")
    print(f"   Storage location: {stats['persist_directory']}")
    
    # Test query
    print("\n" + "="*70)
    print("STEP 5: Test Query")
    print("="*70)
    
    test_queries = [
        "AVL дрва",  # MK technical
        "Big O notation",  # EN technical
        "Колку поени треба?"  # MK support
    ]
    
    for query in test_queries:
        print(f"\n🔍 Testing: {query}")
        results = vsm.search(query, n_results=3)
        
        if results["results"]:
            top = results["results"][0]
            print(f"   ✓ Top result: {top['metadata']['source']}")
            print(f"     Similarity: {top['similarity']:.3f}")
            print(f"     Language: {top['metadata']['language']}")
        else:
            print("   ⚠️  No results found")
    
    # Final summary
    print("\n" + "="*70)
    print(" REBUILD COMPLETE!")
    print("="*70)
    
    print("\n✅ Your vectorstore is ready with:")
    print(f"   • {stats['total_documents']} chunks")
    print(f"   • Macedonian + English documents")
    print(f"   • Fresh embeddings")
    print(f"   • No corruption")
    
    print("\n📝 Next steps:")
    print("   1. Copy fixed smart_retriever.py to src/retrieval/")
    print("   2. Run Streamlit: streamlit run streamlit_app.py")
    print("   3. Test with both technical and support queries")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    rebuild_vectorstore()
