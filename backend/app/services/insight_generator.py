def generate_insights(highlights: list[dict]) -> str:
    """
    Takes the scraped 'Customers say' highlights
    (model_name, category, mention_count, trend)
    and produces a QA report using simple rule-based logic.

    No external API needed - fully free, runs locally.
    """

    if not highlights:
        return "No highlight data available to analyze."

    down_items = [h for h in highlights if h.get("trend") == "DOWN"]
    up_items = [h for h in highlights if h.get("trend") == "UP"]
    neutral_items = [h for h in highlights if h.get("trend") == "NEUTRAL"]

    # Priority issues: DOWN trend, ranked by mention_count (highest first)
    down_items = sorted(
        down_items,
        key=lambda h: h.get("mention_count", 0),
        reverse=True
    )

    # Strengths: UP trend, ranked by mention_count (highest first)
    up_items = sorted(
        up_items,
        key=lambda h: h.get("mention_count", 0),
        reverse=True
    )

    lines = []

    lines.append("QA REPORT")
    lines.append("=" * 40)

    if down_items:
        lines.append("\nPRIORITY ISSUES (declining trend, act on these first):")
        for i, item in enumerate(down_items[:3], start=1):
            lines.append(
                f"{i}. {item['category']} ({item['model_name']}) - "
                f"{item['mention_count']} mentions, trending down. "
                f"Recommendation: investigate root cause of "
                f"'{item['category'].lower()}' complaints and prioritize "
                f"a fix given the mention volume."
            )
    else:
        lines.append("\nNo declining categories found - nothing urgent.")

    if up_items:
        lines.append("\nSTRENGTHS (keep doing this):")
        for i, item in enumerate(up_items[:3], start=1):
            lines.append(
                f"{i}. {item['category']} ({item['model_name']}) - "
                f"{item['mention_count']} mentions, trending up."
            )

    if neutral_items:
        lines.append("\nWATCH LIST (mixed/stable, monitor for changes):")
        for item in neutral_items:
            lines.append(
                f"- {item['category']} ({item['model_name']}) - "
                f"{item['mention_count']} mentions."
            )

    return "\n".join(lines)