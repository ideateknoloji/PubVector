# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

PubVector builds a rare-disease knowledge base from PubMed/PMC. It searches PubMed for selected
article types, fetches NCBI BioC full text, downloads PDFs/images, and builds a local **FAISS**
RAG index (bge embeddings) that an Ollama-backed chatbot queries. The whole app is the single
file `pubvector_bioc_rag.py`. No external service beyond Ollama is needed.

The same file runs two ways and auto-detects which (see the dispatch block at the bottom,
`_running_under_streamlit()`):
- **Streamlit web app** — `run_app()` is called when launched via `streamlit run`.
- **CLI pipeline** — `main()` runs when launched via `python`.

> Note: the in-code docstrings and `requirements.txt` refer to the script as `pubvector.py`,
> but the actual filename is `pubvector_bioc_rag.py`. Use the real filename in commands.

## Commands

```bash
# Install (Python deps)
python -m pip install -r requirements.txt

# External, non-pip dependency for the chatbot:
#   install Ollama (https://ollama.com) and pull the model:
ollama pull medgemma:latest      # must also be running: `ollama serve`

# Launch the web app
streamlit run pubvector_bioc_rag.py

# CLI: quick test run (10 articles/disease/type, with PDFs)
python pubvector_bioc_rag.py --email you@uni.edu --max-per-disease 10 --download-pdfs --log-level DEBUG

# CLI: full run with markdown conversion + FAISS RAG DB
python pubvector_bioc_rag.py --email you@uni.edu --max-per-disease 1000 \
    --download-pdfs --convert-to-markdown --build-rag --rag-source bioc --output ./raredx_full

# Inspect the built-in panels (no --email required)
python pubvector_bioc_rag.py --list-diseases
python pubvector_bioc_rag.py --list-article-types

# Download one PDF and exit (debugging PMC OA access)
python pubvector_bioc_rag.py --email you@uni.edu --test-pmcid PMC1234567 --download-pdfs
```

There is **no test suite, linter config, or build step** in this repo.

NCBI is rate-limited in code (`NCBI_RATE_LIMIT_*`); passing `--api-key` raises the allowed rate.

## Architecture

The pipeline is a linear sequence of numbered stages, each a top-level function, orchestrated by
`run_pipeline()`. The Streamlit app runs `run_pipeline` **on a background thread** and streams
logs to the UI; cooperative cancellation is done via the `should_stop` callback that
`run_pipeline` polls between diseases and articles.

Function names are in `pubvector_bioc_rag.py`:
1. **PubMed search** — `search_pubmed_by_disease` / `build_disease_query` (Bio.Entrez)
2. **PMID → PMCID mapping** — `map_pmid_to_pmcid`
3. **BioC full-text fetch** — `fetch_bioc_article` (NCBI BioC JSON API)
4. **Text/caption extraction** — `extract_text_from_bioc`, `extract_captions_from_bioc`
5. **PDF download** — `download_pdf` (PMC OA service; `pmc_download_candidates` tries multiple URL forms)
6. **Figure image download** — `get_image_urls_from_europepmc` / `download_image` (Europe PMC)
7. *(removed — was BioC chunking)*
8. **PDF → Markdown** — `convert_pdfs_to_markdown` (pymupdf4llm, optional `--convert-to-markdown`)
9. **BioC/Markdown → FAISS RAG DB** — `build_rag_database*` (optional `--build-rag`)

After the RAG stage the **Chatbot tab** becomes usable: `load_chat_vector_db` loads the FAISS
index, and `_build_rag_prompt`/`_call_ollama` answer from the retrieved chunks.

### Two key configuration tables (top of file)

- **`ARTICLE_TYPE_CLASSES`** — maps internal article-type keys (`review`, `trial`,
  `case_report`, `guideline`, `commentary`) to PubMed `[pt]` tokens, `[tiab]` fallbacks, and
  post-hoc `pt_match` classification substrings. **`pt` strings must match NLM's spelling
  verbatim** (e.g. `"Case Reports"` plural, `"Meta-Analysis"` hyphenated) — a typo silently
  matches nothing. PT searches are not exploded, so sibling types must each be listed. The
  `narrative: True` flag (only `case_report`) means records get segmented into a case narrative;
  otherwise full body text is kept. Default selection: `["review", "case_report"]`.

- **`DISEASE_SYNONYMS`** — maps a canonical disease label (stored verbatim as the `disease` tag
  on every record) to a list of `[Title/Abstract]` search terms that are OR-ed together. This
  anchors abbreviations (ASMD, CTX, MPS II) to full names. `resolve_disease_panel` filters this
  case-insensitively against `--diseases`.

### RAG sourcing

`--rag-source` / `RAG_SOURCE_OPTIONS` chooses what the FAISS index is built from: `bioc`
(default, recommended — needs raw BioC JSON, so `save_raw_bioc` is force-enabled), `markdown`
(needs the stage-8 PDF Markdown), or `hybrid` (both). Embedding model is `--bioc-embedding-model`
(`bge-small` or `bge-base`, `BIOC_EMBEDDING_SHORT_NAMES`); the on-disk format
(`index.faiss` + `index.pkl` via `FAISS.save_local`) is plain LangChain FAISS. Only Vector RAG is
supported (FAISS, no BM25).

### Output layout (under `--output`, default `./raredx_data`)

`state/` (pmids, pmid→pmcid, provenance) · `interim/` (metadata/cases/captions jsonl) · `pdfs/` ·
`images/` · `raw_bioc/<PMCID>.json` · `parsed_markdown/<PMCID>.md` (if `--convert-to-markdown`) ·
`vector_db/{index.faiss,index.pkl}` · top-level `*.parquet`, `publication_summary.txt`,
`run_summary.json`.

## Conventions

- **Everything lives in `pubvector_bioc_rag.py`** (single-file rule). New stages/helpers go as
  top-level functions, wired into `run_pipeline`, exposed via both `build_arg_parser` (CLI) and
  `run_app` (Streamlit); keep both entry points in sync when adding a feature.
- Heavy/optional deps (pymupdf4llm, torch, langchain, faiss, sentence-transformers) are **lazily
  imported inside the functions that need them** so the core pipeline and CLI run without them
  installed. Preserve this pattern.
- The logger name is `raredx` and much internal naming still uses "RareDx" — this is the
  project's prior name; treat it as synonymous with PubVector.

## Working Principles

### 1. Think Before Coding
Don't assume. Don't hide confusion. Surface tradeoffs.

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First
Minimum code that solves the problem. Nothing speculative.
- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes
Touch only what you must. Clean up only your own mess.

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution
Define success criteria. Loop until verified.

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"
