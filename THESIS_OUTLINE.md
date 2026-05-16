# Thesis Outline — Skeleton + Key Points

Working scaffold for the graduate thesis based on `thesis_notes.md`. Each section lists the key points it needs to cover. Items the user's original outline did not call out but should arguably be there are marked **[suggested addition]**.

When real numbers are required, defer to:
- `reports/02_phase1_thesis_methodology.md` (Phase 1 methodology details).
- `reports/17_thesis_methodology_phases_2_5.md` (Phases 2–5 methodology details).
- `reports/18_thesis_results_skeleton.md` (Results section in-progress).
- `evaluation/results/*.json` (raw measurements).
- `data/logs/queries.db` (real-usage data once collected).

---

## 1. Abstract

Key points:
- One sentence on the problem: 24/7 multilingual TA for the DSA course at FEEIT, both technical and administrative questions.
- One sentence on the approach: RAG pipeline with hybrid intent routing, multilingual cross-lingual retrieval (MK Cyrillic / Latin / EN), free-tier-only stack.
- One sentence on the result: hybrid routing 94% accuracy at 201 ms; LLM-as-judge shows RAG wins 67% over baseline with 3× fewer hallucinations.
- One sentence on contribution: documented zero-budget RAG architecture for a low-resource-language university course, with reproducible evaluation harness.

Length target: 200–250 words. Write it last.

---

## 2. Voved (Introduction)

Key points:
- Context: explosion of LLM use in education; gap for course-specific virtual assistants in **low-resource languages** (Macedonian).
- Problem: students need both **factual** course information (syllabus, grading, lab rules) and **conceptual** help (algorithms, complexity). General LLMs hallucinate the former; static FAQs can't handle the latter.
- Why this matters at FEEIT specifically: bilingual course materials (MK + EN textbook), MK FAQ documents, single instructor with limited office-hours capacity.
- Research question (suggest framing as): *Can a free-tier, multilingual RAG system reliably answer both technical and administrative questions for the DSA course, with measurable improvements over a no-retrieval baseline?*
- Contributions:
  1. End-to-end RAG architecture working entirely on free-tier APIs and a local vector store.
  2. Hybrid routing strategy that balances accuracy and latency.
  3. Cross-lingual retrieval validated on MK Cyrillic, Latin-script MK, and EN.
  4. Reproducible evaluation harness, including LLM-as-judge with explicit bias mitigations.
  5. **[suggested addition]** Empirical evidence that keyword-based answer-quality metrics undervalue RAG's hallucination-reduction contribution.

---

## 3. Literature review

Original outline: *LLMs, Types, assistants (virtual), RAG.*

Key points:
- **LLMs.** Brief taxonomy: encoder, decoder, encoder-decoder. Focus on instruction-tuned decoders (Llama 3, Mistral, Gemma) that this project uses.
- **LLM types relevant here.** General-purpose vs domain-tuned; size–latency trade-offs (8B fast / 70B accurate).
- **Virtual assistants / educational chatbots.** Prior art on course assistants. Mention what's been done in English; explicitly call out the **gap for Macedonian-language education**.
- **RAG.** Original Lewis et al. paper. Then the architecture variants: dense vs sparse, hybrid, ColBERT-style late interaction. Justify the dense + metadata-filter choice used here.
- **Cross-lingual retrieval.** Why multilingual embedding models (e.g., E5) work; the specific challenge of Latin-script transliterations.
- **[suggested addition] Evaluation methodologies for RAG.** Keyword-based, RAGAS, LLM-as-judge — pros, cons, biases. Sets up §4.7 (Evaluation methodology) and §5.4 (Results).
- **[suggested addition] Hallucination in academic chatbots.** Brief: why this is the dominant risk for student-facing systems and why RAG is the standard mitigation.

---

## 4. Methodology

### 4.1 Data and preprocessing

