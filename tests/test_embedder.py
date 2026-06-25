from src.embeddings.embedder import add_passage_prefix, add_query_prefix


def test_passage_prefix_applied_to_every_text():
    texts = ["agua", "óxido de hierro"]
    assert add_passage_prefix(texts) == ["passage: agua", "passage: óxido de hierro"]


def test_query_prefix_uses_query_not_passage():
    assert add_query_prefix("¿qué es la corrosión?") == "query: ¿qué es la corrosión?"
