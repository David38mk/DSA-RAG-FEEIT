import json
from pathlib import Path
from uuid import uuid4

from src.embeddings.embedder import Embedder
from src.vectorstore.chroma_store import ChromaStore


DOCUMENTS_PATH = Path("data/processed/documents.json")


def main():
    with open(DOCUMENTS_PATH, "r", encoding="utf-8") as f:
        documents = json.load(f)

    texts = [doc["text"] for doc in documents]
    metadatas = [doc["metadata"] for doc in documents]
    ids = [str(uuid4()) for _ in documents]

    embedder = Embedder()
    embeddings = embedder.embed_documents(texts)

    store = ChromaStore()
    store.add_documents(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas
    )

    print(f"Indexed {len(texts)} documents into ChromaDB")


if __name__ == "__main__":
    main()
