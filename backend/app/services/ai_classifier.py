from sentence_transformers import SentenceTransformer, util  # type: ignore
from app.services.ollama_client import classify_sentiment, is_ollama_running

# ── Category definitions ──────────────────────────────────────────────────────

CATEGORIES = {
    "Connectivity":    ["wifi", "wireless", "connect", "network", "bluetooth", "offline", "router"],
    "Print Quality":   ["print", "color", "blur", "sharp", "faded", "quality", "ink", "resolution"],
    "Reliability":     ["jam", "stuck", "crash", "freeze", "error", "broken", "stop", "fail"],
    "Setup & Install": ["setup", "install", "driver", "configure", "easy", "difficult", "guide"],
    "App & Software":  ["app", "software", "update", "firmware", "interface", "mobile", "phone"],
    "Ink & Cost":      ["ink", "cartridge", "expensive", "refill", "cost", "price", "toner"],
    "Speed":           ["slow", "fast", "speed", "quick", "delay", "time", "minutes"],
    "Support":         ["support", "customer service", "help", "warranty", "response", "replace"],
}

# ── Sentiment thresholds ──────────────────────────────────────────────────────
# Reviews in the AMBIGUOUS range get sent to Ollama for proper text-based
# classification instead of just rubber-stamping the star rating.
POSITIVE_MIN = 4          # 4-5 stars -> heuristic POSITIVE
NEGATIVE_MAX = 2          # 1-2 stars -> heuristic NEGATIVE
# 3 stars (the ambiguous middle) -> Ollama

_ollama_available = None  # cached after first check so we don't ping every review


def _check_ollama() -> bool:
    global _ollama_available
    if _ollama_available is None:
        _ollama_available = is_ollama_running()
        if not _ollama_available:
            print("[ai_classifier] Ollama not running - falling back to rating heuristic for all reviews.")
    return _ollama_available


def _heuristic_sentiment(rating: int) -> tuple:
    """Returns (sentiment_label, sentiment_source) from star rating alone."""
    if rating >= POSITIVE_MIN:
        return "POSITIVE", "rating_heuristic"
    elif rating <= NEGATIVE_MAX:
        return "NEGATIVE", "rating_heuristic"
    else:
        return "NEUTRAL", "rating_heuristic"


def _is_ambiguous(rating: int) -> bool:
    """True for 3-star reviews - the genuinely ambiguous middle ground."""
    return rating == 3


# ── Model (loaded once, reused across all calls) ──────────────────────────────

_model = None
_category_embeddings = None  # computed once, reused for every review


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _model


def _get_category_embeddings():
    global _category_embeddings
    if _category_embeddings is None:
        model = _get_model()
        _category_embeddings = {
            category: model.encode(" ".join(keywords), convert_to_tensor=True)
            for category, keywords in CATEGORIES.items()
        }
    return _category_embeddings


# ── Public API ────────────────────────────────────────────────────────────────

def classify_review(review_text: str, rating: int) -> dict:
    """
    Classifies a single review into a category and assigns sentiment.

    Returns:
        {
            "category":         str,   # one of CATEGORIES keys, or "General"
            "sentiment":        str,   # POSITIVE | NEGATIVE | NEUTRAL
            "sentiment_source": str,   # "rating_heuristic" | "ollama"
        }
    """
        # ── 1. Category via embedding similarity ──────────────────────────────────
    model = _get_model()
    category_embeddings = _get_category_embeddings()
    review_embedding = model.encode(review_text, convert_to_tensor=True)

    best_category = "Others / Unclear"
    best_score = -1.0

    for category, keyword_embedding in category_embeddings.items():
        score = float(util.cos_sim(review_embedding, keyword_embedding))
        if score > best_score:
            best_score = score
            best_category = category

    # Below this, nothing was a genuine match - either a generic/no-issue
    # review, or text too short/garbled to classify with confidence.
    CONFIDENCE_THRESHOLD = 0.35  # starting point - tune against your labeled examples
    if best_score < CONFIDENCE_THRESHOLD:
        word_count = len(review_text.strip().split())
        if word_count <= 2:
            best_category = "Others / Unclear"
        elif rating is not None and (rating >= POSITIVE_MIN or rating <= NEGATIVE_MAX):
            best_category = "General / No Issue"
        else:
            best_category = "Others / Unclear"

    # ── 2. Sentiment ──────────────────────────────────────────────────────────
    if rating is not None and not _is_ambiguous(rating):
        # Clear positive or negative rating - trust it, skip the LLM entirely
        sentiment, sentiment_source = _heuristic_sentiment(rating)
    elif _check_ollama():
        # Ambiguous rating (3 stars) or missing rating - ask Ollama to actually read it
        ollama_result = classify_sentiment(review_text)
        if ollama_result:
            sentiment = ollama_result
            sentiment_source = "ollama"
        else:
            # Ollama responded but gave unexpected output - fall back safely
            sentiment, sentiment_source = _heuristic_sentiment(rating or 3)
    else:
        # Ollama not running - fall back to heuristic, nothing crashes
        sentiment, sentiment_source = _heuristic_sentiment(rating or 3)

    return {
        "category": best_category,
        "sentiment": sentiment,
        "sentiment_source": sentiment_source,
    }
