import json
import requests
from collections import defaultdict

from ai_classifier import classify_review

# ==========================================
# CONFIG
# ==========================================
AMAZON_REVIEWS_PATH = "data/amazon_reviews.json"
BACKEND_BASE_URL = "http://127.0.0.1:8000"

HIGHLIGHTS_GET_URL = f"{BACKEND_BASE_URL}/highlights"
HIGHLIGHTS_POST_URL = f"{BACKEND_BASE_URL}/highlights"
RAW_REVIEWS_POST_URL = f"{BACKEND_BASE_URL}/raw-reviews"


def load_reviews(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def classify_all_reviews(reviews):
    """
    Same logic as the HP pipeline: category via embedding similarity,
    sentiment via rating heuristic for clear ratings, Ollama for
    ambiguous (3-star) ones. See ai_classifier.py.
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
    counts = defaultdict(int)
    for review in reviews:
        key = (review["model_name"], review["category"])
        counts[key] += 1
    return counts


def fetch_all_amazon_highlights():
    """
    Same client-side filtering approach as the HP script - GET
    /highlights returns every (model_name, category) pair's latest
    row globally, so we fetch once and filter for source == "Amazon".
    """
    try:
        response = requests.get(HIGHLIGHTS_GET_URL, timeout=10)
        response.raise_for_status()
        rows = response.json()
    except Exception as e:
        print(f"  Could not fetch existing highlights: {e}")
        return []

    return [row for row in rows if row.get("source") == "Amazon"]


def fetch_previous_amazon_counts(model_name, all_amazon_rows):
    return {
        row["category"]: row.get("mention_count", 0)
        for row in all_amazon_rows
        if row.get("model_name") == model_name
    }


def compute_trend(previous_count, current_count):
    if previous_count is None:
        return "NEUTRAL"
    if current_count > previous_count:
        return "UP"
    elif current_count < previous_count:
        return "DOWN"
    else:
        return "NEUTRAL"


def post_highlights_batch(highlight_rows):
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
    Posts all classified Amazon raw reviews in one batch call to the
    unified /raw-reviews endpoint - same table HP reviews land in,
    distinguished by source == "Amazon".
    """
    if not reviews:
        print("  No raw reviews to post.")
        return

    payload = [
        {
            "source": "Amazon",
            "review_id": review["review_id"],
            "model_name": review["model_name"],
            "rating_value": review.get("rating_value"),
            "review_body": review.get("review_body") or "",
            "reviewer_response": review.get("seller_response"),
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
        print(f"  Failed to post raw reviews batch: {e}")
        try:
            print(f"  Server said: {response.json()}")
        except Exception:
            print(f"  Server said (raw): {response.text}")
    except Exception as e:
        print(f"  Failed to post raw reviews batch: {e}")


def main():
    print("Loading scraped Amazon reviews...")
    reviews = load_reviews(AMAZON_REVIEWS_PATH)
    print(f"Loaded {len(reviews)} reviews.\n")

    print("Classifying reviews (category + sentiment)...")
    reviews = classify_all_reviews(reviews)

    print("\nAggregating counts per model + category...")
    counts = aggregate_by_model_and_category(reviews)
    for (model_name, category), count in counts.items():
        print(f"  {model_name} / {category}: {count}")

    print("\nComputing trend and building highlight rows...")
    all_amazon_rows = fetch_all_amazon_highlights()

    highlight_rows = []
    models = {model_name for (model_name, _) in counts.keys()}
    for model_name in models:
        previous_counts = fetch_previous_amazon_counts(model_name, all_amazon_rows)

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
                "source": "Amazon"
            })
            print(f"  {model_name} / {category}: {current_count} "
                  f"(was {previous_count}) -> {trend}")

    print("\nPosting highlights batch...")
    post_highlights_batch(highlight_rows)

    print("\nPosting raw reviews for traceability...")
    post_raw_reviews_batch(reviews)

    print("\n✅ Done. Amazon reviews classified, aggregated, and posted.")


if __name__ == "__main__":
    main()
