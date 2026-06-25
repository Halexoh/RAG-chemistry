"""Sets process-wide environment fixes before anything under src/ can import
faiss or torch — whichever happens first, the wrong combination crashes.

Found while running the full evaluation on the expanded (11-book) corpus:
faiss-cpu and PyTorch (via sentence-transformers) each bundle their own
OpenMP runtime, and on macOS, importing faiss before torch in the same
process — exactly what src/indexing/search.py does (FAISS index load,
then embed_query) — segfaults the moment torch's runtime initializes.
Reproduced reliably with a minimal repro outside this codebase, not a
one-off. Setting both variables together (one alone wasn't enough) makes
the two runtimes coexist regardless of import order.
"""

import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
