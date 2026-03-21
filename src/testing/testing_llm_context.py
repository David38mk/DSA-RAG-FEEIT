# Save as test_llm_context.py
from src.vectorstore.vector_store_manager import VectorStoreManager
from src.retrieval.hybrid_smart_retriever import HybridSmartRetriever
from src.llm.groq_generator import GroqGenerator

# Initialize
vsm = VectorStoreManager(collection_name="dsa_rag_test")
vsm.create_collection(reset=False)

retriever = HybridSmartRetriever(vsm, use_llm=False)  # Use rules for speed

# Query
query = "Каде можам да најдам официјално сиже за предметот?"

# Get retrieval results
results = retriever.route_query(query, n_results=15)

print("="*70)
print("CHUNKS BEING SENT TO LLM:")
print("="*70)

# Check each chunk
syllabus_found = False
for i, chunk in enumerate(results["results"], 1):
    print(f"\n[{i}] {chunk['metadata']['source']}")
    print(f"Similarity: {chunk['similarity']:.3f}")
    print(f"Length: {len(chunk['text'])} chars")
    
    # Check if this is the syllabus chunk
    if 'feit.ukim.edu.mk' in chunk['text'] and 'i-ciklus' in chunk['text']:
        print(">>> ✓✓✓ THIS IS THE SYLLABUS ANSWER! <<<")
        syllabus_found = True
        print(f"\nFull chunk text:")
        print(chunk['text'])
        print("\n" + "="*70)

if not syllabus_found:
    print("\n❌ SYLLABUS CHUNK NOT IN TOP 10 RESULTS!")
    print("This explains why LLM can't answer.")
else:
    print("\n✓ Syllabus chunk IS being sent to LLM")
    print("Problem must be in LLM prompt interpretation")

# Now test what LLM does with this
print("\n" + "="*70)
print("TESTING LLM RESPONSE:")
print("="*70)

generator = GroqGenerator()

# Build context manually
context_chunks = results["results"][:5]  # Top 5
context_text = ""
for i, chunk in enumerate(context_chunks, 1):
    context_text += f"\n[Извор {i}: {chunk['metadata']['source']}]\n"
    context_text += chunk['text']
    context_text += "\n\n"

print(f"Context length: {len(context_text)} chars")
print(f"Context preview (first 500 chars):")
print(context_text[:500])

# Generate answer
response = generator.generate(
    query=query,
    context=context_chunks,
    language="mk"
)

print("\n" + "="*70)
print("LLM RESPONSE:")
print("="*70)
print(response["answer"])