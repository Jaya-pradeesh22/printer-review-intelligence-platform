POSITIVE_WORDS = [
    "good",
    "excellent",
    "fast",
    "smooth",
    "great",
    "easy",
    "passed",
    "amazing",
    "best",
    "perfect",
    "love",
    "awesome",
    "value for money",
    "quality",
    "recommend"
]

NEGATIVE_WORDS = [
    "failed",
    "slow",
    "bad",
    "issue",
    "problem",
    "disconnect",
    "poor",
    "damage",
    "damaged",
    "stuck",
    "jam",
    "blurry",
    "unclear",
    "disappointed",
    "misleading",
    "error",
    "not good",
    "difficult"
]

def detect_sentiment(review_text):
    review_text = review_text.lower()

    positive_score = 0
    negative_score = 0

    for word in POSITIVE_WORDS:
        if word in review_text:
            positive_score += 1

    for word in NEGATIVE_WORDS:
        if word in review_text:
            negative_score += 1

    if positive_score > negative_score:
        return "POSITIVE"
    elif negative_score > positive_score:
        return "NEGATIVE"
    else:
        return "NEUTRAL"