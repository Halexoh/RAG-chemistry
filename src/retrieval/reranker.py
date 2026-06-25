"""Reranks FAISS candidates with a cross-encoder for precision FAISS can't give.

The embedding model (phase 3) is a *bi-encoder*: it encodes the query and
each passage separately, with no interaction between them, which is
exactly what makes FAISS's exhaustive comparison fast — every passage
vector is precomputed once, independent of any future query. The cost
is that the model never lets the query and passage inform each other, so
a passage can score deceptively high on shared vocabulary alone (the
bibliography-noise problem from phases 3-4).

A *cross-encoder* feeds the (query, passage) pair through the same
transformer together, so it can actually reason about whether the
passage answers the query — much more accurate, but it can't be
precomputed: it has to run once per candidate, per query. That's why
it's only applied to FAISS's top-k candidates (phase 4's job: get a
short, decent list fast), not the whole corpus.

Model: BAAI/bge-reranker-base — multilingual, matching the embedding
model's bilingual ES/EN requirement.

Forced onto CPU for the same reason as embedder.py: this model's MPS
(Apple GPU) usage can deadlock against Ollama's own GPU usage during
generation, on a memory-constrained machine running both at once.
"""

from sentence_transformers import CrossEncoder

MODEL_NAME = "BAAI/bge-reranker-base"

_model: CrossEncoder | None = None


def get_model() -> CrossEncoder:
    global _model
    if _model is None:
        _model = CrossEncoder(MODEL_NAME, device="cpu")
    return _model


def _sorted_by_score(candidates: list[dict], scores) -> list[dict]:
    """Pure pairing/sorting step, kept separate from model inference so it's testable
    without loading a ~1 GB model."""
    reranked = []
    for candidate, score in zip(candidates, scores):
        item = dict(candidate)
        item["rerank_score"] = float(score)
        reranked.append(item)
    reranked.sort(key=lambda c: c["rerank_score"], reverse=True)
    return reranked


def rerank(query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
    if not candidates:
        return []
    model = get_model()
    pairs = [(query, c["text"]) for c in candidates]
    scores = model.predict(pairs)
    return _sorted_by_score(candidates, scores)[:top_k]
