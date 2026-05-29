# templates_engine/llm.py
# Phase I: Ollama client (OpenAI-compatible chat endpoint).


def preflight(model):
    raise NotImplementedError


def generate(messages, model, temperature=0.3):
    raise NotImplementedError
