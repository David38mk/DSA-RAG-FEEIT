"""
Universal Document Loader - Loads from both mk/ and en/ folders

This script loads ALL documents from both Macedonian and English folders,
properly classifies them, chunks them, and prepares for vectorization.

Use this to rebuild your complete dataset including the English textbook.
"""

from pathlib import Path
from typing import List, Dict


def load_all_documents() -> List[Dict]:
    """
    Load and process documents from BOTH mk/ and en/ folders.
    
    Returns:
        List of classified documents ready for chunking
    """
    try:
        from src.ingestion.multi_format_extractor import MultiFormatExtractor
        from src.ingestion.document_classifier import DocumentClassifier
        from src.ingestion.faq_parser import parse_faq_file
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running from project root")
        return []
    
    print("\n" + "="*70)
    print(" LOADING ALL DOCUMENTS (Macedonian + English)")
    print("="*70)
    
    extractor = MultiFormatExtractor()
    classifier = DocumentClassifier()
    
    all_documents = []
    
    # Define both data directories
    data_dirs = [
        Path("data/raw/mk"),
        Path("data/raw/en")
    ]
    
    for data_dir in data_dirs:
        if not data_dir.exists():
            print(f"\n⚠️  Directory not found: {data_dir}")
            print(f"   Creating directory...")
            data_dir.mkdir(parents=True, exist_ok=True)
            continue
        
        print(f"\n📁 Processing directory: {data_dir}")
        print("-" * 70)
        
        # Extract PDFs
        pdf_files = list(data_dir.glob("*.pdf"))
        print(f"\n📄 Found {len(pdf_files)} PDF files")
        
        for i, pdf_file in enumerate(pdf_files, 1):
            print(f"  [{i}/{len(pdf_files)}] Extracting: {pdf_file.name}")
            try:
                docs = extractor.extract_document(str(pdf_file))
                all_documents.extend(docs)
                print(f"      ✓ Extracted {len(docs)} pages")
            except Exception as e:
                print(f"      ✗ Error: {e}")
        
        # Extract DOCX with FAQ handling
        docx_files = list(data_dir.glob("*.docx"))
        print(f"\n📝 Found {len(docx_files)} DOCX files")
        
        for i, docx_file in enumerate(docx_files, 1):
            filename = docx_file.name.lower()
            
            # Use FAQ parser for FAQ files
            if 'faq' in filename or 'прашања' in filename or 'често' in filename:
                print(f"  [{i}/{len(docx_files)}] FAQ Parsing: {docx_file.name}")
                try:
                    docs = parse_faq_file(str(docx_file))
                    all_documents.extend(docs)
                    print(f"      ✓ Extracted {len(docs)} Q&A pairs")
                except Exception as e:
                    print(f"      ✗ Error: {e}")
            else:
                print(f"  [{i}/{len(docx_files)}] Extracting: {docx_file.name}")
                try:
                    docs = extractor.extract_document(str(docx_file))
                    all_documents.extend(docs)
                    print(f"      ✓ Extracted {len(docs)} sections")
                except Exception as e:
                    print(f"      ✗ Error: {e}")
    
    # Classify all documents
    print(f"\n🔍 Classifying {len(all_documents)} documents...")
    classified_docs = classifier.classify_batch(all_documents)
    
    # Summary statistics
    print("\n" + "="*70)
    print(" EXTRACTION SUMMARY")
    print("="*70)
    
    print(f"\nTotal documents: {len(classified_docs)}")
    
    # By type
    type_counts = {}
    for doc in classified_docs:
        doc_type = doc.get("classification", {}).get("type", "unknown")
        type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
    
    print("\nBy type:")
    for doc_type, count in sorted(type_counts.items()):
        print(f"  {doc_type}: {count}")
    
    # By language
    lang_counts = {}
    for doc in classified_docs:
        lang = doc.get("classification", {}).get("language", "unknown")
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
    
    print("\nBy language:")
    for lang, count in sorted(lang_counts.items()):
        print(f"  {lang}: {count}")
    
    # By source directory
    mk_count = sum(1 for d in classified_docs if "data/raw/mk" in d.get("source", "") or "data\\raw\\mk" in d.get("source", ""))
    en_count = sum(1 for d in classified_docs if "data/raw/en" in d.get("source", "") or "data\\raw\\en" in d.get("source", ""))
    
    print("\nBy source:")
    print(f"  Macedonian (mk/): {mk_count}")
    print(f"  English (en/): {en_count}")
    
    print("\n" + "="*70)
    
    return classified_docs


def load_and_chunk_all() -> List[Dict]:
    """
    Load all documents AND chunk them.
    
    Returns:
        List of optimized chunks ready for vectorization
    """
    from src.preprocessing.smart_chunker import SmartChunker
    
    # Load documents
    documents = load_all_documents()
    
    if not documents:
        print("\n❌ No documents loaded!")
        return []
    
    # Chunk them
    print("\n" + "="*70)
    print(" CHUNKING DOCUMENTS")
    print("="*70)
    
    chunker = SmartChunker()
    chunks = chunker.chunk_documents(documents)
    
    print(f"\n✓ Created {len(chunks)} optimized chunks")
    
    # Chunk statistics
    chunk_types = {}
    for chunk in chunks:
        chunk_type = chunk.get("type", "unknown")
        chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
    
    print("\nChunks by type:")
    for chunk_type, count in sorted(chunk_types.items()):
        print(f"  {chunk_type}: {count}")
    
    # Size distribution
    sizes = [len(chunk.get("text", "")) for chunk in chunks]
    avg_size = sum(sizes) / len(sizes) if sizes else 0
    
    print(f"\nChunk sizes:")
    print(f"  Average: {int(avg_size)} chars")
    print(f"  Min: {min(sizes)} chars")
    print(f"  Max: {max(sizes)} chars")
    
    return chunks


if __name__ == "__main__":
    print("Universal Document Loader")
    print("Loads documents from both data/raw/mk/ and data/raw/en/")
    print("\nUsage:")
    print("  from load_all_documents import load_all_documents, load_and_chunk_all")
    print("  documents = load_all_documents()  # Just extract")
    print("  chunks = load_and_chunk_all()     # Extract + chunk")
