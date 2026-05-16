# Project Workflow — How DSA-RAG-FEEIT Was Built

This document is a chronological development log: what was built in each phase, how it was tested, and what failed before working. Useful for thesis Methodology drafting and for understanding why the repo has multiple versions of similar files.

The phase numbers match the historical reports under `reports/` (see `reports/INDEX.md` for the chronological reading list). Phases 1–6 are the original build sequence. Phase 7 was added later. The post-phase section covers bug fixes and evaluation infrastructure added during the final stretch.

---

## Phase 1 — Data ingestion

**Goal:** turn the raw course corpus (21 source files: 827 MK lecture PDFs aggregated, 41 MK FAQ Q&A in DOCX, one 738-page EN textbook) into structured documents the system can chunk and index.

**Built:**
- `src/ingestion/multi_format_extractor.py` — PDF (PyPDF2) and DOCX (python-docx) extraction.
- `src/ingestion/faq_parser.py` — special handling so each Q&A becomes one atomic unit (a chunker-respected boundary).
- `src/ingestion/document_classifier.py` — tags each document: `lecture_slides`, `supplementary_slides`, `textbook`, `faq`, `admin`.
- `src/ingestion/data_validator.py` — flagged empty extractions, mis-classified files, encoding issues.
- `src/ingestion/load_all_documents.py` — orchestrator.

**Tested with:**
- `src/testing_archive/test_phase1_complete.py` — end-to-end ingestion run, counts asserted.
- `src/testing_archive/diagnose_phase1.py` — for known mis-extractions during debugging.

**Outcome:** 1,565 raw documents extracted from 21 source files.

---

## Phase 2 — Chunking

**Goal:** turn extracted documents into retrieval-sized chunks (1000–2000 chars) without losing code-block boundaries or FAQ Q&A atomicity.

**Built:**
- `src/preprocessing/smart_chunker.py` — code-aware merging: detects code fences and refuses to split them across chunks. Q&A pairs treated as atomic units.

**Tested with:**
- `src/testing_archive/test_phase2.py`, `src/testing_archive/testing_chunker.py`, `src/testing_archive/code_extraction_test.py`.
- `src/testing_archive/faq_quality_test.py` — verified each Q&A landed in one chunk.

**Outcome:** 1,100 chunks from 1,565 documents (intentional merging reduced count; quality > quantity).

A known bug surfaced here: long FAQ answers (the syllabus chunk at 1,575 chars) suffered from embedding dilution. Documented in `reports/05_phase2_faq_chunking_fix.md`. The fix landed much later, in the post-phase bug-fix pass.

---

## Phase 3 — Vector store and embeddings

**Goal:** persistent index that supports cosine similarity retrieval with metadata filtering, multilingual (MK + EN).

**Built:**
- `src/embeddings/embedder.py` — wrapper around `intfloat/multilingual-e5-base` (768-dim, multilingual).
- `src/embeddings/build_index.py` — one-shot embedding + write to ChromaDB.
- `src/vectorstore/vector_store_manager.py` — collection lifecycle, search API with `filter_metadata` parameter.
- `src/vectorstore/rebuild_vectorstore.py` — drop and rebuild utility for re-runs.

**Tested with:**
- `src/testing_archive/test_phase3.py` — round-trip retrieval sanity.
- `src/testing_archive/retrieval_testing.py` — qualitative inspection of top-k results.

**Outcome:** persistent ChromaDB at `data/vectorstore/`, populated with 1,100 chunks. Cross-lingual retrieval verified informally (MK queries returning EN textbook chunks where appropriate).

---

## Phase 4 — Smart retrieval (rule-based routing)

**Goal:** route queries to the right corpus — technical questions through lecture/textbook chunks, administrative through FAQ chunks.

**Built:**
- `src/retrieval/smart_retriever.py` — first cut. Rule-based intent (MK + EN keyword patterns), per-intent metadata filters.
- `src/retrieval/smart_retriever_fixed.py` — addresses filter-format bugs surfaced during testing.
- `src/retrieval/smart_retriever_v2.py` — cleaner second iteration, kept as a reference implementation.

**Tested with:**
- `src/testing_archive/test_phase4.py`.
- The 30-query routing test set (later 9 in the JSON) — manual.

**Outcome:** rule-based routing achieved 76.7% overall (93.3% technical, 60.0% support). Support accuracy was the obvious weak point.

