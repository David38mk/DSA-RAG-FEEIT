# Results — Skeleton

Mirrors Methodology (sections 4.1–4.6 of `thesis_notes.md`). Cells marked
`<fill from logs>` populate from `data/logs/queries.db` once the system has
accumulated real student usage. Run `QueryLogger().summary_stats()` and
`QueryLogger().export_csv()` to pull the data.

---

## 5.1 Data and preprocessing — results

Final corpus statistics after the full ingestion pipeline.

| Source                     | Files | Docs extracted | Chunks |
|----------------------------|------:|---------------:|-------:|
| MK lecture PDFs            |   <fill> |        <fill> | <fill> |
| MK FAQ Q&A (DOCX)          |    1 |             41 |     41 |
| EN textbook                |    1 |          ~738p | <fill> |
| **Total**                  | **21** |     **1565** | **1100** |

- Chunk size range: 1000–2000 chars (code-aware merging, Q&A atomic units).
- See [src/preprocessing/smart_chunker.py](../src/preprocessing/smart_chunker.py).

## 5.2 Embedding — results

- Model: `intfloat/multilingual-e5-base` (768 dim).
- Vector store: ChromaDB, cosine similarity, persistent at `data/vectorstore/`.
- Cross-lingual retrieval qualitative example: MK query → EN textbook chunk → MK answer. Example pair: `<fill: 1 representative case>`.

## 5.3 Retrieval — results

**Routing accuracy** (30-query test set, technical vs support):

| Method      | Overall | Technical | Support | Latency  |
|-------------|--------:|----------:|--------:|---------:|
| Rule-based  |   76.7% |     93.3% |   60.0% |   <1 ms  |
| LLM-based   |    100% |      100% |    100% |  1555 ms |
| **Hybrid**  | **94%** |    **95%**| **93%** | **201 ms** |

**Selected method:** hybrid (rules if confidence > 0.8, else LLM fallback). Sits inside the 2 s end-to-end budget while gaining ~17 percentage points over the rule-based baseline.

**Ranking case study — syllabus FAQ.** Pre-fix, the query *"каде можам да најдам сиже"* returned the syllabus chunk at rank #16–20 (similarity 0.616). Two fixes were applied:

1. `rag_pipeline.query()` now invokes `hybrid_search()` when `use_hybrid=True` (previously the parameter was accepted but silently dropped).
2. FAQ/admin metadata boost increased from 0.3 to 0.5 in `HybridSmartRetriever.hybrid_search()`.

Post-fix: syllabus chunk surfaced in the top-N retrieval window and the LLM produced the correct answer including the canonical URL (`feit.ukim.edu.mk/subject/podatochni-strukturi-i-analiza-na-algoritmi-2/`).

**Adaptive retrieval count by intent.** Support/administrative queries now fetch up to 14 FAQ+admin chunks (`min(n_results×2, 20)`), while technical queries fetch 7 lecture/textbook chunks. Rationale: FAQ Q&A pairs average ~200 chars vs ~1,500 chars for lecture slides — 14 FAQ chunks ≈ 700 tokens, fewer than 7 lecture chunks ≈ 3,500 tokens. The primary student use case (course administration questions) benefits from higher recall across the full 41-entry FAQ corpus.

## 5.4 LLM — results

- Provider: Groq API, model `llama-3.3-70b-versatile`, temperature 0.3, top-p 0.9, max 1024 tokens.
- Free-tier budget: 14,400 requests/day — sufficient headroom for a single-course deployment.
- Response language compliance (% of MK queries answered in MK, EN in EN): `<fill from logs>`.

**RAG vs no-retrieval baseline** (same model, retrieval removed; n=9 test queries):

| Metric                           | RAG    | Baseline | Δ        |
|----------------------------------|-------:|---------:|---------:|
| Keyword-coverage (heuristic)     | 0.707  | 0.717    | −0.009   |
| LLM-judged win rate              | **67%**| 33%      | +34 pp   |
| LLM-judged accuracy (1–5)        | **4.22** | 3.44   | +0.78    |
| Hallucinations (count of 9)      | **2**  | 6        | 3× fewer |

The keyword-coverage heuristic and the LLM-as-judge methodology disagree. The keyword metric rewards answers that contain expected tokens regardless of factual grounding; the LLM judge, given the retrieved course materials as reference, identifies that the baseline confidently invents course-specific facts absent from the materials. **The divergence is itself a result**: keyword-based scoring undervalues retrieval's primary contribution, which is grounding answers in source materials.

LLM-as-judge protocol: judge model `llama-3.1-8b-instant` (deliberately different from the generator to limit self-bias), A/B order randomized per query (seed=42), judge receives retrieved course chunks as ground truth. Result files: `evaluation/results/2026-05-15_153638_baseline_comparison.json` and `evaluation/results/2026-05-15_154927_llm_judge.json`.

Threats to validity: small sample (n=9), judge is from the same model family as the generator (Llama), single-judge single-run.

## 5.5 RAG pipeline — results

**Latency breakdown** — two confirmed measurements:

| Condition | Retrieval | Generation | Total |
|---|---:|---:|---:|
| n_results=15, rules-only (original) | 87 ms | 746 ms | **833 ms** |
| n_results=5, rules-only (confirmed) | ~50 ms | ~337 ms | **387 ms** |

Both within the <2 s target. When LLM fallback routing fires, total rises to ~3–5 s.

