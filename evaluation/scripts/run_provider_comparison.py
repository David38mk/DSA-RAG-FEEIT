"""
Multi-provider RAG comparison.

Runs the routing test set through every configured LLM generator and produces
a side-by-side quality + latency table. Any provider whose API key is missing
is skipped with a warning — the script still runs for the remaining providers.

Configured providers (add keys to D:\\API_KEYS\\ to enable):
  groq_70b      Groq / llama-3.3-70b-versatile   (GROK_API_KEY.txt)
  groq_8b       Groq / llama-3.1-8b-instant       (GROK_API_KEY.txt)
  gemini_flash  Google / gemini-2.0-flash          (GEMINI_API_KEY.txt)
  openrouter    OpenRouter / mistral-7b-instruct   (OPENROUTER_API_KEY.txt)

Usage (from repo root):
    python -m evaluation.scripts.run_provider_comparison
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
from src.llm.gemini_generator import GeminiGenerator
from src.llm.openai_compatible_generator import OpenAICompatibleGenerator


def _build_retriever():
    vsm = VectorStoreManager(collection_name="dsa_rag_test")
    vsm.create_collection(reset=False)
    return vsm, HybridSmartRetriever(vsm)


def _build_generators(available_keys: dict) -> list[dict]:
    """
    Build generator configs for every provider whose key is present.
    Each entry: {id, label, generator}
    """
    configs = []

    if available_keys.get("GROQ_API_KEY"):
        try:
            configs.append({
                "id": "groq_70b",
                "label": "Groq / llama-3.3-70b",
                "generator": GroqGenerator(model_name="llama-3.3-70b-versatile"),
            })
            configs.append({
                "id": "groq_8b",
                "label": "Groq / llama-3.1-8b-instant",
                "generator": GroqGenerator(model_name="llama-3.1-8b-instant"),
            })
        except Exception as e:
            print(f"  Groq init failed: {e}")

    if available_keys.get("GEMINI_API_KEY"):
        try:
            configs.append({
                "id": "gemini_flash",
                "label": "Gemini / gemini-2.0-flash",
                "generator": GeminiGenerator(model_name="gemini-2.0-flash"),
            })
        except Exception as e:
            print(f"  Gemini init failed: {e}")

    if available_keys.get("OPENROUTER_API_KEY"):
        try:
            configs.append({
                "id": "openrouter_llama70b",
                "label": "OpenRouter / llama-3.3-70b (free)",
                "generator": OpenAICompatibleGenerator.for_openrouter(
                    model_name="meta-llama/llama-3.3-70b-instruct:free",
                    max_retries=3,
                ),
            })
        except Exception as e:
            print(f"  OpenRouter init failed: {e}")

    return configs


def _run_one_provider(pipeline: RAGPipeline, evaluator: EvaluationFramework,
                      test_set: list, provider_id: str, label: str) -> dict:
    results = []
    total_latency = 0

    for case in test_set:
        query = case["query"]
        language = case.get("language", "mk")
        expected_topics = case.get("expected_topics", [])

        try:
            response = pipeline.query(query, n_results=7, language=language)
            answer = response.get("answer", "")
            latency = response.get("total_time_ms", 0)
        except Exception as e:
            answer = f"ERROR: {e}"
            latency = 0

        quality = evaluator.evaluate_answer_quality(query, answer, expected_topics)
        total_latency += latency

        results.append({
            "id": case.get("id"),
            "query": query,
            "language": language,
            "intent": case.get("intent"),
            "answer": answer,
            "quality_score": quality["quality_score"],
            "topic_coverage": quality["topic_coverage"],
            "is_uncertain": quality["is_uncertain"],
            "latency_ms": latency,
        })

    n = len(results) or 1
    return {
        "provider_id": provider_id,
        "label": label,
        "n_queries": len(results),
        "avg_quality": sum(r["quality_score"] for r in results) / n,
        "avg_latency_ms": total_latency / n,
        "uncertain_count": sum(1 for r in results if r["is_uncertain"]),
        "per_query": results,
    }


def main() -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    from evaluation.scripts._keys import load_all_available_keys
    available_keys = load_all_available_keys()

    print(f"\nAvailable providers: {list(available_keys.keys())}")

    vsm, retriever = _build_retriever()
    evaluator = EvaluationFramework()
    test_set = evaluator.create_test_set()
    provider_configs = _build_generators(available_keys)

    if not provider_configs:
        print("No providers configured. Add key files and retry.")
        return

    provider_results = []

    for cfg in provider_configs:
        print(f"\n{'='*60}")
        print(f"Running: {cfg['label']}")
        print(f"{'='*60}")

        pipeline = RAGPipeline(vsm, retriever, cfg["generator"])

        start = time.perf_counter()
        result = _run_one_provider(
            pipeline, evaluator, test_set, cfg["id"], cfg["label"]
        )
        elapsed = time.perf_counter() - start

        for r in result["per_query"]:
            print(
                f"  [{r['language']}] q={r['quality_score']:.2f} "
                f"lat={r['latency_ms']}ms  {r['query'][:45]}"
            )

        print(
            f"\n  avg quality={result['avg_quality']:.3f}  "
            f"avg latency={result['avg_latency_ms']:.0f}ms  "
            f"uncertain={result['uncertain_count']}/{result['n_queries']}  "
            f"(wall {elapsed:.1f}s)"
        )
        provider_results.append(result)

    # Summary table
    print(f"\n{'='*70}")
    print("PROVIDER COMPARISON SUMMARY")
    print(f"{'='*70}")
    print(f"{'Provider':<40} {'Avg Quality':>11} {'Avg Latency':>12} {'Uncertain':>9}")
    print("-" * 70)
    for r in provider_results:
        print(
            f"{r['label']:<40} {r['avg_quality']:>11.3f} "
            f"{r['avg_latency_ms']:>10.0f}ms {r['uncertain_count']:>7}/{r['n_queries']}"
        )
    print("=" * 70)

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out_path = RESULTS_DIR / f"{stamp}_provider_comparison.json"
    payload = {
        "timestamp": stamp,
        "test_set_size": len(test_set),
        "providers": provider_results,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=float)
    print(f"\nWrote: {out_path.relative_to(REPO_ROOT)}")
    return out_path


if __name__ == "__main__":
    main()
