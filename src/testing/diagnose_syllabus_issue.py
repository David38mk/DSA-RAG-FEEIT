# Save as diagnose_syllabus_issue.py
from docx import Document
import re

print("="*70)
print("DIAGNOSING SYLLABUS RETRIEVAL ISSUE")
print("="*70)

# Step 1: Check if Q&A exists in DOCX
print("\n[1] Checking FAQ DOCX file...")
try:
    doc = Document('data/raw/mk/Често поставувани прашања.docx')
    full_text = '\n'.join([p.text for p in doc.paragraphs])
    
    if 'сиже' in full_text:
        print("✓ Found 'сиже' in DOCX file")
        # Find the Q&A pair
        lines = full_text.split('\n')
        for i, line in enumerate(lines):
            if 'сиже' in line.lower():
                context = '\n'.join(lines[max(0,i-2):min(len(lines),i+10)])
                print(f"\nContext around 'сиже':")
                print(context[:500])
                break
    else:
        print("✗ 'сиже' NOT found in DOCX file!")
except Exception as e:
    print(f"✗ Error reading DOCX: {e}")

# Step 2: Check FAQ parser
print("\n[2] Testing FAQ parser...")
try:
    from src.ingestion.faq_parser import parse_faq_file
    
    pairs = parse_faq_file('data/raw/mk/Често поставувани прашања.docx')
    print(f"✓ Parsed {len(pairs)} Q&A pairs")
    
    # Look for syllabus
    found_syllabus = False
    for i, pair in enumerate(pairs):
        q = pair.get('question', '')
        a = pair.get('answer', '')
        if 'сиже' in q.lower() or 'сиже' in a.lower():
            found_syllabus = True
            print(f"\n✓ Found syllabus Q&A at pair #{i+1}")
            print(f"Question: {q[:150]}...")
            print(f"Answer: {a[:150]}...")
            break
    
    if not found_syllabus:
        print("\n✗ Syllabus Q&A NOT found in parsed pairs!")
        
except Exception as e:
    print(f"✗ Parser error: {e}")

# Step 3: Check vector store
print("\n[3] Testing vector store retrieval...")
try:
    from src.vectorstore.vector_store_manager import VectorStoreManager
    
    vsm = VectorStoreManager(collection_name="dsa_rag_test")
    vsm.create_collection(reset=False)
    
    # Try different queries
    test_queries = [
        "каде можам да најдам сиже",
        "официјално сиже",
        "syllabus",
        "Where can I find the syllabus"
    ]
    
    for query in test_queries:
        results = vsm.search(query, n_results=3)
        print(f"\nQuery: '{query}'")
        if results['results']:
            top = results['results'][0]
            print(f"  Top result: {top['metadata']['source']}")
            print(f"  Similarity: {top['similarity']:.3f}")
            print(f"  Preview: {top['text'][:100]}...")
            
            # Check if it's the right answer
            if 'сиже' in top['text'] or 'feit.ukim.edu.mk' in top['text']:
                print(f"  ✓ FOUND THE SYLLABUS ANSWER!")
            else:
                print(f"  ✗ Wrong document retrieved")
        else:
            print(f"  ✗ No results found")
            
except Exception as e:
    print(f"✗ Vector store error: {e}")

# Step 4: Check intent routing
print("\n[4] Testing intent classification...")
try:
    from src.retrieval.smart_retriever_v2 import SmartRetriever
    
    class MockVSM:
        def search(self, *args, **kwargs):
            return {"results": []}
    
    retriever = SmartRetriever(MockVSM())
    
    queries = [
        ("Каде можам да најдам официјално сиже?", "mk"),
        ("Where can I find the official syllabus?", "en")
    ]
    
    for query, expected_lang in queries:
        intent, conf = retriever.detect_intent(query)
        lang = retriever.detect_language(query)
        
        print(f"\nQuery: '{query}'")
        print(f"  Intent: {intent.value} (conf: {conf:.2f})")
        print(f"  Language: {lang}")
        
        if intent.value == "support":
            print(f"  ✓ Correctly routed to SUPPORT")
        else:
            print(f"  ✗ WRONG: Routed to {intent.value}, should be SUPPORT")
            
except Exception as e:
    print(f"✗ Retriever error: {e}")

print("\n" + "="*70)
print("DIAGNOSIS COMPLETE")
print("="*70)