---

## Phase 5 — Enhanced language detection

**Goal:** correctly route queries typed in Latin-script Macedonian (e.g., `Dali ke imame lab?`) that earlier components misclassified as English.

**Built:**
- `src/retrieval/enhanced_language_detector.py` — Cyrillic ratio + 25 MK word patterns covering common Latin transliterations. Returns `mk`, `en`, or `mixed`.

**Tested with:**
- Internal Latin-MK test set. Hit 100% accuracy.
- Documented in `reports/12_phase5_latin_mk_changelog.md` and `reports/13_phase5_latin_quick_deploy.md`.

**Outcome:** queries like `Dali ke imame lab?` correctly classified as MK and routed to support corpus.

---

## Phase 6 — Hybrid routing (rules + LLM)

**Goal:** close the 23-point gap on support queries by adding LLM-based intent classification, while keeping latency under the 2 s budget.

**Built:**
- `src/retrieval/llm_intent_classifier.py` — Groq LLM call returning structured intent + confidence + reasoning.
- `src/retrieval/hybrid_smart_retriever.py` — two-path retriever: rule-based when confidence ≥ 0.8, LLM fallback otherwise. Also implements `hybrid_search()` for metadata-boosted re-ranking.

**Tested with:**
- `src/testing_archive/evaluate_routing_methods.py` — compares rule-based, LLM-only, and hybrid on the 30-query set.

**Outcome (30-query test set):**

| Method      | Overall | Technical | Support | Latency  |
|-------------|--------:|----------:|--------:|---------:|
| Rule-based  |   76.7% |     93.3% |   60.0% |  < 1 ms  |
| LLM-based   |    100% |      100% |    100% |  1555 ms |
| **Hybrid**  |     94% |       95% |     93% |   201 ms |

Hybrid chosen — sits within the latency budget while gaining 17 percentage points over rules.

---

## Phase 7 — Observability and conversation memory

Built later, after the production pipeline was already running. Goal: collect thesis-grade usage data and improve follow-up handling.

**Built:**
- `src/telemetry/query_logger.py` — SQLite logger with four tables: `sessions`, `queries`, `responses`, `metrics`. Exposes `log_query()`, `log_response()`, `log_metrics()`, `summary_stats()`, `export_csv()`.
- `src/llm/conversation_memory.py` — sliding window (10 turns) of (query, answer) pairs. Last 3 turns are formatted and inserted into the LLM system prompt to resolve anaphora ("how do they work?", "и таа?").
- Integration into `src/llm/rag_pipeline.py` — both optional, backward-compatible.
- Integration into `ui/streamlit_app_v2.py` — logger instantiated once per Streamlit run, memory held in `st.session_state`, cleared by the existing "Clear chat" button.

**Tested with:**
- Standalone smoke run of `query_logger.py` (`python -m src.telemetry.query_logger`).
- Signature inspection of the updated pipeline.
- Streamlit dialog round-trip with a deliberately ambiguous follow-up.

---

## Application layer (cross-cutting)

Built incrementally alongside the phases.

**Built:**
- `ui/streamlit_app.py` — first Streamlit version (Phase A).
- `ui/streamlit_app_v2.py` — second iteration (Phase B): auto language detection, model selector, cached pipeline initialization. **Current production UI.**
- `ui/gradio_app.py` — exploratory; not maintained.
- `launch_app.py` — entry point. Loads `GROQ_API_KEY` from `D:\API_KEYS\GROK_API_KEY.txt` and runs Streamlit.

---

## Post-phase bug fixes and evaluation work

The phases above describe the original build. After the production system was running, several issues were discovered and the evaluation harness was substantially extended.

**Bug: dead `use_hybrid` parameter.**
`RAGPipeline.query()` accepted `use_hybrid` but silently ignored it — always called `route_query()`, never `hybrid_search()`. The FAQ boost in `hybrid_search()` was therefore dead code. Fixed in `src/llm/rag_pipeline.py` by dispatching to `hybrid_search()` when `use_hybrid=True`.

