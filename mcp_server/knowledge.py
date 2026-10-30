"""Reference knowledge shared by the MCP tools and exposed as MCP resources.

Keeping it in one place guarantees that what a client *reads* (resources)
is exactly what the tools *use* in their calculations.
"""

# Score thresholds used to label results (rating, NPS).
BENCHMARKS = {
    "satisfaction_pct": [
        {"level": "Excellent", "min": 85},
        {"level": "Good", "min": 70},
        {"level": "Needs improvement", "min": 50},
        {"level": "Critical", "min": 0},
    ],
    "nps": [
        {"level": "Excellent", "min": 50},
        {"level": "Good", "min": 20},
        {"level": "Needs improvement", "min": 0},
        {"level": "Critical", "min": -100},
    ],
    "definitions": {
        "satisfaction_pct": "Share of responses rated 4 or 5 out of 5.",
        "nps": "Net Promoter Score = % promoters (9-10) minus % detractors (0-6).",
        "promoter": "recommend_score 9-10",
        "passive": "recommend_score 7-8",
        "detractor": "recommend_score 0-6",
        "complaint": "A comment attached to a response rated 1-3.",
    },
}

# Complaint topics: keywords to detect in comments and the suggested action.
COMPLAINT_TOPICS = {
    "waiting time": {
        "keywords": ["wait", "waiting", "slow", "queue", "line", "late"],
        "action": "Add staff during peak hours and open an extra cashier to cut waiting time.",
    },
    "staff behaviour": {
        "keywords": ["rude", "staff", "unfriendly", "employee", "attitude", "ignored"],
        "action": "Run a short customer-service training and review staff scheduling.",
    },
    "prices": {
        "keywords": ["price", "expensive", "overpriced", "cost"],
        "action": "Review pricing against competitors and promote loyalty offers.",
    },
    "cleanliness": {
        "keywords": ["dirty", "clean", "cleanliness", "messy", "smell"],
        "action": "Introduce an hourly cleaning checklist with a named owner per shift.",
    },
    "product availability": {
        "keywords": ["out of stock", "unavailable", "missing", "stock", "shortage"],
        "action": "Improve stock forecasting and restock best-sellers before peak days.",
    },
    "parking": {
        "keywords": ["parking", "park"],
        "action": "Coordinate extra parking or valet service at busy times.",
    },
}


def level_for(metric: str, value: float) -> str:
    """Return the benchmark level label for a metric value."""
    for band in BENCHMARKS[metric]:
        if value >= band["min"]:
            return band["level"]
    return BENCHMARKS[metric][-1]["level"]
