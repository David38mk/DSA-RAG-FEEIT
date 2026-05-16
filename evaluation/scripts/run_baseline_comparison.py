"""
Baseline comparison: RAG pipeline vs plain LLM (no retrieval).

Runs the routing test set through two configurations:
  A. Full RAG pipeline (retrieval + generation with context)
  B. Baseline: same LLM, same query, NO context, NO system prompt rules

Scores both with the existing keyword/topic heuristic and reports deltas.
This is the headline number the thesis defense will ask about:
"Does retrieval actually help, and by how much?"

Usage (from repo root):
    python -m evaluation.scripts.run_baseline_comparison
"""

import json
import sys
import time
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


MODEL_NAME = "llama-3.3-70b-versatile"


def build_rag_pipeline() -> RAGPipeline:
    vsm = VectorStoreManager(collection_name="dsa_rag_test")
    vsm.create_collection(reset=False)
    retriever = HybridSmartRetriever(vsm)
    generator = GroqGenerator(model_name=MODEL_NAME)
    return RAGPipeline(vsm, retriever, generator)


def baseline_generate(client, query: str, language: str) -> dict:
    """
    Plain LLM call. No retrieved context, no course-specific system prompt
    beyond identifying as a DSA assistant in the right language. This is the
    fair baseline: same model, same query, retrieval removed.
    """
    if language == "mk":
        system = (
            "Ти си асистент за курсот Податочни Структури и Анализа на Алгоритми. "
            "Одговори на македонски."
        )
        user = query
    else:
        system = (
            "You are an assistant for the Data Structures and Algorithms course. "
            "Answer in English."
        )
        user = query

    start = time.perf_counter()
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
        max_tokens=512,
        top_p=0.9,
    )
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    return {
        "answer": response.choices[0].message.content,
        "latency_ms": elapsed_ms,
    }


def main() -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    from evaluation.scripts._keys import load_groq_api_key
    from groq import Groq

    api_key = load_groq_api_key()
    groq_client = Groq(api_key=api_key)

    pipeline = build_rag_pipeline()
    evaluator = EvaluationFramework()
    test_set = evaluator.create_test_set()

    per_query = []
    rag_quality_scores = []
    baseline_quality_scores = []
    rag_latencies = []
    baseline_latencies = []

    print(f"\nBaseline comparison on {len(test_set)} queries...\n")

    for i, case in enumerate(test_set, 1):
        query = case["query"]
        expected_topics = case.get("expected_topics", [])
        language = case.get("language", "mk")

        print(f"[{i}/{len(test_set)}] {query}")

        rag_response = pipeline.query(query, n_results=7, language=language)
        rag_answer = rag_response.get("answer", "")
        rag_latency = rag_response.get("total_time_ms", 0)

        baseline_response = baseline_generate(groq_client, query, language)
        baseline_answer = baseline_response["answer"]
        baseline_latency = baseline_response["latency_ms"]

        rag_quality = evaluator.evaluate_answer_quality(query, rag_answer, expected_topics)
        baseline_quality = evaluator.evaluate_answer_quality(query, baseline_answer, expected_topics)

        rag_quality_scores.append(rag_quality["quality_score"])
        baseline_quality_scores.append(baseline_quality["quality_score"])
        rag_latencies.append(rag_latency)
        baseline_latencies.append(baseline_latency)

        per_query.append({
            "id": case.get("id"),
            "query": query,
            "language": language,
            "intent": case.get("intent"),
            "rag": {
                "answer": rag_answer,
                "quality_score": rag_quality["quality_score"],
                "topic_coverage": rag_quality["topic_coverage"],
                "is_uncertain": rag_quality["is_uncertain"],
                "latency_ms": rag_latency,
            },
            "baseline": {
                "answer": baseline_answer,
                "quality_score": baseline_quality["quality_score"],
                "topic_coverage": baseline_quality["topic_coverage"],
                "is_uncertain": baseline_quality["is_uncertain"],
                "latency_ms": baseline_latency,
            },
            "delta_quality": rag_quality["quality_score"] - baseline_quality["quality_score"],
        })

        print(f"  RAG      quality={rag_quality['quality_score']:.2f} latency={rag_latency}ms")
        print(f"  Baseline quality={baseline_quality['quality_score']:.2f} latency={baseline_latency}ms")

    n = len(test_set)
    rag_wins = sum(1 for r in per_query if r["delta_quality"] > 0.05)
    baseline_wins = sum(1 for r in per_query if r["delta_quality"] < -0.05)
    ties = n - rag_wins - baseline_wins

    aggregated = {
        "n_queries": n,
        "rag_avg_quality": sum(rag_quality_scores) / n,
        "baseline_avg_quality": sum(baseline_quality_scores) / n,
        "rag_avg_latency_ms": sum(rag_latencies) / n,
        "baseline_avg_latency_ms": sum(baseline_latencies) / n,
        "rag_wins": rag_wins,
        "baseline_wins": baseline_wins,
        "ties": ties,
        "rag_win_rate": rag_wins / n,
    }

    print("\n" + "=" * 60)
    print("BASELINE COMPARISON SUMMARY")
    print("=" * 60)
    print(f"RAG avg quality:      {aggregated['rag_avg_quality']:.3f}")
    print(f"Baseline avg quality: {aggregated['baseline_avg_quality']:.3f}")
    print(f"Delta:                {aggregated['rag_avg_quality'] - aggregated['baseline_avg_quality']:+.3f}")
    print(f"RAG wins / Baseline wins / Ties: {rag_wins} / {baseline_wins} / {ties}")
    print(f"RAG avg latency:      {aggregated['rag_avg_latency_ms']:.0f} ms")
    print(f"Baseline avg latency: {aggregated['baseline_avg_latency_ms']:.0f} ms")
    print("=" * 60)

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out_path = RESULTS_DIR / f"{stamp}_baseline_comparison.json"
    payload = {
        "timestamp": stamp,
        "model": MODEL_NAME,
        "test_set_size": n,
        "aggregated": aggregated,
        "per_query": per_query,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=float)
    print(f"\nWrote: {out_path.relative_to(REPO_ROOT)}")
    return out_path


if __name__ == "__main__":
    main()
