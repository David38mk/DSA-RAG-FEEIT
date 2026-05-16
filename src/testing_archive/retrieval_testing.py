from src.vectorstore.vector_store_manager import VectorStoreManager
from src.retrieval.smart_retriever import SmartRetriever

# 1. Initialize the manager
COLLECTION_NAME = "dsa_rag_test" 
vsm = VectorStoreManager(collection_name=COLLECTION_NAME)

# 2. IMPORTANT: Initialize/Get the collection! 
# reset=False ensures we don't wipe existing data
vsm.create_collection(reset=False) 

# 3. Now check the count (vsm.collection is no longer None)
if vsm.collection is not None:
    doc_count = vsm.collection.count()
    print(f"--- Verification ---")
    print(f"✅ Connected to collection: {COLLECTION_NAME}")
    print(f"📊 Total documents found: {doc_count}")
    print(f"--------------------\n")
else:
    print("❌ Failed to initialize collection.")
    exit()

if doc_count == 0:
    print("⚠️ WARNING: Collection is empty. Run your ingestion script first!")
else:
    # 4. Run retrieval
    retriever = SmartRetriever(vsm)
    queries = ["Објасни quicksort", "What is Big O?"]

    for q in queries:
        results = retriever.route_query(q, n_results=3)
        retriever.print_results(results, max_chars=150)