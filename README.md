# RAG-chemistry

A Retrieval-Augmented Generation (RAG) system built **from scratch** (no LangChain/LlamaIndex) to answer questions over a library of chemistry-of-coatings textbooks (PDFs, split by chapter, mostly in English). Runs **100% locally** on Apple Silicon using Ollama, FAISS, and open embedding models — bilingual (Spanish/English) questions, answers always cite their exact source.

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
        │             chapter boundary; metadata: {book, chapter, page}
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
| Keyword hit rate (in-domain) | 0.90 |
| Correct-book hit rate (in-domain) | 0.89 |
| Citation validity rate | 0.70 |
| Refusal rate (out-of-domain) | 0.80 |
| Fabricated-citation rate (out-of-domain) | 0.40 |

Measured on an 11-book corpus (6957 chunks). Metrics are lower than an earlier 2-book run (1.00/1.00/0.80/1.00/0.20) — expected when scaling the corpus 5.5x without re-tuning `top_k` or the reranker: see [`docs/07-evaluacion.md`](docs/07-evaluacion.md) for the full comparison and why this isn't hidden or tuned away.

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
├── docs/                    # one file per phase: the why behind each decision
├── notebooks/
│   └── pipeline_completo.ipynb   # interactive walkthrough with real outputs
├── data/{raw,processed}/    # raw/ has source PDFs (not committed — copyright)
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

PDF source files are not committed to this repo (copyright). Drop your own book folders into `data/raw/<Book Title>/` — either one PDF per chapter, or a single PDF for the whole book (chapters are then derived from its embedded table of contents).

## Running the pipeline

```bash
python -m src.extraction.run        # data/raw/        -> data/processed/*/pages.jsonl
python -m src.chunking.run          # pages.jsonl       -> chunks.jsonl
python -m src.embeddings.run        # chunks.jsonl      -> embeddings.npy
python -m src.indexing.build_index  # embeddings.npy    -> vectorstore/index.faiss
python -m src.evaluation.run_eval   # runs the 15-question test set, saves a report

pytest                                # 44 tests across every stage
```

Or open [`notebooks/pipeline_completo.ipynb`](notebooks/pipeline_completo.ipynb) for an interactive, explained walkthrough of every stage with real outputs from this corpus.

## Known limitations

- Table and figure extraction (beyond plain text) isn't implemented yet — documented as a deliberate scope cut in [`docs/01-extraccion.md`](docs/01-extraccion.md).
- The bibliography filter is a tuned regex heuristic, not a learned classifier — it can miss reference styles it wasn't tuned against (see [`docs/04-indexacion.md`](docs/04-indexacion.md)).
- A 7B local LLM doesn't follow prompt instructions 100% of the time (e.g. occasionally cites a source while still correctly refusing to answer) — see [`docs/07-evaluacion.md`](docs/07-evaluacion.md).
- No LLM-as-judge evaluation of answer quality, only retrieval/citation correctness — a natural next step if this grows past a portfolio project.
- Embeddings and reranking are forced onto CPU rather than Apple Silicon's GPU (MPS) — found a real segfault from `faiss` and PyTorch fighting over the same OpenMP runtime when used together in one process; see [`docs/04-indexacion.md`](docs/04-indexacion.md).
