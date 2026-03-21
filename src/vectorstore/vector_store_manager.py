"""
Vector Store Manager - ChromaDB Integration

Handles:
- Loading chunks into ChromaDB
- Creating embeddings with multilingual-e5-base
- Metadata filtering and search
- Collection management

For DSA-RAG-FEEIT thesis project
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import numpy as np
from pathlib import Path


class VectorStoreManager:
    """Manage ChromaDB vector store for RAG system"""
    
    def __init__(self, 
                 persist_directory: str = "data/vectorstore",
                 collection_name: str = "dsa_rag_collection",
                 embedding_model: str = "intfloat/multilingual-e5-base"):
        """
        Initialize vector store manager.
        
        Args:
            persist_directory: Where to persist the vector database
            collection_name: Name of the collection
            embedding_model: HuggingFace model for embeddings
        """
        self.persist_dir = Path(persist_directory)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model
        
        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Load embedding model
        print(f"Loading embedding model: {embedding_model}")
        self._load_embedding_model()
        
        self.collection = None
        self.stats = {
            "documents_loaded": 0,
            "embeddings_created": 0,
            "searches_performed": 0
        }
    
    def _load_embedding_model(self):
        """Load the embedding model"""
        try:
            from sentence_transformers import SentenceTransformer
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            print(f"✓ Loaded {self.embedding_model_name}")
        except ImportError:
            print("❌ sentence-transformers not installed")
            print("Install with: pip install sentence-transformers")
            raise
    
    def create_collection(self, reset: bool = False):
        """
        Create or get the collection.
        
        Args:
            reset: If True, delete existing collection and create new one
        """
        if reset:
            try:
                self.client.delete_collection(self.collection_name)
                print(f"Deleted existing collection: {self.collection_name}")
            except:
                pass
        
        # Create collection with custom embedding function
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "DSA course RAG system - Macedonian/English"}
        )
        
        print(f"✓ Collection ready: {self.collection_name}")
        return self.collection
    
    def _prepare_text_for_embedding(self, text: str, doc_type: str = None) -> str:
        """
        Prepare text for E5 embedding model.
        
        E5 models require prefixes:
        - query: "query: <text>"
        - passage: "passage: <text>"
        """
        # For storage, we use passage prefix
        return f"passage: {text}"
    
    def _create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for list of texts"""
        # Prepare texts with E5 prefix
        prepared_texts = [self._prepare_text_for_embedding(t) for t in texts]
        
        # Generate embeddings
        embeddings = self.embedding_model.encode(
            prepared_texts,
            show_progress_bar=True,
            normalize_embeddings=True  # Important for cosine similarity
        )
        
        self.stats["embeddings_created"] += len(texts)
        
        return embeddings.tolist()
    
    def load_chunks(self, chunks: List[Dict], batch_size: int = 100):
        """
        Load chunks into vector store.
        
        Args:
            chunks: List of chunk dicts from Phase 2
            batch_size: Number of chunks to process at once
        """
        if not self.collection:
            self.create_collection()
        
        print(f"\n📥 Loading {len(chunks)} chunks into vector store...")
        
        # Process in batches
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            
            # Extract data
            ids = [chunk["chunk_id"] for chunk in batch]
            texts = [chunk["text"] for chunk in batch]
            
            # Create embeddings
            embeddings = self._create_embeddings(texts)
            
            # Prepare metadata (ChromaDB requires flat dicts)
            metadatas = []
            for chunk in batch:
                metadata = {
                    "source": chunk.get("source", "unknown"),
                    "type": chunk.get("type", "unknown"),
                    "chunk_index": chunk.get("chunk_index", 0),
                    
                    # Classification metadata
                    "doc_type": chunk.get("classification", {}).get("type", "unknown"),
                    "domain": chunk.get("classification", {}).get("domain", "unknown"),
                    "language": chunk.get("classification", {}).get("language", "unknown"),
                    
                    # Chunk metadata
                    "has_code": str(chunk.get("metadata", {}).get("has_code", False)),
                    "char_count": chunk.get("metadata", {}).get("char_count", 0),
                    
                    # Add special flags
                    "is_faq": str(chunk.get("type") == "faq_chunk"),
                    "is_admin": str(chunk.get("type") == "admin_chunk"),
                }
                
                # Add FAQ-specific metadata if available
                if chunk.get("type") == "faq_chunk":
                    metadata["question"] = chunk.get("metadata", {}).get("question", "")[:500]  # Truncate for storage
                
                metadatas.append(metadata)
            
            # Add to collection
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas
            )
            
            self.stats["documents_loaded"] += len(batch)
            
            if (i + batch_size) % 500 == 0:
                print(f"  Loaded {i + batch_size}/{len(chunks)} chunks...")
        
        print(f"✓ Loaded {len(chunks)} chunks successfully")
        print(f"  Total embeddings created: {self.stats['embeddings_created']}")
    
    def search(self, 
               query: str,
               n_results: int = 5,
               filter_metadata: Optional[Dict] = None) -> Dict:
        """
        Search the vector store.
        
        Args:
            query: Search query
            n_results: Number of results to return
            filter_metadata: ChromaDB where filter dict
            
        Returns:
            Dict with results
        """
        if not self.collection:
            raise ValueError("Collection not loaded. Call create_collection() first.")
        
        # Prepare query with E5 prefix
        query_text = f"query: {query}"
        
        # Create query embedding
        query_embedding = self.embedding_model.encode(
            query_text,
            normalize_embeddings=True
        ).tolist()
        
        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_metadata,
            include=["documents", "metadatas", "distances"]
        )
        
        self.stats["searches_performed"] += 1
        
        # Format results
        formatted_results = {
            "query": query,
            "n_results": len(results["ids"][0]),
            "results": []
        }
        
        for i in range(len(results["ids"][0])):
            result = {
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
                "similarity": 1 - results["distances"][0][i]  # Convert distance to similarity
            }
            formatted_results["results"].append(result)
        
        return formatted_results
    
    def search_by_type(self, 
                       query: str, 
                       doc_types: List[str],
                       n_results: int = 5) -> Dict:
        """
        Search filtered by document type.
        
        Args:
            query: Search query
            doc_types: List of doc types (e.g., ["lecture_slides", "faq"])
            n_results: Number of results
        """
        # Create filter
        if len(doc_types) == 1:
            filter_metadata = {"doc_type": doc_types[0]}
        else:
            # ChromaDB $in operator for multiple values
            filter_metadata = {"doc_type": {"$in": doc_types}}
        
        return self.search(query, n_results, filter_metadata)
    
    def search_faq_only(self, query: str, n_results: int = 3) -> Dict:
        """Search only FAQ documents"""
        filter_metadata = {"is_faq": "True"}
        return self.search(query, n_results, filter_metadata)
    
    def search_admin_only(self, query: str, n_results: int = 3) -> Dict:
        """Search only administrative documents"""
        filter_metadata = {"is_admin": "True"}
        return self.search(query, n_results, filter_metadata)
    
    def search_with_code(self, query: str, n_results: int = 5) -> Dict:
        """Search only documents containing code"""
        filter_metadata = {"has_code": "True"}
        return self.search(query, n_results, filter_metadata)
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about the collection"""
        if not self.collection:
            return {"error": "Collection not loaded"}
        
        count = self.collection.count()
        
        return {
            "collection_name": self.collection_name,
            "total_documents": count,
            "embeddings_created": self.stats["embeddings_created"],
            "searches_performed": self.stats["searches_performed"],
            "persist_directory": str(self.persist_dir)
        }
    
    def reset_collection(self):
        """Delete and recreate the collection"""
        self.create_collection(reset=True)
        self.stats = {
            "documents_loaded": 0,
            "embeddings_created": 0,
            "searches_performed": 0
        }


if __name__ == "__main__":
    print("Vector Store Manager")
    print("Usage: VectorStoreManager().load_chunks(chunks)")
