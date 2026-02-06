import chromadb
import os

class ChromaStore:
    def __init__(self, persist_directory="data/chroma"):
        """
        Initializes the ChromaDB client. 
        Using PersistentClient ensures the data is saved to disk automatically.
        """
        # Create the directory if it doesn't exist
        os.makedirs(persist_directory, exist_ok=True)
        self.persist_directory = persist_directory

        # The new way to initialize a local database in ChromaDB 0.4.0+
        self.client = chromadb.PersistentClient(path=self.persist_directory)

        # Get or create the collection
        self.collection = self.client.get_or_create_collection(
            name="dsa_documents"
        )

    def add_documents(self, ids, embeddings, documents, metadatas):
        """
        Adds vector embeddings and metadata to the collection.
        Data is saved to disk immediately; no .persist() call required.
        """
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        
        # Confirmation for the console
        print(f"Successfully added {len(ids)} documents to {self.persist_directory}")

    def query(self, embedding, n_results=5, where=None):
        """
        Queries the collection using a vector embedding.
        """
        return self.collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
            where=where
        )

    def get_count(self):
        """
        Returns the number of documents in the collection.
        Useful for debugging.
        """
        return self.collection.count()