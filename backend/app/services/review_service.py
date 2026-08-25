import json
from pathlib import Path

from app.services.sentiment_analyzer import detect_sentiment
from app.services.issue_classifier import detect_issue_categories

def get_reviews():

    file_path = (
        Path(__file__).resolve().parents[3]
        / "scraper"
        / "data"
        / "hp_reviews.json"
    )

    with open(file_path, "r", encoding="utf-8") as file:
        reviews = json.load(file)

    return reviews

def get_analyzed_reviews():

    file_path = (
        Path(__file__).resolve().parents[3]
        / "scraper"
        / "data"
        / "hp_reviews.json"
    )

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as file:

        reviews = json.load(file)

    analyzed_reviews = []

    for review in reviews:

        review_text = review["review"]

        analyzed_reviews.append({
            "product": review["product"],
            "review": review_text,
            "source": review["source"],
            "sentiment": detect_sentiment(review_text),
            "issues": detect_issue_categories(review_text)
        })

    return analyzed_reviews