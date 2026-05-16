"""
LLM-as-judge: compare RAG vs baseline answers head-to-head.

Loads the most recent baseline_comparison.json from evaluation/results/,
re-retrieves course context for each query, and asks a Groq model to pick
a winner with structured JSON output. Mitigations:

- Position bias: A/B order randomized per query (seed=42 for reproducibility).
- Self-bias: judge model is intentionally a different model from the one
  that generated the answers.
- Ground truth: judge sees retrieved course materials, not just the question.

Usage (from repo root):
    python -m evaluation.scripts.run_llm_judge
"""

import json
import random
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "evaluation" / "results"

sys.path.insert(0, str(REPO_ROOT))

from src.vectorstore.vector_store_manager import VectorStoreManager
from src.retrieval.hybrid_smart_retriever import HybridSmartRetriever


JUDGE_MODEL = "llama-3.1-8b-instant"
SEED = 42


def find_latest_baseline_result(results_dir: Path) -> Path:
    candidates = sorted(results_dir.glob("*_baseline_comparison.json"))
    if not candidates:
        raise RuntimeError(f"No baseline_comparison results in {results_dir}")
    return candidates[-1]


def fetch_context(retriever, query: str, n_results: int = 5) -> str:
    """Re-retrieve chunks so the judge has ground-truth course materials."""
    results = retriever.route_query(query, n_results=n_results)
    chunks = results.get("results", [])
    parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("metadata", {}).get("source", "Unknown")
        body = chunk.get("text", "")
        parts.append(f"[Source {i}: {source}]\n{body}")
    return "\n\n".join(parts)


def build_judge_prompt(query: str, context: str, answer_a: str, answer_b: str, language: str) -> str:
    return f"""You are evaluating two answers given by AI assistants for a Data Structures
and Algorithms course at FEEIT (North Macedonia). Use the course materials
below as the ground truth. Be especially strict on administrative questions
where invented facts (dates, point thresholds, policies) are unacceptable
even if they sound plausible.

QUERY (language={language}):
{query}

COURSE MATERIALS (ground truth):
{context}

ANSWER A:
{answer_a}

ANSWER B:
{answer_b}

Return a JSON object with these keys:
- winner: "A", "B", or "tie"
- reasoning: 1-2 sentence explanation
- accuracy_a: integer 1-5 (1=wrong, 5=fully matches course materials)
- accuracy_b: integer 1-5
- uses_sources_a: boolean (cites or refers to course materials)
- uses_sources_b: boolean
- hallucinates_a: boolean (invents facts not in materials)
- hallucinates_b: boolean

Output JSON only, no surrounding text."""


def judge(client, model, query, context, answer_a, answer_b, language) -> dict:
    prompt = build_judge_prompt(query, context, answer_a, answer_b, language)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a careful, impartial evaluator. Respond with JSON only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
        max_tokens=400,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content
    return json.loads(raw)


def main() -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    from evaluation.scripts._keys import load_groq_api_key
    from groq import Groq

    load_groq_api_key()
    groq_client = Groq()

    baseline_path = find_latest_baseline_result(RESULTS_DIR)
    print(f"Loading: {baseline_path.relative_to(REPO_ROOT)}")
    with open(baseline_path, "r", encoding="utf-8") as f:
        baseline_data = json.load(f)

    vsm = VectorStoreManager(collection_name="dsa_rag_test")
    vsm.create_collection(reset=False)
    retriever = HybridSmartRetriever(vsm)

    judgments = []
    rag_wins = 0
    baseline_wins = 0
    ties = 0
    rag_hallu = 0
    baseline_hallu = 0
    rag_accuracy = []
    baseline_accuracy = []
    rng = random.Random(SEED)

    for i, q in enumerate(baseline_data["per_query"], 1):
        query = q["query"]
        language = q.get("language", "mk")
        rag_answer = q["rag"]["answer"]
        baseline_answer = q["baseline"]["answer"]

        print(f"\n[{i}/{len(baseline_data['per_query'])}] {query}")
        context = fetch_context(retriever, query)

        if rng.random() < 0.5:
            a_label, b_label = "rag", "baseline"
            answer_a, answer_b = rag_answer, baseline_answer
        else:
            a_label, b_label = "baseline", "rag"
            answer_a, answer_b = baseline_answer, rag_answer

        try:
            verdict = judge(groq_client, JUDGE_MODEL, query, context, answer_a, answer_b, language)
        except Exception as e:
            print(f"  Judge error: {e}")
            continue

        raw_winner = verdict.get("winner", "tie")
        if raw_winner == "A":
            winner = a_label
        elif raw_winner == "B":
            winner = b_label
        else:
            winner = "tie"

        if winner == "rag":
            rag_wins += 1
        elif winner == "baseline":
            baseline_wins += 1
        else:
            ties += 1

        rag_hallu_key = "hallucinates_a" if a_label == "rag" else "hallucinates_b"
        baseline_hallu_key = "hallucinates_a" if a_label == "baseline" else "hallucinates_b"
        if verdict.get(rag_hallu_key):
            rag_hallu += 1
        if verdict.get(baseline_hallu_key):
            baseline_hallu += 1

        rag_acc_key = "accuracy_a" if a_label == "rag" else "accuracy_b"
        baseline_acc_key = "accuracy_a" if a_label == "baseline" else "accuracy_b"
        rag_accuracy.append(verdict.get(rag_acc_key, 0))
        baseline_accuracy.append(verdict.get(baseline_acc_key, 0))

        reasoning = (verdict.get("reasoning", "") or "")[:120]
        print(f"  winner: {winner} | {reasoning}")

        judgments.append({
            "id": q.get("id"),
            "query": query,
            "language": language,
            "intent": q.get("intent"),
            "a_label": a_label,
            "b_label": b_label,
            "winner": winner,
            "verdict": verdict,
        })

    n = len(judgments) or 1
    aggregated = {
        "judge_model": JUDGE_MODEL,
        "seed": SEED,
        "n_queries": len(judgments),
        "rag_wins": rag_wins,
        "baseline_wins": baseline_wins,
        "ties": ties,
        "rag_win_rate": rag_wins / n,
        "baseline_win_rate": baseline_wins / n,
        "rag_avg_accuracy": sum(rag_accuracy) / n,
        "baseline_avg_accuracy": sum(baseline_accuracy) / n,
        "rag_hallucinations": rag_hallu,
        "baseline_hallucinations": baseline_hallu,
    }

    print("\n" + "=" * 60)
    print("LLM-AS-JUDGE SUMMARY")
    print("=" * 60)
    print(f"Judge model:   {JUDGE_MODEL}")
    print(f"RAG wins:      {rag_wins} / {len(judgments)} ({rag_wins/n*100:.0f}%)")
    print(f"Baseline wins: {baseline_wins} / {len(judgments)} ({baseline_wins/n*100:.0f}%)")
    print(f"Ties:          {ties} / {len(judgments)}")
    print(f"Avg accuracy  -  RAG: {aggregated['rag_avg_accuracy']:.2f}  |  Baseline: {aggregated['baseline_avg_accuracy']:.2f}")
    print(f"Hallucinations - RAG: {rag_hallu}  |  Baseline: {baseline_hallu}")
    print("=" * 60)

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out_path = RESULTS_DIR / f"{stamp}_llm_judge.json"
    payload = {
        "timestamp": stamp,
        "source_baseline_result": baseline_path.name,
        "aggregated": aggregated,
        "judgments": judgments,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=float)
    print(f"\nWrote: {out_path.relative_to(REPO_ROOT)}")
    return out_path


if __name__ == "__main__":
    main()
