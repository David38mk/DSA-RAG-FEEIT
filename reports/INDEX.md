# Reports — Reading Index

Chronological reading order of the development history. Files are numbered so a single `ls reports/` shows the timeline. Read top-to-bottom to follow how the project was built; jump in by topic using the per-phase headers below.

## Phase 1 — Data ingestion

| File | What it covers |
|---|---|
| [01_phase1_ingestion.md](01_phase1_ingestion.md) | Phase 1 completion report — 21 source files → 1,565 documents via multi-format extractor, FAQ parser, document classifier, and data validator. |
| [02_phase1_thesis_methodology.md](02_phase1_thesis_methodology.md) | Phase 1 written up in thesis-methodology style (feeds §4.1 Data and Preprocessing). |

## Phase 2 — Chunking

| File | What it covers |
|---|---|
| [03_phase2_chunking.md](03_phase2_chunking.md) | Phase 2 build — code-aware chunk merging, Q&A atomic units, 1000–2000 char targets. |
| [04_phase2_chunking_metrics.md](04_phase2_chunking_metrics.md) | Numbers from the chunking pass — chunk count distribution and code-block preservation rates. |
| [05_phase2_faq_chunking_fix.md](05_phase2_faq_chunking_fix.md) | Bug investigation — long FAQ chunks (the 1,575-char syllabus chunk) suffer embedding dilution. Identifies the root cause behind the later FAQ-boost fix. |

## Phase 3 — Vector store and embeddings

| File | What it covers |
|---|---|
| [06_phase3_vectorstore.md](06_phase3_vectorstore.md) | Phase 3 setup — ChromaDB persistent store, `intfloat/multilingual-e5-base` embeddings, cosine similarity. |
| [07_phase3_vectorstore_results.md](07_phase3_vectorstore_results.md) | Phase 3 results — 1,100 chunks indexed, cross-lingual sanity checks, top-k retrieval quality. |

## Phase 4 — Smart retrieval (rule-based)

| File | What it covers |
|---|---|
| [08_phase4_smart_retrieval.md](08_phase4_smart_retrieval.md) | Phase 4 build — rule-based intent routing with MK + EN keyword patterns and per-intent metadata filters. |
| [09_phase4_debugging.md](09_phase4_debugging.md) | Early debug log — cross-lingual prompt fixes, introduction of `smart_retriever_fixed.py`. |

## Phase A — Critical infrastructure fixes

| File | What it covers |
|---|---|
| [10_phaseA_critical_fixes.md](10_phaseA_critical_fixes.md) | Step-by-step guide for ChromaDB corruption, intent confusion, and missing English textbook embeddings. |

## Phase 5 — Language detection (incl. Latin-script Macedonian)

| File | What it covers |
|---|---|
| [11_phase5_language_detection.md](11_phase5_language_detection.md) | Phase 5 README — Groq integration, Streamlit + Gradio UIs, 25-pattern Latin-MK detection. |
| [12_phase5_latin_mk_changelog.md](12_phase5_latin_mk_changelog.md) | Changelog for the Latin-script Macedonian detector ("Dali ke imame lab?" → routed as MK). |
| [13_phase5_latin_quick_deploy.md](13_phase5_latin_quick_deploy.md) | Quick-deploy instructions for the Latin-MK fix. |

## Phase B — Streamlit v2 UX overhaul

| File | What it covers |
|---|---|
| [14_phaseB_streamlit_v2.md](14_phaseB_streamlit_v2.md) | UX improvements — auto-initialization, auto language detection, model selector, cleaner UI. The basis for `ui/streamlit_app_v2.py`. |

## Phase 6 — Hybrid routing

| File | What it covers |
|---|---|
| [15_phase6_debugging_motivation.md](15_phase6_debugging_motivation.md) | 19.03.2026 debug log — surfaces retrieval failures and first proposes the hybrid approach. |
| [16_phase6_hybrid_routing.md](16_phase6_hybrid_routing.md) | Phase 6 completion — rule + LLM hybrid intent classification, 94% accuracy at 201 ms. |

## Thesis docs (cross-cutting)

| File | What it covers |
|---|---|
| [17_thesis_methodology_phases_2_5.md](17_thesis_methodology_phases_2_5.md) | Phases 2–5 written up in thesis-methodology style. |
| [18_thesis_results_skeleton.md](18_thesis_results_skeleton.md) | Results section skeleton with placeholders for live usage data. |

## Operational reference

| File | What it covers |
|---|---|
| [19_operational_update_docs.md](19_operational_update_docs.md) | How to refresh FAQ / course info and rebuild embeddings. |
| [20_test_questions_admin.md](20_test_questions_admin.md) | Hand-collected test questions in Latin-script Macedonian, organized by category (administrative, grading, labs, etc.). |

---

## Suggested reading paths

- **First time through:** Read in numeric order. The build narrative reads naturally.
- **Just the thesis-relevant material:** `02 → 17 → 18 → 16` (Phase 1 methodology, Phases 2–5 methodology, Results skeleton, Hybrid routing results).
- **Just the bugs and fixes:** `05 (FAQ dilution) → 09 (Phase 4 debug) → 10 (critical fixes) → 12 (Latin-MK fix) → 15 (Phase 6 motivation)`.
- **For onboarding someone new:** Top-level `README.md` → `WORKFLOW.md` → this index → cherry-pick by interest.
