import requests
import json

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "phi3"


def is_ollama_running() -> bool:
    """Quick health check before attempting any classification."""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


def classify_sentiment(review_text: str, model: str = DEFAULT_MODEL) -> str:
    """
    Ask the local Ollama LLM to classify a review as POSITIVE, NEGATIVE, or NEUTRAL.
    Returns one of those three strings, or None if Ollama is unavailable or fails.
    The caller decides the fallback - this function never crashes the pipeline.
    """
    prompt = (
        "You are a product review sentiment classifier. "
        "Read the following customer review and respond with EXACTLY one word: "
        "POSITIVE, NEGATIVE, or NEUTRAL. "
        "No explanation. No punctuation. Just the single word.\n\n"
        f"Review: {review_text.strip()}"
    )

    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.0,   # deterministic - consistent labels
                    "num_predict": 5,     # only need one word, cap token output
                },
            },
            timeout=30,
        )

        if response.status_code != 200:
            return None

        raw = response.json().get("response", "").strip().upper()

        # Guard against the model being verbose despite instructions
        for label in ["POSITIVE", "NEGATIVE", "NEUTRAL"]:
            if label in raw:
                return label

        return None  # model gave something unexpected - caller will fall back

    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        return None
    except (json.JSONDecodeError, KeyError):
        return None