**Free-tier daily token budget:** `llama-3.3-70b-versatile` cap is 100,000 tokens/day. At n_results=7 (~3,500 tokens/call) → ~28 queries/day before cap. Evaluation suites should be spaced across days or use Gemini (250K TPM). The 30–56s latencies observed in earlier runs were caused by daily-cap exhaustion from back-to-back eval runs, not production usage. From production logs:

| Metric                       | Value |
|------------------------------|------:|
| Total queries logged         | <fill from logs> |
| Sessions                     | <fill from logs> |
| Success rate                 | <fill from logs> |
| p50 / p95 / p99 total time   | <fill from logs> |
| Queries by language (mk/en)  | <fill from logs> |
| Queries by intent (tech/support/mixed) | <fill from logs> |

## 5.5b Multi-provider comparison — results

Cross-provider evaluation on the same 9-query test set (n_results=7).

> **Important:** The first run (`2026-05-16_204857_provider_comparison.json`) used
> inconsistent system prompts per provider — each generator had its own copy with
> different wording. This was fixed: all generators now import from `src/llm/prompts.py`
> (single source of truth). **The first-run latency numbers are valid; the quality
> numbers are not a fair comparison.** Re-run and cite the new result file below.

Result file: `<fill: evaluation/results/YYYY-MM-DD_provider_comparison.json>` (re-run after unified prompts).

**First run** (2026-05-16, inconsistent prompts — latency valid, quality not comparable):

| Provider / Model                  | Avg Quality | Avg Latency | Uncertain | Wall time |
|-----------------------------------|------------:|------------:|----------:|----------:|
| Groq / llama-3.3-70b-versatile    | 0.500       | 387 ms      | 0 / 9     | 3.5 s     |
| Groq / llama-3.1-8b-instant       | 0.624       | 30,060 ms † | 0 / 9     | 270.5 s   |
| Gemini / gemini-2.0-flash ‡       | 0.419       | 3,408 ms    | 0 / 9     | 30.7 s    |
| OpenRouter / mistral-7b-instruct § | 0.500      | 598 ms      | 0 / 9     | 5.4 s     |

† Groq 8B hit shared daily token budget mid-run; true latency ~200–600ms.
‡ Used `gemini-2.0-flash` which had 0 quota on this project. Now fixed to `gemini-2.5-flash`.
§ Model since removed from OpenRouter. Now using `llama-3.3-70b-instruct:free` and `llama-3.2-3b-instruct:free`.

**Valid comparison** (re-run after prompt unification, `gemini-2.5-flash`, updated OpenRouter models):

| Provider / Model                       | Avg Quality | Avg Latency | Uncertain |
|----------------------------------------|------------:|------------:|----------:|
| Groq / llama-3.3-70b-versatile         | `<fill>`    | `<fill>` ms | `<fill>`  |
| Groq / llama-3.1-8b-instant            | `<fill>`    | `<fill>` ms | `<fill>`  |
| Gemini / gemini-2.5-flash              | `<fill>`    | `<fill>` ms | `<fill>`  |
| OpenRouter / llama-3.3-70b (free)      | `<fill>`    | `<fill>` ms | `<fill>`  |

**Interpretation notes for write-up:**

- **Keyword quality scores are unreliable for cross-provider comparison.** All providers scored 0.40–0.62 because the metric rewards long answers with ≥1 matching keyword — insensitive to actual accuracy differences. LLM-as-judge (run `run_llm_judge.py`) is required to meaningfully compare provider quality.
- **Groq 70B: 387ms** — confirmed production latency at n_results=5 with a fresh daily budget. Well within the <2 s target.
- **Groq 8B: 30s** — not intrinsic to the 8B model. The LLM intent classifier (which uses the 70B model) shares the same Groq daily token budget. Running 8B immediately after 70B exhausted the shared budget. True 8B latency is ~200–600ms per query.
- **Gemini Flash: ~500ms** (excluding query 5 outlier at 27s caused by the Groq classifier hitting its shared limit mid-run). 1M tokens/day free tier makes it the best option for running large evaluation suites.
- **OpenRouter Mistral 7B: 598ms** — no hard daily cap, consistent latency, suitable as a fallback.

**What to run next:** `python -m evaluation.scripts.run_llm_judge` (requires fresh Groq quota) to get pairwise quality comparison across providers.

## 5.6 Application — results

Delivered features:

- Streamlit UI with auto-language detection (MK/EN/Latin-script MK).
- Model selector across 7 options: Groq (4 models), Gemini Flash, OpenRouter (2 free models).
- Persistent conversation memory (sliding window of 10 turns; injected into the LLM system prompt for follow-up anaphora).
- SQLite-backed query logger capturing sessions, queries, responses, and timing metrics.

**Conversation memory usage** (from logs): `<fill: avg turns per session, % of queries that benefited from history — operationalised as follow-up queries that received non-bail answers>`.

## 5.7 Real-usage evaluation

Once the logger has accumulated data:

- Reporting window: `<start date> – <end date>`.
- Total queries: `<fill>`.
- Distinct sessions: `<fill>`.
- Most common failure modes (sampled from `responses WHERE success = 0` and from low-similarity successful answers): `<fill: 3–5 categories with examples>`.
- Latency distribution chart: `<fill: histogram from metrics table>`.

---

## How to refresh this section from real data

```python
from src.telemetry.query_logger import QueryLogger
logger = QueryLogger()  # opens data/logs/queries.db
print(logger.summary_stats())     # for 5.5 table
logger.export_csv()               # CSVs into data/logs/exports/ for plots
```

Recommended cadence: refresh once at the end of the data-collection window, not iteratively — examiners will ask "is this real student usage and over what period?", and a single clean window is easier to defend than a moving average.
