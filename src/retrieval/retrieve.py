"""Two-stage retrieval: FAISS for recall, cross-encoder for precision.

Stage 1 (fast, broad): FAISS returns the top `fetch_k` candidates by
embedding similarity across the whole corpus.
Stage 2 (slow, precise): the cross-encoder rescoring only those
`fetch_k` candidates, returning the best `top_k`.

`fetch_k` should comfortably exceed `top_k` — the entire point of this
two-stage design is giving the reranker a wider net to pick the true
best answers out of, including ones a bi-encoder might have under-ranked.
"""

from src.indexing.search import search as faiss_search
from src.retrieval.reranker import rerank


def retrieve(query: str, top_k: int = 5, fetch_k: int = 20) -> list[dict]:
    candidates = faiss_search(query, k=fetch_k)
    return rerank(query, candidates, top_k=top_k)
