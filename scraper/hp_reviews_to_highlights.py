import json
import requests
from collections import defaultdict
from datetime import datetime, timezone

from ai_classifier import classify_review

# ==========================================
# CONFIG
# ==========================================
HP_REVIEWS_PATH = "data/hp_reviews.json"
BACKEND_BASE_URL = "http://127.0.0.1:8000"  # adjust if your backend runs elsewhere

HIGHLIGHTS_GET_URL = f"{BACKEND_BASE_URL}/highlights"
HIGHLIGHTS_POST_URL = f"{BACKEND_BASE_URL}/highlights"
RAW_REVIEWS_POST_URL = f"{BACKEND_BASE_URL}/raw-reviews"  # unified endpoint (Amazon + HP) -
# named /raw-reviews, not /reviews, since main.py already defines POST /reviews
# for the older single-review Review/ReviewCreate system.


def load_reviews(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def classify_all_reviews(reviews):
    """
    Runs each review through ai_classifier.classify_review() once,
    attaching:
      - category: the QA bucket (Connectivity, Print Performance, etc.)
      - sentiment: POSITIVE/NEGATIVE/NEUTRAL for that review
      - sentiment_source: "rating_heuristic" or "ollama", depending on
        which path decided the sentiment (see ai_classifier.py)
    Mutates and returns the same list with these fields added.
    """
    for review in reviews:
        result = classify_review(
            review_text=review.get("review_body", ""),
            rating=review.get("rating_value"),
        )
        review["category"] = result["category"]
        review["sentiment"] = result["sentiment"]
        review["sentiment_source"] = result["sentiment_source"]

        print(
            f"  [{review['review_id']}] -> {review['category']} "
            f"({review['sentiment']} via {review['sentiment_source']})"
        )
    return reviews


def aggregate_by_model_and_category(reviews):
    """
    Groups classified reviews into per (model_name, category) counts -
    this becomes each row's mention_count, matching the shape your
    Amazon highlights already use.
    """
    counts = defaultdict(int)
    for review in reviews:
        key = (review["model_name"], review["category"])
        counts[key] += 1
    return counts


def fetch_all_hp_highlights():
    """
    GET /highlights returns EVERY (model_name, category) pair's most
    recent row, globally - it does not support filtering by query
    params. So we fetch everything once and filter client-side for
    source == "HP.com" ourselves.
    """
    try:
        response = requests.get(HIGHLIGHTS_GET_URL, timeout=10)
        response.raise_for_status()
        rows = response.json()
    except Exception as e:
        print(f"  Could not fetch existing highlights: {e}")
        return []

    return [row for row in rows if row.get("source") == "HP.com"]


def fetch_previous_hp_counts(model_name, all_hp_rows):
    """
    Filters the already-fetched HP.com rows down to this model, and
    returns mention_count per category. Since GET /highlights already
    returns only the latest row per (model_name, category) - not raw
    history - this IS already "the previous run's count" as long as
    we call it BEFORE posting this run's new data (which main() does).
    """
    return {
        row["category"]: row.get("mention_count", 0)
        for row in all_hp_rows
        if row.get("model_name") == model_name
    }


def compute_trend(previous_count, current_count):
    """
    Mirrors the meaning of Amazon's trend: is this category getting
    mentioned MORE (worsening signal, if it's a problem category) or
    LESS over time. No previous run yet -> NEUTRAL (baseline run).
    """
    if previous_count is None:
        return "NEUTRAL"
    if current_count > previous_count:
        return "UP"
    elif current_count < previous_count:
        return "DOWN"
    else:
        return "NEUTRAL"


def post_highlights_batch(highlight_rows):
    """
    POST /highlights expects a LIST (bulk insert), not one row per
    call - matches the backend's List[HighlightCreate] signature.
    """
    if not highlight_rows:
        print("  No highlight rows to post.")
        return

    try:
        response = requests.post(
            HIGHLIGHTS_POST_URL, json=highlight_rows, timeout=15
        )
        response.raise_for_status()
        result = response.json()
        print(f"  {result.get('message', 'Posted.')} "
              f"(count: {result.get('count', len(highlight_rows))})")
    except Exception as e:
        print(f"  Failed to post highlights batch: {e}")


def post_raw_reviews_batch(reviews):
    """
    Posts all classified raw reviews in ONE batch call to the unified
    /reviews endpoint, matching its List[RawReviewCreate] signature.
    Dedup on (source, review_id) is handled server-side, so re-running
    this script on the same scrape data is safe.
    """
    if not reviews:
        print("  No raw reviews to post.")
        return

    payload = [
        {
            "source": "HP.com",
            "review_id": review["review_id"],
            "model_name": review["model_name"],
            "rating_value": review.get("rating_value"),
            # .get(key, "") only falls back to "" if the key is MISSING -
            # if review_body is present but null in the scraped JSON, this
            # `or ""` catches that too, since RawReviewCreate requires a str.
            "review_body": review.get("review_body") or "",
            "reviewer_response": review.get("hp_response"),
            "category": review.get("category"),
            "sentiment": review.get("sentiment"),
            "sentiment_source": review.get("sentiment_source"),
        }
        for review in reviews
    ]

    try:
        response = requests.post(RAW_REVIEWS_POST_URL, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        print(
            f"  {result.get('message', 'Posted.')} "
            f"(received: {result.get('received')}, "
            f"inserted: {result.get('inserted')}, "
            f"skipped duplicates: {result.get('skipped_duplicates')})"
        )
    except requests.exceptions.HTTPError as e:
        # Print FastAPI's actual validation detail, not just "422 error" -
        # this tells us exactly which field on which row is the problem.
        print(f"  Failed to post raw reviews batch: {e}")
        try:
            print(f"  Server said: {response.json()}")
        except Exception:
            print(f"  Server said (raw): {response.text}")
    except Exception as e:
        print(f"  Failed to post raw reviews batch: {e}")


def main():
    print("Loading scraped HP reviews...")
    reviews = load_reviews(HP_REVIEWS_PATH)
    print(f"Loaded {len(reviews)} reviews.\n")

    print("Classifying reviews (category + sentiment)...")
    reviews = classify_all_reviews(reviews)

    print("\nAggregating counts per model + category...")
    counts = aggregate_by_model_and_category(reviews)
    for (model_name, category), count in counts.items():
        print(f"  {model_name} / {category}: {count}")

    print("\nComputing trend and building highlight rows...")
    all_hp_rows = fetch_all_hp_highlights()

    highlight_rows = []
    models = {model_name for (model_name, _) in counts.keys()}
    for model_name in models:
        previous_counts = fetch_previous_hp_counts(model_name, all_hp_rows)

        for (m_name, category), current_count in counts.items():
            if m_name != model_name:
                continue
            previous_count = previous_counts.get(category)
            trend = compute_trend(previous_count, current_count)
            highlight_rows.append({
                "model_name": model_name,
                "category": category,
                "mention_count": current_count,
                "trend": trend,
                "source": "HP.com"
            })
            print(f"  {model_name} / {category}: {current_count} "
                  f"(was {previous_count}) -> {trend}")

    print("\nPosting highlights batch...")
    post_highlights_batch(highlight_rows)

    print("\nPosting raw reviews for traceability...")
    post_raw_reviews_batch(reviews)

    print("\n✅ Done. HP reviews classified, aggregated, and posted.")


if __name__ == "__main__":
    main()

# ==========================================
# BACKEND NOTE
# ==========================================
# 1. POST /highlights expects a LIST (bulk insert) - unchanged.
# 2. GET /highlights takes NO query params - unchanged. Fetches
#    everything, filters for source == "HP.com" client-side.
# 3. POST /reviews (unified raw_reviews table, replaces the old
#    /hp-reviews endpoint) - expects a LIST, dedups server-side on
#    (source, review_id). Every row now also carries category,
#    sentiment, and sentiment_source, since ai_classifier.py computes
#    all three in a single classify_review() call now.