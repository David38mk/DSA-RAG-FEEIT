"""
Run the existing EvaluationFramework against the JSON test set and write a
timestamped JSON result file under evaluation/results/.

Usage (from repo root):
    python -m evaluation.scripts.run_routing_eval
"""

import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "evaluation" / "results"

sys.path.insert(0, str(REPO_ROOT))

from src.evaluation.evaluation_framework import EvaluationFramework
from src.vectorstore.vector_store_manager import VectorStoreManager
from src.retrieval.hybrid_smart_retriever import HybridSmartRetriever
from src.llm.rag_pipeline import RAGPipeline
from src.llm.groq_generator import GroqGenerator


def build_pipeline() -> RAGPipeline:
    vsm = VectorStoreManager(collection_name="dsa_rag_test")
    vsm.create_collection(reset=False)
    retriever = HybridSmartRetriever(vsm)
    generator = GroqGenerator(model_name="llama-3.3-70b-versatile")
    return RAGPipeline(vsm, retriever, generator)


def main() -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    from evaluation.scripts._keys import load_groq_api_key
    load_groq_api_key()
    pipeline = build_pipeline()
    evaluator = EvaluationFramework()
    test_set = evaluator.create_test_set()
    aggregated = evaluator.run_evaluation(pipeline, test_set=test_set)
    evaluator.print_report(aggregated)

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out_path = RESULTS_DIR / f"{stamp}_routing_eval.json"
    payload = {
        "timestamp": stamp,
        "test_set_size": len(test_set),
        "aggregated": aggregated,
        "per_query": evaluator.results,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=float)
    print(f"\nWrote: {out_path.relative_to(REPO_ROOT)}")
    return out_path


if __name__ == "__main__":
    main()
