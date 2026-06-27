# RAG-chemistry

A Retrieval-Augmented Generation (RAG) system built **from scratch** (no LangChain/LlamaIndex) to answer questions over a 436-source chemistry-of-coatings corpus: full textbooks, vendor data sheets, papers, and standards (mostly English, some Spanish), including a personal archive accumulated over years of professional coatings experience. Runs **100% locally** on Apple Silicon using Ollama, FAISS, and open embedding models — bilingual (Spanish/English) questions, answers always cite their exact source.

This is a learning + portfolio project: every architectural decision — including the dead ends — is documented in [`docs/`](docs/), and the system was evaluated with real, verified test cases rather than left untested.

## Why build it from scratch?

Frameworks like LangChain hide the mechanics of chunking, embedding, indexing, and retrieval behind abstractions. Building each stage manually makes the trade-offs explicit and shows a working understanding of how RAG actually works, not just how to call a library.

## Architecture

```
PDF chapters (native + scanned)
        │
        ▼
  1. Extraction   ── PyMuPDF (native text) + Tesseract OCR (scanned), chapter from
        │             filename or from the PDF's embedded TOC
        ▼
  2. Chunking     ── token-based chunks (600 tok, 100 overlap), never crossing a
        │             chapter boundary; metadata: {book, chapter, page, category}
        ▼
  3. Embeddings   ── multilingual-e5-base (local) — Spanish queries, English source
        │
        ▼
  4. Vector index ── FAISS (IndexFlatIP), excluding bibliography & structural
        │             sections (Index, TOC, Front Matter) found to be noise
        ▼
  5. Retrieval    ── FAISS top-20 (recall) -> cross-encoder reranking (precision) -> top-5
        │
        ▼
  6. Generation   ── local LLM via Ollama, forced to cite [Book, Chapter, p. X-Y],
                      refuses instead of guessing when the excerpts don't cover it
```

