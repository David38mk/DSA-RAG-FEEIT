# DSA-RAG-FEEIT

Retrieval-Augmented Generation (RAG) system serving as a 24/7 virtual assistant for the **Data Structures and Algorithms (DSA / ПСАА)** course at the **Faculty of Electrical Engineering and Information Technologies (FEEIT)**, Skopje, North Macedonia. Graduate thesis project.

The assistant handles both **technical questions** (algorithms, data structures, complexity analysis) and **administrative/support questions** (exams, grading, labs, syllabus). Multilingual: Macedonian (Cyrillic and Latin script) and English, with cross-lingual retrieval.

---

## Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Embeddings | `intfloat/multilingual-e5-base` (768 dim) |
| Vector store | ChromaDB (persistent, local) |
| LLM | Groq API — primary: `llama-3.3-70b-versatile`, judge: `llama-3.1-8b-instant` |
| UI | Streamlit (single-user, local) |
| Parsing | PyPDF2, python-docx |
| Logging | SQLite |

Constraints by design: zero budget (free-tier APIs only), Macedonian language mandatory, cross-lingual MK↔EN retrieval required.

---

## Quickstart

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your Groq API key (free tier — get one at https://console.groq.com/)
$env:GROQ_API_KEY = '<your-key>'
# OR put the key in D:\API_KEYS\GROK_API_KEY.txt and use launch_app.py

# 3. Run the Streamlit UI
python launch_app.py
# alternatively: streamlit run ui/streamlit_app_v2.py

# 4. Run an evaluation
python -m evaluation.scripts.run_baseline_comparison
python -m evaluation.scripts.run_llm_judge
```

---

## Project structure

### Repo root

| File | Purpose |
|---|---|
| `launch_app.py` | Entry point: loads `GROQ_API_KEY` from `D:\API_KEYS\GROK_API_KEY.txt`, sets env, runs Streamlit. |
| `requirements.txt` | Pinned Python dependencies. |
| `thesis_notes.md` | Working notes / current outline for the graduate thesis. |
| `WORKFLOW.md` | Phase-by-phase development log (how this project was built). |
| `THESIS_OUTLINE.md` | Skeleton + key points for the thesis write-up. |

### `src/` — application code

#### `src/ingestion/` — corpus extraction
| File | Purpose |
|---|---|
| `multi_format_extractor.py` | Extracts text from PDFs and DOCX, dispatching by file type. |
| `faq_parser.py` | Parses the FAQ DOCX into atomic Q&A units (each becomes one chunk). |
| `document_classifier.py` | Tags documents (lecture_slides, supplementary_slides, textbook, FAQ, admin). |
| `data_validator.py` | Sanity checks: encoding, empty extractions, classification coverage. |
| `load_all_documents.py` | Orchestrator that runs the full ingestion pass. |

#### `src/preprocessing/` — chunking
| File | Purpose |
|---|---|
| `smart_chunker.py` | Code-aware chunking. Merges code fences across paragraph breaks; treats Q&A pairs as atomic; targets 1000–2000 char chunks. |

#### `src/embeddings/`
| File | Purpose |
|---|---|
| `embedder.py` | Wrapper around the `intfloat/multilingual-e5-base` Sentence Transformer. |
| `build_index.py` | Embeds the chunk corpus and writes to ChromaDB. |

#### `src/vectorstore/`
| File | Purpose |
|---|---|
| `vector_store_manager.py` | ChromaDB wrapper: collection lifecycle, search with cosine similarity and metadata filters. |
| `rebuild_vectorstore.py` | Utility to drop and rebuild the persistent index from scratch. |

#### `src/retrieval/` — routing and retrieval
| File | Purpose |
|---|---|
| `enhanced_language_detector.py` | Detects MK / EN / Latin-script MK. 25 MK word patterns; 100% accuracy on internal test set. |
| `llm_intent_classifier.py` | LLM-based intent classifier (Groq). Used as the "slow path" in hybrid routing. |
| `hybrid_smart_retriever.py` | **Production retriever.** Combines rule-based intent (fast) with LLM fallback (when confidence < 0.8). Implements `route_query()` (adaptive n_results: support queries fetch up to 20 short FAQ chunks; technical queries fetch 7 longer lecture chunks) and `hybrid_search()` (metadata-boosted re-ranking). |
| `smart_retriever_v2.py` | Rule-based-only retriever from Phase 4. Imported but currently superseded by `hybrid_smart_retriever`. |
| `smart_retriever.py`, `smart_retriever_fixed.py` | **Legacy.** Earlier iterations kept for git/history reference. Not used in the production pipeline. |

#### `src/llm/` — generation pipeline
| File | Purpose |
|---|---|
| `base_generator.py` | Abstract base class. Defines the `generate()` contract all generators must satisfy. Makes `RAGPipeline` provider-agnostic. |
| `prompts.py` | **Single source of truth for all system prompts and user prompt builder.** All generators import `get_system_prompt()` and `build_user_prompt()` from here — ensures cross-provider comparisons are fair (prompt is not a confound). |
| `rag_pipeline.py` | End-to-end orchestration: retrieve → generate → log → memory update. Accepts any `BaseGenerator`, plus optional `logger` and `conversation_memory`. |
| `groq_generator.py` | Groq API generator — `llama-3.3-70b-versatile` (default), `llama-3.1-8b-instant`, Mixtral. Free tier: 100K tokens/day on 70B. |
| `gemini_generator.py` | Google Gemini generator — `gemini-2.5-flash` (default). Free tier: 5 RPM / 250K TPM / 20 RPD. Requires `GEMINI_API_KEY`. Uses `google.genai` SDK. |
| `openai_compatible_generator.py` | OpenAI-format generator for **OpenRouter** (free models: Llama 3.3 70B, Llama 3.2 3B) and **Ollama** (local). Configurable `base_url` and `max_retries`. |
| `conversation_memory.py` | Sliding window (10 turns) of recent (query, answer) pairs. Feeds the last 3 turns into the LLM system prompt for anaphora resolution. |
| `mistral_generator.py` | **Legacy.** Earlier Mistral-based generator from the planning phase. Not active. |

#### `src/telemetry/`
| File | Purpose |
|---|---|
| `query_logger.py` | SQLite-backed logger. Records sessions, queries, responses, and timing metrics for thesis-grade observability. Writes to `data/logs/queries.db`. |

#### `src/evaluation/`
| File | Purpose |
|---|---|
| `evaluation_framework.py` | Metric implementations: keyword coverage @k, answer-quality heuristic, intent accuracy, combined score. Loads test cases from `evaluation/datasets/routing_test_set.json`. |

#### `src/testing_archive/` — historical test scripts (not a pytest suite)

Kept as an archive of how each phase was verified at the time. Not part of the production codepath and not run automatically.

| File | Purpose |
|---|---|
| `test_phase1_complete.py` … `test_phase4.py` | Phase-gated smoke tests run during initial development. |
| `evaluate_routing_methods.py` | Compares rule-based, LLM, and hybrid routing on the test set. |
| `diagnose_phase1.py`, `diagnose_syllabus_issue.py` | Diagnostic scripts for known failure modes. |
| `faq_quality_test.py`, `code_extraction_test.py` | Targeted quality checks for FAQ chunking and code-block preservation. |
| `retrieval_testing.py`, `testing_chunker.py`, `testing_llm_context.py`, `quick_test.py` | Exploratory scripts kept for traceability. |

### `ui/`

| File | Purpose |
|---|---|
| `streamlit_app_v2.py` | **Production UI.** Auto language detection, model selector, conversation memory + logger wired in. |
| `streamlit_app.py` | **Legacy** Streamlit app from Phase A. Superseded. |
| `gradio_app.py` | Exploratory Gradio UI. Not maintained. |

### `evaluation/` — datasets, scripts, results

| Path | Purpose |
|---|---|
| `evaluation/README.md` | Index of metrics, how to reproduce. |
| `evaluation/datasets/routing_test_set.json` | Source-of-truth test set (currently 9 queries). |
| `evaluation/scripts/_keys.py` | Shared key loader (mirrors `launch_app.py`). |
| `evaluation/scripts/run_routing_eval.py` | Routing + retrieval + answer-quality eval on test set. |
| `evaluation/scripts/run_baseline_comparison.py` | RAG vs no-retrieval baseline (n_results=5, stays within free-tier 100K tokens/day budget). |
| `evaluation/scripts/run_llm_judge.py` | LLM-as-judge pairwise comparison — position-randomized, hallucination flags, accuracy 1–5. |
| `evaluation/scripts/run_provider_comparison.py` | Runs test set through all configured providers (Groq 70B, Groq 8B, Gemini Flash, OpenRouter Mistral 7B). Skips any provider with missing key. |
| `evaluation/results/` | Timestamped JSON outputs of each run. Cite specific files in the thesis. |

### `reports/` — historical phase reports and thesis docs

Historical phase reports are numbered chronologically (`01_phase1_ingestion.md` through `20_test_questions_admin.md`). See [`reports/INDEX.md`](reports/INDEX.md) for a one-line summary of each file in reading order. The `*_thesis_*.md` files contain methodology and results material being assembled for the final thesis.

### `data/` — runtime data (not all in git)

| Path | Purpose |
|---|---|
| `data/vectorstore/` | Persistent ChromaDB collection. |
| `data/logs/queries.db` | SQLite database written by `QueryLogger`. |
| `data/logs/exports/` | CSV exports of the log tables (generated on demand by `QueryLogger.export_csv()`). |

---

## What is and isn't production code

The repo contains several iterations of the same component (`smart_retriever.py` v1 → v2 → fixed → hybrid; `streamlit_app.py` → `_v2.py`; `mistral_generator.py` → `groq_generator.py`). The **production path** is:

```
launch_app.py
  └─ ui/streamlit_app_v2.py
       └─ src/llm/rag_pipeline.py (RAGPipeline)
            ├─ src/retrieval/hybrid_smart_retriever.py (HybridSmartRetriever)
            │    ├─ src/vectorstore/vector_store_manager.py
            │    ├─ src/retrieval/enhanced_language_detector.py
            │    └─ src/retrieval/llm_intent_classifier.py
            ├─ src/llm/groq_generator.py
            ├─ src/llm/conversation_memory.py
            └─ src/telemetry/query_logger.py
```

Everything outside this graph is either build-time tooling (`src/embeddings/build_index.py`, `src/vectorstore/rebuild_vectorstore.py`), evaluation, or legacy iterations kept for traceability.

---

## See also

- [WORKFLOW.md](WORKFLOW.md) — how this project was built, phase by phase.
- [THESIS_OUTLINE.md](THESIS_OUTLINE.md) — skeleton for the thesis write-up with key points.
- [evaluation/README.md](evaluation/README.md) — evaluation methodology and how to reproduce results.
- [reports/18_thesis_results_skeleton.md](reports/18_thesis_results_skeleton.md) — Results section draft for the thesis.
- [reports/INDEX.md](reports/INDEX.md) — one-line index of all 20 phase reports in chronological reading order.
