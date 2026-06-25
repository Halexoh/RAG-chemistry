# RAG-chemistry

A Retrieval-Augmented Generation (RAG) system built **from scratch** (no LangChain/LlamaIndex) to answer questions over a library of chemistry-of-coatings textbooks (PDFs, split by chapter, mostly in English). Runs **100% locally** on Apple Silicon using Ollama, FAISS, and open embedding models.

This is a learning + portfolio project: every architectural decision is documented in [`docs/`](docs/), and every answer the system gives cites its exact source (book, chapter, page).

## Why build it from scratch?

Frameworks like LangChain hide the mechanics of chunking, embedding, indexing, and retrieval behind abstractions. Building each stage manually makes the trade-offs explicit and shows a working understanding of how RAG actually works, not just how to call a library.

## Architecture

```
PDF chapters (native + scanned)
        │
        ▼
  1. Extraction  ── PyMuPDF (native text) + Tesseract OCR (scanned) + pdfplumber (tables)
        │
        ▼
  2. Chunking    ── token-based chunks with overlap, metadata: {book, chapter, page}
        │
        ▼
  3. Embeddings  ── multilingual sentence-transformer model (local)
        │
        ▼
  4. Vector index ── FAISS (local, no server)
        │
        ▼
  5. Retrieval   ── top-k similarity search (+ optional reranking)
        │
        ▼
  6. Generation  ── local LLM via Ollama, forced to cite [Book, Ch. X, p. Y]
```

## Status

🚧 Early development — see [`docs/`](docs/) for phase-by-phase progress and design decisions.

## Stack

- **Language:** Python (no RAG frameworks — built from first principles)
- **LLM:** [Ollama](https://ollama.com/) (local)
- **Embeddings:** sentence-transformers (multilingual)
- **Vector store:** FAISS
- **OCR:** Tesseract (via pytesseract)
- **PDF parsing:** PyMuPDF, pdfplumber

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

PDF source files are not committed to this repo (copyright). Drop your own chapter PDFs into `data/raw/` to run the pipeline.
