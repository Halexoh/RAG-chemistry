"""End-to-end RAG: retrieve, build a grounded prompt, generate a cited answer."""

from src.generation.generate import generate_answer
from src.generation.prompt import SYSTEM_PROMPT, build_user_prompt
from src.retrieval.retrieve import retrieve

NO_CONTEXT_ANSWER = "No encontré información relevante en los libros indexados para responder esta pregunta."


def answer_question(query: str, top_k: int = 5, fetch_k: int = 20) -> dict:
    chunks = retrieve(query, top_k=top_k, fetch_k=fetch_k)
    if not chunks:
        return {"query": query, "answer": NO_CONTEXT_ANSWER, "sources": []}

    user_prompt = build_user_prompt(query, chunks)
    answer = generate_answer(SYSTEM_PROMPT, user_prompt)
    return {"query": query, "answer": answer, "sources": chunks}