**Bug: FAQ boost too small.**
Even when active, the FAQ/admin metadata boost of 0.3 was insufficient to surface the syllabus chunk (rank #16–20, similarity 0.616). Raised to 0.5 in `src/retrieval/hybrid_smart_retriever.py`. Combined with wiring fix, the syllabus query now returns the correct answer with the canonical URL.

**Bug: dead `n_results` slider in Streamlit.**
The sidebar slider was read but `pipeline.query()` was called with `n_results=30` hardcoded. Slider removed.

**Evaluation harness extension.**
Test set lifted from `src/evaluation/evaluation_framework.create_test_set()` into `evaluation/datasets/routing_test_set.json` (single source of truth). New `evaluation/` folder with:
- `evaluation/scripts/run_routing_eval.py` — wraps existing framework, writes timestamped JSON results.
- `evaluation/scripts/run_baseline_comparison.py` — RAG vs no-retrieval-context baseline using the same Groq model.
- `evaluation/scripts/run_llm_judge.py` — pairwise LLM-as-judge with position randomization, accuracy ratings, hallucination flags. Judge model is a different Llama variant from the generator to limit self-bias.
- `evaluation/scripts/_keys.py` — shared key loader mirroring `launch_app.py`.

**Headline evaluation results (n=9):**
- Keyword-coverage heuristic: RAG 0.707 vs Baseline 0.717 — effectively tied.
- LLM-as-judge: **RAG wins 67%** (6 of 9), avg accuracy 4.22/5 vs 3.44/5, hallucinations 2 vs 6 (3× reduction).
- The two-metric divergence is itself a thesis finding — keyword scoring undervalues retrieval's primary contribution (factual grounding).

Result files: `evaluation/results/2026-05-15_153638_baseline_comparison.json`, `evaluation/results/2026-05-15_154927_llm_judge.json`.

---

## Repo cleanup and documentation (post-evaluation)

**reports/ reorganisation.**
All 20 files in `reports/` renamed with chronological numeric prefix (`01_phase1_ingestion.md` … `20_test_questions_admin.md`) so they sort in reading order. `INDEX.md` added as a table of contents.

**src/ cleanup.**
- Removed empty placeholders `src/api/` and `src/prompts/` (both had only 1-line empty files).
- `src/testing/` renamed to `src/testing_archive/` to signal historical status.
- `evaluation_results.json` (root) moved to `evaluation/results/2026-03-21_225546_routing_eval.json` to sit alongside newer timestamped results.

**.gitignore rewrite.**
Added missing patterns: `.claude/`, `*.egg-info/`, `dist/`, `build/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, broader secret patterns (`*.key`, `*.pem`). Sectioned with comments.

**Three new top-level docs.**
- `README.md` — full project overview, file-by-file structure, production call graph.
- `WORKFLOW.md` — this file, phase-by-phase development log.
- `THESIS_OUTLINE.md` — skeleton with key points for every thesis section, including suggested additions.

---

## Latency investigation

**Observation:** evaluation runs showed ~37s/query average for RAG vs ~833ms documented. Investigation via `QueryLogger` and per-query pattern analysis revealed:

- Logger confirmed: `rules_only` path = 87ms retrieval, 746ms generation (833ms total — valid).
- Logger confirmed: `llm_fallback` path = 40,096ms retrieval, 88ms generation — the LLM intent classifier was blocking.
- Root cause: **Groq free-tier daily token cap (100,000 tokens/day)** was exhausted mid-run across multiple back-to-back evaluation runs. Once the cap is hit, every subsequent call queues.

**Tested hypothesis:** swapping classifier from `llama-3.3-70b-versatile` to `llama-3.1-8b-instant` — no improvement. Cause was the daily cap, not per-call classifier cost. Reverted to 70B classifier.

**Fix applied:** `run_baseline_comparison.py` now uses `n_results=5` instead of 15, cutting per-call token cost by ~57% (7K → 3K tokens). Stays within daily budget for multiple eval runs per day.

**Conclusion for thesis:** 833ms is valid for single-user production use. Evaluation suites should use `n_results=5` and be spaced across days to avoid daily cap exhaustion. Updated in `reports/18_thesis_results_skeleton.md` §5.5.

---

## Multi-vendor LLM support

**Motivation:** Groq's 100K tokens/day limit constrains evaluation throughput. Adding multiple providers also strengthens the thesis (vendor-agnostic architecture, cross-provider comparison).

**Built:**
- `src/llm/base_generator.py` — abstract `BaseGenerator` class. `RAGPipeline` now accepts any compliant generator.
- `src/llm/gemini_generator.py` — Google Gemini 2.0 Flash. Free tier: 1M tokens/day, 15 RPM. Key: `D:\API_KEYS\GEMINI_API_KEY.txt`.
- `src/llm/openai_compatible_generator.py` — OpenAI-format wrapper. Works for **OpenRouter** (free models: Mistral 7B, Llama 3.1 8B, Qwen 2.5) and **Ollama** (local). Key: `D:\API_KEYS\OPENROUTER_API_KEY.txt`.
- `GroqGenerator` updated to inherit from `BaseGenerator`.
- `evaluation/scripts/_keys.py` — extended to optionally load Gemini and OpenRouter keys; gracefully skips missing keys.
- `evaluation/scripts/run_provider_comparison.py` — runs the test set through all configured providers, prints a comparison table, writes `evaluation/results/<stamp>_provider_comparison.json`.
- Streamlit dropdown updated — 7 options across 3 providers (Groq ×4, Gemini ×1, OpenRouter ×2).
- `requirements.txt` updated: added `google-generativeai`, `openai`.

**First run results** (`evaluation/results/2026-05-16_204857_provider_comparison.json`):

| Provider | Avg Quality | Avg Latency | Note |
|---|---:|---:|---|
| Groq 70B | 0.500 | **387 ms** | Clean run, fresh daily budget |
| Groq 8B | 0.624 | 30,060 ms | Shared Groq budget exhausted mid-run |
| Gemini Flash | 0.419 | 3,408 ms | One outlier (27s, shared Groq classifier hit); true ~500ms |
| OpenRouter Mistral 7B | 0.500 | **598 ms** | Consistent, no daily cap |

Key finding: quality scores are uniform (0.40–0.62) because the keyword metric is too blunt to differentiate providers on short answers. LLM-as-judge required for meaningful quality comparison. Latency finding is solid: Groq 70B 387ms and OpenRouter 598ms are both well inside the <2s target.

Gemini SDK updated from deprecated `google.generativeai` → `google.genai` (v2.3.0). `requirements.txt` updated accordingly.

**To run:**
```powershell
python -m evaluation.scripts.run_provider_comparison
```

---

## Bug fixes and cleanup — post provider comparison

**Bug: meta-tensor error on Streamlit load.**
`SentenceTransformer(model_name)` crashed with "Cannot copy out of meta tensor" due to a PyTorch version mismatch with lazy device initialization. Fixed: `SentenceTransformer(model_name, device="cpu")` in `src/vectorstore/vector_store_manager.py:65`. Explicit `device="cpu"` bypasses lazy loading. No performance impact — model runs CPU-only on this machine regardless.

**Bug: Groq 413 "request too large" on llama-3.1-8b-instant.**
`n_results=30` in the Streamlit pipeline call produced ~14,700-token requests, exceeding the 8B model's 6,000 TPM free-tier cap. Fixed: `n_results=5` in `ui/streamlit_app_v2.py`. This is also the correct value for all providers — confirmed adequate answer quality and safe within all free-tier TPM limits.

**Decommissioned model removed.**
Groq deprecated `gemma2-9b-it`. Removed from the Streamlit dropdown and model map. Replaced by adding an additional OpenRouter option.

**Gemini model corrected.**
New API key's project has `gemini-2.5-flash` available (not `gemini-2.0-flash`). All references updated: `gemini_generator.py`, `streamlit_app_v2.py`, `run_provider_comparison.py`. Free tier confirmed from AI Studio dashboard: 5 RPM / 250K TPM / 20 RPD.

**OpenRouter model availability.**
`mistralai/mistral-7b-instruct:free` returned 404 (endpoint removed). Listed current free models with the OpenRouter API. New defaults: `meta-llama/llama-3.2-3b-instruct:free` (fast, Streamlit default) and `meta-llama/llama-3.3-70b-instruct:free` (quality, eval runs). Both served via Venice provider — subject to upstream rate-limiting. Added retry logic (`max_retries`, reads `retry_after_seconds` from 429 response) with `max_retries=1` default (fail-fast for interactive use) and `max_retries=3` for eval scripts.

**System prompts unified — critical for thesis fairness.**
Each generator previously had its own copy of the system prompt with slightly different wording, making cross-provider quality comparisons invalid (prompt was a confound). Fix: extracted all system prompts and user prompt builder into `src/llm/prompts.py`. All three generators (`GroqGenerator`, `GeminiGenerator`, `OpenAICompatibleGenerator`) now import `get_system_prompt()` and `build_user_prompt()` from the shared module. The only variable in provider comparisons is now the model itself.

Files modified: `src/llm/groq_generator.py` (rewritten clean, ~60% shorter), `src/llm/gemini_generator.py` (rewritten clean), `src/llm/openai_compatible_generator.py` (rewritten clean). Files added: `src/llm/prompts.py`.

---

## UI and pipeline quality fixes

**Language detection for Latin-script Macedonian in Streamlit.**
The `detect_language()` function in `ui/streamlit_app_v2.py` used a raw Cyrillic-ratio heuristic — it classified Latin-script MK queries like "Daj mi kod za AVL drva" as English, causing the system to respond in English with English instructions. Fixed: `detect_language()` now uses `EnhancedLanguageDetector` (the same Phase 5 module used by the retriever, with 25 MK word patterns). Falls back to Cyrillic-ratio heuristic if the module is unavailable.

**max_tokens increased 512 → 1024.**
Gemini and other providers were producing short/truncated answers on complex technical questions. Raised `max_tokens=1024` in the `generator.generate()` call inside `src/llm/rag_pipeline.py`. Applies to all providers uniformly. 1024 output tokens gives room for full explanations with code examples.

**Prompt: explicit code generation rule added.**
The models were refusing to generate AVL tree code because they found the concept in course materials but no implementation, and interpreted "answer from materials only" as "cannot answer." Added rule 6 to both MK and EN system prompts in `src/llm/prompts.py`:
- MK: *"За прашања за код и имплементации: СЕКОГАШ обезбеди Java имплементација врз основа на општото DSA познавање, дури и кога материјалите го покриваат само концептот теоретски."*
- EN: *"For code and implementation requests: always provide a Java implementation based on general DSA knowledge, even when the course materials only cover the concept theoretically."*
In both cases, the model is instructed to clearly note that code comes from general knowledge, not the course materials.

**n_results raised 5 → 7.**
After stabilising the system at n_results=5 to stop rate-limit exhaustion, bumped to 7 for richer context. `hybrid_search()` internally retrieves 14 (7×2) and re-ranks to 7, so the model sees the best 7 out of 14 candidates. Token cost per query: ~3,500 tokens — safe for all providers (Groq 8B TPM 6K/min, Gemini TPM 250K/min, OpenRouter no hard cap).

Files updated: `ui/streamlit_app_v2.py`, `src/evaluation/evaluation_framework.py`, `evaluation/scripts/run_baseline_comparison.py`, `evaluation/scripts/run_provider_comparison.py`.

**Support queries now retrieve double the chunks (up to 20).**
Administrative queries filter to FAQ + admin metadata and pass `n_results` to the vector search. With n_results=7, only 7 of the 41 FAQ entries are considered — not enough for specific grading thresholds. Fix in `src/retrieval/hybrid_smart_retriever.py:route_query()`: when intent is SUPPORT, use `min(n_results * 2, 20)` = 14 for the filtered search. Since FAQ/admin chunks are short (~150-300 chars each), 14 chunks = ~2,100 chars ≈ 700 tokens — cheaper than 7 lecture-slide chunks. This is the primary use case of the system (student administrative queries) and the most important retrieval improvement made.

**UI redesign — academic/institutional look.**
Replaced the generic AI-chatbot visual style with a clean academic design:
- Page title: "ПСАА Асистент — ФЕИТ" (was "DSA RAG Assistant"); page icon 📚 (was 🤖).
- Header: "Виртуелен Асистент за ПСАА" with ФЕИТ course subtitle; no robot emoji.
- Message labels: "Студент" / "Асистент" as small uppercase text — no emoji, no "Вие".
- Source box: clean label and subtle styling — removed warm amber.
- Metric line: inline dots · separator, no ⚡ emoji.
- Spinner: "Барам одговор..." (was "Размислувам...").
- Chat input placeholder: "Постави прашање за курсот..." (was "Напиши го твоето прашање...").
- Sidebar: clean text labels, no emoji section headers, compact stats.
- Footer: single line with · separators, muted grey.
All functional code unchanged.

**UI color scheme — slate dark.**
Initial white/light-grey palette had insufficient contrast and felt too bright. Switched to slate dark (Tailwind slate-800 palette):
- Page background: `#1e293b` (slate-800)
- Sidebar: `#162032` (deeper slate)
- User message: `#2d3f55` with `#38bdf8` (sky blue) left border
- Assistant message: `#334155` (slate-700) with `#60a5fa` (light blue) left border
- Text: `#f1f5f9` (slate-100) — high contrast on dark backgrounds
- Source box: `#253650` with `#38bdf8` label
- Code blocks: `#0f172a` (near black) — matches typical dark-mode code style
- Bold text in messages: `#93c5fd` (light blue) for emphasis without being harsh
- `.streamlit/config.toml` added: sets `base = "dark"` so native Streamlit widgets (dropdowns, buttons, metrics, sliders) also render in the dark theme — eliminates the light/dark widget mismatch.

**max_tokens raised 1024 → 2048 → 4096.**
Detailed explanations (e.g. Big O notation, AVL trees) were being cut off mid-sentence at 1024 tokens. Doubled to 2048 in `src/llm/rag_pipeline.py`; still cutting off full Java implementations + multi-step complexity proofs, so raised again to 4096 (2026-05-16).

- **Where:** `src/llm/rag_pipeline.py` — the `max_tokens=4096` argument in the `self.generator.generate(...)` call inside `RAGPipeline.query()`. This is the single place that controls output length for **all** providers (Groq, Gemini, OpenRouter), because every generator's `generate()` method accepts and forwards this parameter.
- **Why 4096:** A complete AVL rotation explanation + Java implementation routinely reaches 1,800–2,500 tokens; a Big O proof with recurrence relation + Master Theorem walkthrough hits ~1,400 tokens; a full dynamic-programming answer with code can exceed 2,000. 4096 gives room for the longest realistic answers without waste.
- **Token budget impact:** At n_results=7, each Groq 70B query now uses up to ~6,500 tokens (prompt ≈2,400 + answer ≤4,096). Groq daily cap is 100K tokens → ~15 full queries/day worst-case. In practice most answers are shorter; budget ~20–25 queries/day. Use Gemini (250K TPM) for multi-query eval runs to avoid exhausting the Groq cap.

**Fix: language persistence across conversation turns.**
When a student switched from Macedonian to English mid-conversation ("What is Big O?"), the model responded in Macedonian because the conversation history block contained Macedonian text from the previous turn, overriding the English system prompt. Fixed in `src/llm/prompts.py`: the history block now explicitly states the required response language:
- MK: *"одговорот мора да биде на МАКЕДОНСКИ ЈАЗИК"*
- EN: *"your reply MUST be in ENGLISH regardless of the language used in previous turns"*
Both the history block label and the user prompt closing line now reinforce the language requirement.

**UI bug: unclosed code fences swallowing HTML.**
When LLM answers contain an odd number of triple-backtick fences (unclosed code block), Markdown rendering captures all subsequent HTML including the source box as literal text inside the code block. This made `<div class="source-box">` appear as raw text in the chat. Fixed: `_close_unclosed_fences()` in `ui/streamlit_app_v2.py` detects and closes unclosed fences before the content is inserted into the HTML template.

---

## Testing philosophy

This project does **not** use pytest. Testing is mostly:

1. **Phase smoke tests** under `src/testing_archive/` — run manually, assert structural properties.
2. **Diagnostic scripts** — when a specific failure mode appeared, a script was written to reproduce and verify the fix.
3. **Evaluation runs** under `evaluation/scripts/` — output goes to `evaluation/results/` as timestamped JSON.
4. **Manual UI testing** — open Streamlit, run representative queries, eyeball the answers.

The thesis Limitations section should note this honestly: no automated regression suite means a change anywhere in the pipeline could silently break a previously verified scenario.

---

## What's next (not yet built)

- **Provider comparison re-run with unified prompts.** First run (`2026-05-16_204857`) used inconsistent prompts per provider — quality scores are not fully comparable. Re-run with fresh daily quota now that all generators share the same prompt. This gives the valid cross-provider latency + quality table for §5.5b.
- **Test-set expansion.** 9 queries is small. Target ~30 with more administrative and cross-lingual cases to reduce result variance.
- **Automated regression suite.** Run the routing + baseline + judge scripts on every change, fail loudly on regressions.
- **Real-usage data collection.** `QueryLogger` is live — accumulate a fixed window of real student usage before finalising the Results section.
- **Thesis writing.** Methodology 4.1–4.6 are ready to draft (material in `reports/02_*` and `reports/17_*`). Start here.
