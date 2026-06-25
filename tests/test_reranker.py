from src.retrieval.reranker import _sorted_by_score


def test_sorts_descending_by_score():
    candidates = [{"text": "a"}, {"text": "b"}, {"text": "c"}]
    scores = [0.1, 0.9, 0.5]

    result = _sorted_by_score(candidates, scores)

    assert [c["text"] for c in result] == ["b", "c", "a"]


def test_attaches_rerank_score_without_mutating_input():
    candidates = [{"text": "a", "score": 0.7}]
    scores = [0.3]

    result = _sorted_by_score(candidates, scores)

    assert result[0]["rerank_score"] == 0.3
    assert result[0]["score"] == 0.7  # original FAISS score preserved
    assert "rerank_score" not in candidates[0]  # input untouched