Key points:
- Source corpus: 21 source files → 1,565 documents → 1,100 chunks. Breakdown: 827 MK lecture PDFs (aggregated), 41 MK FAQ Q&A pairs (DOCX), 738-page EN textbook.
- Extraction stack: PyPDF2 for PDFs, python-docx for DOCX (`src/ingestion/multi_format_extractor.py`).
- Document classification (`document_classifier.py`): lecture_slides, supplementary_slides, textbook, faq, admin. Used downstream by retrieval filters.
- Chunking strategy (`smart_chunker.py`): 1000–2000 char target, code-aware merging (no splitting across code fences), FAQ Q&A treated as atomic units.
- Data validation (`data_validator.py`): coverage and encoding sanity.

### 4.2 Embeddings

Key points:
- Model: `intfloat/multilingual-e5-base`, 768 dim, multilingual.
- Why this model: handles both Cyrillic and Latin script natively, free, open-weights, established cross-lingual performance.
- Vector store: ChromaDB, persistent, cosine similarity, local-only (`data/vectorstore/`).
- **[suggested addition]** Brief note on why a re-ranker was not added — kept to the latency budget and zero-budget constraint.

### 4.3 Retrieval

Key points:
- Two-stage architecture: **language detection** → **intent classification** → **filtered retrieval**.
- Language detection (`enhanced_language_detector.py`): Cyrillic ratio + 25-pattern Latin-MK list. Handles the specific edge case of MK queries typed in Latin script.
- Intent classification: rule-based (fast, ~1 ms) → LLM fallback (Groq, ~1.5 s) → hybrid (rules if confidence ≥ 0.8, else LLM). Latency cost weighed against accuracy gain.
- Retrieval filters: support queries → FAQ + admin metadata; technical queries → lecture/textbook metadata; mixed → no filter.
- Hybrid re-ranking (`hybrid_search()`): retrieves k×2 candidates (k=7 → 14 candidates), applies metadata boost (0.5 for FAQ/admin on support queries) and language match, returns top-k=7.
- **Adaptive retrieval count by intent:** support queries use `min(k×2, 20)` = 14 chunks from the FAQ+admin filter, while technical queries use k=7 from lecture/textbook chunks. Rationale: FAQ Q&A pairs average ~200 chars vs ~1,500 chars for lecture slides, so 14 FAQ chunks cost fewer tokens than 7 lecture chunks while covering more of the 41-entry FAQ corpus.

### 4.4 LLM (generation)

Key points:
- **Provider-agnostic architecture.** All generators implement `BaseGenerator` (`src/llm/base_generator.py`), making `RAGPipeline` provider-neutral. Evaluated providers:
  - Groq `llama-3.3-70b-versatile` — primary, 100K tokens/day free.
  - Groq `llama-3.1-8b-instant` — fast/lightweight comparison.
  - Google Gemini `gemini-2.0-flash` — 1M tokens/day free; different architecture.
  - OpenRouter `mistral-7b-instruct:free` — free, no daily hard cap.
- Primary model for production: `llama-3.3-70b-versatile`. Generation params: temperature 0.3, top-p 0.9, max tokens 512.
- Prompt design: language-specific system prompts (MK/EN). Strict rule: answer ONLY from context for administrative questions; allowed to use general DSA knowledge for technical (with disclosure).
- Conversation memory: sliding window of 10 turns; last 3 turns inserted into the LLM prompt for reference resolution only.
- **Prompt standardisation** (`src/llm/prompts.py`): all providers receive identical system and user prompts. This is a methodological requirement for valid cross-provider comparison — without it, prompt wording becomes a confound.
- **[suggested addition]** Cross-provider comparison table is a key Result (§5.5b) — shows latency and quality across Groq 70B, Groq 8B, Gemini 2.5 Flash, and OpenRouter Llama 70B.

### 4.5 RAG pipeline

