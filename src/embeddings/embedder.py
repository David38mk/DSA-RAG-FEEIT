from sentence_transformers import SentenceTransformer

class Embedder:
    def __init__(self, model_name="intfloat/multilingual-e5-base"):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts):
        """
        texts: List[str]
        returns: List[List[float]]
        """
        # E5 expects "passage: " prefix
        texts = [f"passage: {t}" for t in texts]
        return self.model.encode(texts, show_progress_bar=True)

    def embed_query(self, query: str):
        query = f"query: {query}"
        return self.model.encode([query])[0]
