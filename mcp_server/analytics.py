"""Pure calculation functions used by the MCP tools.

They receive plain Python lists/dicts (no database access), which makes
them easy to test and to reuse.
"""

from collections import Counter

from .knowledge import COMPLAINT_TOPICS, level_for


def satisfaction(ratings: list[int]) -> dict:
    """Average rating and % of satisfied customers (rating 4-5)."""
    total = len(ratings)
    if total == 0:
        return {"responses": 0, "avg_rating": None, "satisfaction_pct": None, "level": "No data"}
    satisfied = sum(1 for r in ratings if r >= 4)
    pct = round(satisfied / total * 100, 1)
    return {
        "responses": total,
        "avg_rating": round(sum(ratings) / total, 2),
        "satisfaction_pct": pct,
        "level": level_for("satisfaction_pct", pct),
    }


def nps(recommend_scores: list[int]) -> dict:
    """Net Promoter Score from 0-10 'would you recommend us' answers."""
    total = len(recommend_scores)
    if total == 0:
        return {"responses": 0, "nps": None, "level": "No data"}
    promoters = sum(1 for s in recommend_scores if s >= 9)
    detractors = sum(1 for s in recommend_scores if s <= 6)
    passives = total - promoters - detractors
    score = round((promoters - detractors) / total * 100, 1)
    return {
        "responses": total,
        "promoters": promoters,
        "passives": passives,
        "detractors": detractors,
        "nps": score,
        "level": level_for("nps", score),
    }


def complaint_topics(comments: list[str], limit: int = 5) -> dict:
    """Count which complaint topics appear in negative comments."""
    counter = Counter()
    for comment in comments:
        text = comment.lower()
        for topic, info in COMPLAINT_TOPICS.items():
            if any(keyword in text for keyword in info["keywords"]):
                counter[topic] += 1
    top = [
        {"topic": topic, "mentions": count, "suggested_action": COMPLAINT_TOPICS[topic]["action"]}
        for topic, count in counter.most_common(limit)
    ]
    return {"negative_comments": len(comments), "top_complaints": top}
