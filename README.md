# 📖 PubVector

**Build a rare-disease knowledge base from PubMed/PMC — then chat with it, locally and privately.**

PubVector searches PubMed for the article types you care about (reviews, case reports, trials,
guidelines, commentary), fetches structured full text, extracts case narratives, downloads
PDFs and figures, and builds a [FAISS](https://github.com/facebookresearch/faiss) vector
database. An [Ollama](https://ollama.com)-backed chatbot then answers questions over that
database **on your own machine** — no data leaves your computer, no API bills.

Built for life-sciences and computational-biology students: **click "Build knowledge base",
then "Chat".** Every setting has a sensible default; the power is tucked behind *Advanced*.

> It's a **single Python file** (`pubvector_bioc_rag.py`) that runs two ways — a Streamlit web
> app *or* a command-line pipeline — and auto-detects which.

---

## ✨ Features

- **Zero-config to start.** Good defaults everywhere; a student never *has* to open a setting.
- **Curated rare-disease panels.** 30+ ready-made disease queries (Fabry, Gaucher, Pompe, the
  MPS family, Wilson, ASMD, CTX, and more) with abbreviations anchored to full names.
- **Structured full text, not just abstracts.** Pulls NCBI BioC JSON, keeps section structure,
  tables, and figure captions.
- **Case-narrative extraction** from case reports.
- **PDFs + figure images** downloaded from the PMC Open Access service and Europe PMC.
- **Local RAG chatbot** via Ollama — *you* pick the model, *your* GPU (or CPU) runs it.
- **Auto-detected models.** The chatbot lists the models already installed in your Ollama; no
  typing tags.
- **Streaming answers.** Responses appear word-by-word as the model generates them.
- **Citations with clickable links.** Every answer shows its sources with direct
  PMC / PubMed / DOI links.
- **Remembers your settings.** Email, output folder, and last-used model are saved between
  launches (your API key is *never* written to disk).

---

## 🚀 Quickstart

### 1. Install the Python dependencies

```bash
python -m pip install -r requirements.txt
```

### 2. Install Ollama and pull a model (for the chatbot)

[Ollama](https://ollama.com) runs the language model locally. Install it, then:

```bash
ollama pull medgemma:latest    # or any model you like — llama3.2, qwen, mistral…
ollama serve                   # leave this running
```

> The chatbot auto-detects whatever models you've pulled. `medgemma` is a good default for
> clinical text, but anything works.

### 3. Launch the web app

```bash
streamlit run pubvector_bioc_rag.py
```

Enter your email (NCBI requires it), pick a disease panel, click **Build knowledge base** →
then open the **Chatbot** tab and ask away.

---

## 🖥️ Two ways to run

PubVector is one file that detects how it was launched.

### Web app (recommended for most users)

```bash
streamlit run pubvector_bioc_rag.py
```

### Command-line pipeline (for batch / scripted runs)

```bash
# Quick test: 10 articles per disease, with PDFs
python pubvector_bioc_rag.py --email you@uni.edu --max-per-disease 10 --download-pdfs

# Full run: many articles + PDF→Markdown + build the RAG database
python pubvector_bioc_rag.py --email you@uni.edu --max-per-disease 1000 \
    --download-pdfs --convert-to-markdown --build-rag --rag-source bioc \
    --output ./raredx_full

# Inspect the built-in panels (no --email needed)
python pubvector_bioc_rag.py --list-diseases
python pubvector_bioc_rag.py --list-article-types

# Debug PMC Open-Access access for one article
python pubvector_bioc_rag.py --email you@uni.edu --test-pmcid PMC1234567 --download-pdfs
```

NCBI throttles requests; passing `--api-key YOUR_KEY` raises the allowed rate (~3 → ~10 req/s)
and is strongly recommended for large runs.

<details>
<summary>All CLI flags</summary>

`--email` · `--api-key` · `--diseases` · `--article-types` · `--max-per-disease` ·
`--output` · `--download-images` · `--download-pdfs` · `--no-pmc-oa-filter` ·
`--no-raw-bioc` · `--convert-to-markdown` · `--build-rag` · `--rag-source` ·
`--rag-device` · `--embedding-model` · `--bioc-chunk-size` · `--bioc-chunk-overlap` ·
`--md-chunk-size` · `--md-chunk-overlap` · `--user-agent` · `--log-level` ·
`--test-pmcid` · `--list-diseases` · `--list-article-types`

</details>

---

## 🧬 How it works

The pipeline is a linear sequence of stages:

1. **Search PubMed** for the selected diseases × article types.
2. **Map PMID → PMCID** to find full-text-available articles.
3. **Fetch BioC full text** (NCBI BioC JSON API).
4. **Extract** body text, case narratives, and figure/table captions.
5. **Download PDFs** (PMC Open Access service) and **figure images** (Europe PMC) — these are
   saved for manual inspection/reading but are **not** currently fed into the FAISS retrieval
   index used by the chatbot or the paper's evaluation; retrieval is built from BioC (and,
   optionally, PDF→Markdown) text only.
6. **PDF → Markdown** (optional, via `pymupdf4llm`).
7. **Build the FAISS RAG database** from BioC (default), Markdown, or both, retrieving the
   top-10 (`k=10`) most similar chunks per query at chat time.

Once the database is built, the **Chatbot** tab retrieves the most relevant chunks for your
question and asks your local Ollama model to answer — with the source passages and links shown
beneath every reply.

Embeddings use `BAAI/bge-small-en-v1.5` by default (small and CPU-friendly); bge-base, bge-large,
and a biomedical PubMedBERT-based model are offered as curated alternatives under *Advanced*, and
you can add **any** other sentence-transformers-compatible HuggingFace model by pasting its
model ID or URL — already-downloaded models are marked ✅, new ones download automatically the
first time you build with them selected. The on-disk index format is plain LangChain FAISS
(`index.faiss` + `index.pkl`).

---

## 📂 Output layout

Everything lands under your chosen `--output` folder (default `./raredx_data`):

```
state/            pmids, PMID→PMCID maps, provenance
interim/          metadata / cases / captions (jsonl)
raw_bioc/         <PMCID>.json   (structured full text)
pdfs/             downloaded PDFs
images/           downloaded figure images
parsed_markdown/  <PMCID>.md     (if --convert-to-markdown)
vector_db/        index.faiss + index.pkl   (the RAG database)
*.parquet         metadata / cases / captions / images tables
publication_summary.txt, run_summary.json
```

---

## 🩺 Disease panels & article types

Run `--list-diseases` for the full set. A sample of the 30+ panels:

> Fabry · Gaucher · Pompe · Niemann-Pick · Wilson · Cystinosis · ASMD · CTX ·
> Mucopolysaccharidosis (I / II / IVA / VI) · Familial Mediterranean Fever ·
> Transthyretin Amyloidosis · X-linked Hypophosphatemia · Alagille Syndrome · …

Article types (`--list-article-types`): **review**, **case_report**, **trial**, **guideline**,
**commentary**. The default selection is `review` + `case_report`.

---

## 📦 Requirements

- **Python 3.10+**
- The pip packages in [`requirements.txt`](requirements.txt) (Streamlit, Biopython, pandas,
  FAISS, LangChain, sentence-transformers, PyMuPDF, …)
- **[Ollama](https://ollama.com)** — for the chatbot tab only. The search/fetch pipeline runs
  without it.

Heavy/optional dependencies (PyTorch, FAISS, LangChain, pymupdf4llm) are imported lazily, so
the core search-and-fetch pipeline works even if you haven't installed the RAG stack.

---

## 📊 Evaluation data & paper

[`evaluation/`](evaluation/) contains everything behind the paper's 4,800-answer, 10-model,
4-domain, 4-retrieval-condition blind evaluation: the 120 test questions, the raw model
answers, both judges' scores (GPT-5.5 primary, Claude Sonnet 5.5 as a second, independent blind
judge used to check inter-rater reliability), the judging rubric/prompt generator, and the
statistical-analysis scripts (paired Wilcoxon + Holm correction) used to produce every reported
p-value — see [`evaluation/README.md`](evaluation/README.md) for how the pieces fit together
and how to reproduce the results.

---

## 🤝 Contributing

Issues and pull requests are welcome. PubVector is intentionally a **single file** — new
pipeline stages are added as top-level functions and wired into both the CLI and the Streamlit
app. Please keep both entry points in sync.

---

## 📄 License

Released under the MIT License — see [`LICENSE`](LICENSE).

---

## 🙏 Acknowledgements

Built on the openly available [NCBI E-utilities / BioC API](https://www.ncbi.nlm.nih.gov/),
[Europe PMC](https://europepmc.org/), [Ollama](https://ollama.com),
[LangChain](https://github.com/langchain-ai/langchain),
[FAISS](https://github.com/facebookresearch/faiss), and the
[BAAI BGE](https://huggingface.co/BAAI/bge-small-en-v1.5) embedding models.

> Please respect NCBI's [usage policies](https://www.ncbi.nlm.nih.gov/home/about/policies/) and
> the licenses of individual articles. PubVector is a research aid, **not** a source of medical
> advice.
