# Evaluation

Datasets, scripts, results, and reports that measure each part of the
DSA-RAG-FEEIT system. Metric implementations live in
[../src/evaluation/evaluation_framework.py](../src/evaluation/evaluation_framework.py);
this folder holds everything around them.

## Layout

```
evaluation/
  datasets/           gold-standard test cases (JSON, source of truth)
  scripts/            entry-point scripts that consume datasets, write to results/
  results/            timestamped JSON outputs of each run (one file per run)
  reports/            human-readable markdown summaries citing specific result files
```

## What we measure, and how

| System part      | Metric                                | Script                                | Source of truth                |
|------------------|---------------------------------------|---------------------------------------|--------------------------------|
| Routing          | Intent accuracy (overall + per-class) | `scripts/run_routing_eval.py`         | `datasets/routing_test_set.json` |
| Retrieval        | Keyword coverage @ top-k, avg sim     | `scripts/run_routing_eval.py`         | `datasets/routing_test_set.json` |
| Answer quality   | Topic coverage, uncertainty rate      | `scripts/run_routing_eval.py`         | `datasets/routing_test_set.json` |
| RAG vs baseline  | Quality delta, win rate, latency cost | `scripts/run_baseline_comparison.py`  | `datasets/routing_test_set.json` |
| Answer quality (LLM-judged) | Pairwise wins, accuracy 1-5, hallucination flag | `scripts/run_llm_judge.py` | latest `*_baseline_comparison.json` |
| Multi-provider comparison | Quality + latency across Groq / Gemini / OpenRouter | `scripts/run_provider_comparison.py` | `datasets/routing_test_set.json` |
| Live usage       | p50/p95 latency, success, by-intent   | `QueryLogger.summary_stats()`         | `data/logs/queries.db`         |
| Routing latency  | Rule vs LLM vs Hybrid (existing)      | See `reports/17_thesis_methodology_phases_2_5.md` | Recorded once on 30-q set      |

## How to reproduce

```powershell
# Routing + retrieval + answer-quality on the test set:
python -m evaluation.scripts.run_routing_eval

# RAG vs no-retrieval baseline (the headline thesis number):
python -m evaluation.scripts.run_baseline_comparison

# LLM-as-judge on the latest baseline comparison (pairwise, position-randomized):
python -m evaluation.scripts.run_llm_judge

# Multi-provider comparison (Groq + Gemini + OpenRouter, n_results=5):
python -m evaluation.scripts.run_provider_comparison
```

Each run writes `evaluation/results/YYYY-MM-DD_HHMMSS_<name>.json`. Commit
the result files you cite in the thesis so they survive future code changes.

## Honest notes on the current metrics

- **Keyword-based scoring is a proxy, not ground truth.** Answer quality
  is computed from `expected_topics` keyword presence. This penalises
  correct paraphrases and rewards verbose answers that happen to include
  the right tokens. For thesis-grade quality numbers, layer an
  LLM-as-judge pass on top of the same test set — `evaluation_framework`
  is the natural place to add that method.

- **Test set size is 9 cases**, not the "30" mentioned in earlier docs.
  Verify against `datasets/routing_test_set.json`. Expanding it (more
  cross-lingual cases, more administrative edge cases) is the highest-ROI
  improvement available before defense.

- **The baseline comparison uses the same Groq model with no retrieval
  context.** This isolates the value of retrieval, not the value of the
  full system over a generic chatbot.

## Adding a new metric

1. Add the dataset under `datasets/` (JSON).
2. Implement metric logic in `src/evaluation/evaluation_framework.py`.
3. Add an entry-point script under `scripts/` that loads the dataset,
   runs the system, calls the metric, writes `results/<stamp>_<name>.json`.
4. Add a row to the table above and link the resulting markdown report
   under `reports/`.
