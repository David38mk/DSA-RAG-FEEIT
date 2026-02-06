from src.retrieval.retrieval import Retriever

def print_results(results):
    docs = results["documents"][0]
    metas = results["metadatas"][0]

    for i, (doc, meta) in enumerate(zip(docs, metas), 1):
        print(f"\n--- Result {i} ---")
        print(f"Type: {meta.get('type')}")
        print(f"Language: {meta.get('language')}")
        print(f"Source: {meta.get('source')}")
        print(doc[:500])  # first 500 chars


def main():
    retriever = Retriever(n_results=5)

    print("\n=== TEST 1: English theory ===")
    res = retriever.retrieve("Explain AVL trees")
    print_results(res)

    print("\n=== TEST 2: Macedonian theory ===")
    res = retriever.retrieve("Објасни AVL дрва")
    print_results(res)

    print("\n=== TEST 3: Academic rules ===")
    res = retriever.retrieve("Колку поени се потребни за положување")
    print_results(res)


if __name__ == "__main__":
    main()
