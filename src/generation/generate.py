"""Calls the local Ollama model to produce the final answer text."""

import ollama

MODEL_NAME = "qwen2.5:7b-instruct"


def generate_answer(system_prompt: str, user_prompt: str) -> str:
    response = ollama.chat(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response["message"]["content"]