Plus a **7th stage, evaluation**: a 15-question test set, verified against the real corpus, scored with deterministic metrics (no LLM-as-judge) — see [Results](#results) below.

## Results

From the latest evaluation run ([`docs/07-evaluacion.md`](docs/07-evaluacion.md), full methodology and iteration history):

| Metric | Value |
|---|---|
| Keyword hit rate (in-domain) | 0.80 |
| Correct-book hit rate (in-domain, where a single source is still expected) | 0.67 |
| Citation validity rate | 0.70 |
| Refusal rate (out-of-domain) | 0.60-1.00 (varies run to run) |
| Fabricated-citation rate (out-of-domain) | 0.20-0.80 (varies run to run) |

Measured on a 436-source corpus (22386 indexed chunks) — 8 full books plus a 685-PDF personal archive (vendor data sheets, papers, standards) accumulated over years of professional coatings experience, integrated in a later phase (see [`docs/01-extraccion.md`](docs/01-extraccion.md)). Growing the corpus this much surfaced a real evaluation-tooling bug (a citation regex that broke on book titles containing a comma) and made the original 2-book test set's single-source assumptions stale for a few topics — both fixed, with the full before/after numbers and reasoning in [`docs/07-evaluacion.md`](docs/07-evaluacion.md). Out-of-domain metrics vary across runs because the local LLM samples at temperature > 0 — also documented there rather than smoothed over.

**Example — in-domain, Spanish:**
> *"¿Qué es la corrosión por picadura?"*
> La corrosión por picadura es un tipo de corrosión localizada que se caracteriza por la formación de cavidades... **[Handbook of Corrosion Engineering, 5. Corrosion Failures, p. 343-345]**.

**Example — out-of-domain (correct refusal, not a hallucination):**
> *"¿Cuál es la capital de Mongolia?"*
> Lo siento, pero los fragmentos proporcionados no contienen información sobre la capital de Mongolia... Los pasajes se centran en reacciones químicas y datos de corrosión.

The evaluation phase found and fixed three real problems along the way (index pages cited in refusals, citations attached to correct refusals, a flawed test case) — see [`docs/07-evaluacion.md`](docs/07-evaluacion.md) for the full, honest account.

## Project structure

```
RAG-chemistry/
├── README.md
├── app.py                   # Streamlit chat UI over the pipeline
├── docs/                    # one file per phase: the why behind each decision
├── notebooks/
│   └── pipeline_completo.ipynb   # interactive walkthrough with real outputs
├── data/{raw,processed}/    # raw/ has source PDFs and other documents
│                            # (not committed — copyright + some confidential)
├── vectorstore/             # FAISS index + metadata (not committed — derived)
├── eval/results/            # evaluation run history (committed — small, no copyrighted data)
├── src/
│   ├── extraction/          # PDF -> pages.jsonl
│   ├── chunking/             # pages.jsonl -> chunks.jsonl
│   ├── embeddings/           # chunks.jsonl -> embeddings.npy
│   ├── indexing/             # embeddings -> FAISS index, noise filters
│   ├── retrieval/            # FAISS search + cross-encoder reranking
│   ├── generation/           # prompt + Ollama call, grounded answers
│   └── evaluation/           # test set + metrics + eval runner
└── tests/                   # one test module per src/ submodule
```

## Stack

- **Language:** Python (no RAG frameworks — built from first principles)
- **LLM:** [Ollama](https://ollama.com/) running `qwen2.5:7b-instruct` (local)
- **Embeddings:** `intfloat/multilingual-e5-base` via sentence-transformers
- **Reranker:** `BAAI/bge-reranker-base` (cross-encoder)
- **Vector store:** FAISS (`IndexFlatIP`)
- **OCR:** Tesseract (via pytesseract), for scanned PDFs
- **PDF parsing:** PyMuPDF, pdfplumber

## Setup

```bash
# System dependencies (macOS)
brew install poppler tesseract ollama
ollama pull qwen2.5:7b-instruct
brew services start ollama

# Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

PDF source files are not committed to this repo (copyright, plus some personal/confidential documents in this author's own archive). Drop a book into `data/raw/[Author_Year]_Title/` (brackets required) — either one PDF per chapter, or a single PDF for the whole book (chapters are then derived from its embedded table of contents). Anything in `data/raw/` *without* that bracket naming is instead treated as a folder of independent standalone documents (vendor data sheets, papers...), each cited by its own filename — see [`docs/01-extraccion.md`](docs/01-extraccion.md).

## Running the pipeline

```bash
python -m src.extraction.run        # data/raw/        -> data/processed/*/pages.jsonl
python -m src.chunking.run          # pages.jsonl       -> chunks.jsonl
python -m src.embeddings.run        # chunks.jsonl      -> embeddings.npy
python -m src.indexing.build_index  # embeddings.npy    -> vectorstore/index.faiss
python -m src.evaluation.run_eval   # runs the 15-question test set, saves a report

pytest                                # 65 tests across every stage
```

Or open [`notebooks/pipeline_completo.ipynb`](notebooks/pipeline_completo.ipynb) for an interactive, explained walkthrough of every stage with real outputs from this corpus.

For a chat UI instead: `streamlit run app.py` — a thin presentation layer over the same `answer_question()` used by the notebook and the evaluation suite, with a sources panel showing each citation's exact excerpt.

## Known limitations

- Table and figure extraction (beyond plain text) isn't implemented yet — documented as a deliberate scope cut in [`docs/01-extraccion.md`](docs/01-extraccion.md).
- The bibliography filter is a tuned regex heuristic, not a learned classifier — it can miss reference styles it wasn't tuned against (see [`docs/04-indexacion.md`](docs/04-indexacion.md)).
- A 7B local LLM doesn't follow prompt instructions 100% of the time (e.g. occasionally cites a source while still correctly refusing to answer) — see [`docs/07-evaluacion.md`](docs/07-evaluacion.md).
- No LLM-as-judge evaluation of answer quality, only retrieval/citation correctness — a natural next step if this grows past a portfolio project.
- Embeddings and reranking are forced onto CPU rather than Apple Silicon's GPU (MPS) — found a real segfault from `faiss` and PyTorch fighting over the same OpenMP runtime when used together in one process; see [`docs/04-indexacion.md`](docs/04-indexacion.md).