Key points:
- Orchestration in `src/llm/rag_pipeline.py`: retrieve → generate → log → memory update.
- Latency breakdown: ~87 ms retrieval + ~746 ms generation = **~833 ms total on the rules-only path**. When LLM fallback routing fires, total rises to ~3–5 s (one extra classifier call). These are the numbers to cite for production use.
- **Free-tier daily cap:** Groq 70B is limited to 100,000 tokens/day. At n_results=5 (~3K tokens/call), that supports ~33 queries/day before hitting the cap. Bulk evaluation runs should use n_results=5 and be spaced across days. Root cause of the 37s latencies observed during evaluation: daily cap exhaustion from back-to-back eval runs — not a production issue.
- Error handling: failures still logged as `success=false` rows for thesis observability.

### 4.6 Application

Key points:
- Streamlit UI (`ui/streamlit_app_v2.py`): single-user local deployment.
- Auto language detection from query text (Cyrillic-ratio heuristic).
- Model selector for sensitivity analysis (Llama 3.3 70B, 3.1 8B, Mixtral 8×7B, Gemma 2 9B).
- Session-scoped conversation memory.
- Persistent query log (`data/logs/queries.db`).

### 4.7 Evaluation methodology **[suggested addition]**

Key points:
- Test set: `evaluation/datasets/routing_test_set.json`, 9 cases (3 MK technical, 2 EN technical, 1 admin, 1 FAQ, 2 cross-lingual). **Acknowledge n is small** and discuss as a limitation.
- Metrics in three layers:
  1. **Routing accuracy** — intent classification on the test set.
  2. **Keyword-based answer quality** — `evaluation_framework.evaluate_answer_quality()`. Heuristic; topic coverage from `expected_topics`.
  3. **LLM-as-judge** — pairwise RAG vs baseline, judge model is `llama-3.1-8b-instant` (different from the generator's `llama-3.3-70b-versatile` to limit self-bias). A/B order randomized per query (seed=42). Outputs accuracy 1–5, source-usage flag, hallucination flag.
- Baseline definition: same Groq model, same language instructions, **retrieval removed**. Isolates the value of retrieval, not of the full system over a generic chatbot.
- Threats to validity: small sample; judge is from the same Llama family as the generator (bias not fully eliminated); single-judge single-run.

---

## 5. Results

(Already drafted as a skeleton in `reports/18_thesis_results_skeleton.md`. Pull the headline numbers below.)

Key points per subsection:
- **5.1 Data:** 21 sources → 1,565 docs → 1,100 chunks. Per-source breakdown.
- **5.2 Embeddings:** model choice; one qualitative cross-lingual example (MK query → EN chunk → MK answer).
- **5.3 Retrieval:** routing accuracy table (rule 76.7% / LLM 100% / hybrid 94%); latency table; the syllabus FAQ case study (pre/post fix).
- **5.4 LLM:** baseline-vs-RAG table — keyword heuristic shows 0.71 vs 0.72 (tie); LLM-as-judge shows **RAG 67% wins, accuracy 4.22 vs 3.44, hallucinations 2 vs 6 (3× reduction)**. The two-metric divergence is itself a result.
- **5.5 Pipeline:** end-to-end latency breakdown; per-intent and per-language stats from `QueryLogger` once real usage data is collected.
- **5.6 Application:** features delivered checklist; conversation memory usage statistics from logs.
- **5.7 Real-usage evaluation [suggested addition]:** reporting window, total queries, distinct sessions, most common failure modes, latency distribution. All from `data/logs/queries.db`.

---

## 6. Discussion

Original outline: *latency and shit.*

Key points:
- **Latency vs accuracy trade-off.** Pure LLM routing gives 100% accuracy at 1,555 ms; pure rules give 76.7% at <1 ms; hybrid 94% at 201 ms. Defend the hybrid choice against the 2 s end-to-end budget.
- **Why RAG won on admin queries and tied/lost on general CS concepts.** The baseline LLM has internalized the textbook from training; RAG cannot improve on facts the model already knows. RAG's value is targeted: course-specific facts, administrative accuracy, hallucination reduction.
- **Two-metric divergence.** Keyword scoring undervalued retrieval's primary contribution. Argue for LLM-as-judge or human eval as the appropriate methodology for RAG systems.
- **6.x Limitations [suggested addition]:**
  - Small test set (n=9). Variance is wide.
  - Judge is from the same model family as the generator. Position bias mitigated; self-bias not fully eliminated.
  - No automated regression suite.
  - Single-corpus (one course, one institution).
  - No user study with actual FEEIT students.
  - Latency regression in current measurement (~37 s) vs design target (833 ms) — flag for resolution.
  - Free-tier rate limits and queue jitter create variance in latency measurements.
- **6.x Threats to validity [suggested addition]:** measurement bias, judge bias, corpus bias (curated by the author).

---

## 7. Conclusion

Key points:
- Restate the contribution: end-to-end multilingual RAG for a low-resource-language university course, on zero budget, with reproducible evaluation.
- Strongest single number: **3× hallucination reduction (RAG 2 vs Baseline 6)** — direct evidence the system is safer for student-facing deployment than a generic chatbot.
- Hybrid routing achieved 94% intent accuracy within the latency budget.
- **7.x Future work [suggested addition]:**
  - Multi-vendor LLM fallback (Together AI, OpenRouter, HF Inference, Ollama local) for redundancy.
  - Test-set expansion to 30+ with broader administrative and cross-lingual coverage.
  - Real student user study, ideally A/B against status-quo office hours/email.
  - Automated regression CI.
  - Hallucination detection layer (claim-checker against retrieved chunks).
  - Cross-course generalization (a second FEEIT subject as a replication study).

---

## 8. References

Categories to populate:
- Foundational RAG: Lewis et al., 2020; Karpukhin et al. (DPR), 2020.
- Multilingual embeddings: Wang et al. (E5), 2022; Reimers & Gurevych (Sentence-BERT), 2019.
- LLM evaluation: RAGAS, LLM-as-judge papers (Zheng et al., 2023; Chiang et al., 2024).
- Educational chatbots / academic AI assistants — pick 3–5 representative.
- Macedonian / low-resource NLP — anything available; flag the scarcity as a sub-finding.
- Course materials being indexed (FEEIT syllabus PDF, textbook citation).
- Specific tool / model documentation: Groq, ChromaDB, Streamlit.

---

## Appendix A — Reproducibility statement **[suggested addition]**

Key points to include:
- Model versions: `llama-3.3-70b-versatile` (generator), `llama-3.1-8b-instant` (judge), `intfloat/multilingual-e5-base` (embeddings).
- Library versions: `pip freeze` from a clean install of `requirements.txt`.
- Chunk parameters: 1000–2000 chars, code-aware merging, atomic FAQ Q&A units.
- Random seeds: judge order randomization seed = 42; generation temperature 0.3; top-p 0.9.
- Data availability: lecture PDFs are course-internal and not redistributable; FAQ DOCX and textbook are cited but not included.
- Code: full repo, including `WORKFLOW.md` and per-phase reports under `reports/`.
- Cited result files: `evaluation/results/2026-05-15_153638_baseline_comparison.json`, `evaluation/results/2026-05-15_154927_llm_judge.json`.

---

## Writing-order recommendation

The most efficient drafting order (not the reading order):

1. Methodology 4.1 → 4.6 — already largely drafted in `reports/THESIS_DOCS_*`.
2. 4.7 Evaluation methodology — describes the harness in `evaluation/`.
3. Results 5.1 → 5.7 — fill the skeleton in `reports/18_thesis_results_skeleton.md` from JSON result files + the SQLite log.
4. Discussion — the analysis hinges on results so it follows naturally.
5. Literature review — easier to scope once you know exactly what you've claimed.
6. Conclusion + Future work.
7. Introduction (Voved) — easier once everything else exists.
8. Abstract — last.
9. References — populate as you cite; do not leave to the end.
