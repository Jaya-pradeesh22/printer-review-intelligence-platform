from app.services.review_service import get_analyzed_reviews

def get_dashboard_summary():
    reviews = get_analyzed_reviews()
    total_reviews = len(reviews)

    positive =0
    negative =0
    neutral =0

    issue_counts ={}
    for review in reviews:

        sentiment = review["sentiment"]

        if sentiment == "POSITIVE":
            positive += 1

        elif sentiment == "NEGATIVE":
            negative += 1

        else:
            neutral += 1

        for issue in review["issues"]:

            issue_counts[issue] = (
                issue_counts.get(issue, 0) + 1
            )

    return {
        "total_reviews": total_reviews,
        "positive_reviews": positive,
        "negative_reviews": negative,
        "neutral_reviews": neutral,
        "issue_distribution": issue_counts
    }