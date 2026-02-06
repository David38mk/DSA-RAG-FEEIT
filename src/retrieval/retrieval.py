from src.embeddings.embedder import Embedder
from src.vectorstore.chroma_store import ChromaStore

class Retriever:
    def __init__(self, n_results=5):
        self.embedder = Embedder()
        self.store = ChromaStore()
        self.n_results = n_results

    def retrieve(self, query: str, where: dict | None = None):
        query_embedding = self.embedder.embed_query(query)

        results = self.store.query(
            embedding=query_embedding,
            n_results=self.n_results,
            where=where
        )

        return results
