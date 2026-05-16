"""
PHASE 4 TEST - Full RAG Pipeline Demo
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.vectorstore.vector_store_manager import VectorStoreManager
from src.retrieval.smart_retriever import SmartRetriever
from src.llm.mistral_generator import MistralGenerator
from src.llm.rag_pipeline import RAGPipeline


def main():
    print("\n" + "="*70)
    print(" PHASE 4: RAG PIPELINE DEMO")
    print("="*70)
    
    # Load components
    print("\n🔧 Loading components...")
    vsm = VectorStoreManager(collection_name="dsa_rag_test") 
    vsm.create_collection(reset=False)
    
    # Check count to be sure
    count = vsm.collection.count()
    print(f"✅ Connected to: {vsm.collection_name} ({count} documents)")
    
    if count == 0:
        print("❌ Warning: Collection is empty. Retrieval will fail.")

    retriever = SmartRetriever(vsm)
    
    # Choose mode
    print("\nMistral mode:")
    print("  1. API (requires key)")
    print("  2. Local (requires Ollama)")
    print("  3. Skip (retrieval only)")
    
    choice = input("\nChoice (1/2/3): ").strip() or "3"
    
    generator = None
    if choice == "1":
        try:
            generator = MistralGenerator(mode="api")
        except:
            print("API failed, continuing retrieval-only")
    elif choice == "2":
        try:
            generator = MistralGenerator(mode="local", model_name="mistral:latest")
        except Exception as e:
            print(f"Local failed: {e}")
    
    # Test queries
    queries = [
        "Објасни AVL дрва",
        "What is quicksort complexity?",
        "Колку поени треба за полагање?",
    ]
    
    for q in queries:
        print(f"\n🔍 {q}")
        results = retriever.route_query(q, n_results=3)
        print(f"   {results['routing']['strategy']}")
        
        if results["results"]:
            print(f"   Top: {results['results'][0]['metadata']['source']}")
            print(f"   Similarity: {results['results'][0]['similarity']:.3f}")
        
        if generator:
            try:
                answer = generator.generate(q, results["results"])
                print(f"   Answer: {answer['answer'][:200]}...")
            except Exception as e:
                print(f"   Generation error: {e}")
    
    print("\n✅ Demo complete!")


if __name__ == "__main__":
    main()
