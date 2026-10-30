"""Create demo (fictional) branches, surveys and customer responses.

Usage:  python manage.py seed_demo
The data is random but reproducible (fixed seed), so results are the same
on every computer.
"""

import random
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from insight.models import Branch, Response, Survey

BRANCHES = [
    # name, city, manager, quality profile (higher = happier customers), main issues
    ("Al-Aziziyah Branch", "Madinah", "Sara Alharbi", 0.82, ["waiting time", "parking"]),
    ("Quba Branch", "Madinah", "Faisal Alotaibi", 0.62, ["staff behaviour", "waiting time"]),
    ("King Fahd Branch", "Madinah", "Noura Aljuhani", 0.45, ["cleanliness", "product availability"]),
    ("Al-Khalidiyah Branch", "Madinah", "Khalid Alamri", 0.72, ["prices"]),
]

SURVEYS = [
    ("Customer Satisfaction Survey", "September 2026", datetime(2026, 9, 1)),
    ("Customer Satisfaction Survey", "October 2026", datetime(2026, 10, 1)),
]

NEGATIVE = {
    "waiting time": ["The waiting time at the cashier was too long.", "Very slow service, long queue.",
                     "I had to wait almost 20 minutes."],
    "staff behaviour": ["The staff were rude and unfriendly.", "An employee ignored me when I asked for help.",
                        "Staff attitude needs improvement."],
    "prices": ["Prices are too expensive compared to other stores.", "Everything feels overpriced lately."],
    "cleanliness": ["The store was dirty and messy.", "Bad smell near the entrance, cleanliness is poor."],
    "product availability": ["The product I wanted was out of stock.", "Many items were unavailable again."],
    "parking": ["Hard to find parking.", "No parking space at all in the evening."],
}
NEUTRAL = ["It was okay.", "Average experience.", "Nothing special.", ""]
POSITIVE = ["Great service, thank you!", "Friendly staff and quick checkout.", "Clean store and good offers.",
            "Excellent experience as always.", ""]


class Command(BaseCommand):
    help = "Delete existing survey data and create reproducible demo data."

    @transaction.atomic
    def handle(self, *args, **options):
        rng = random.Random(2026)
        Response.objects.all().delete()
        Survey.objects.all().delete()
        Branch.objects.all().delete()

        branches = [
            (Branch.objects.create(name=n, city=c, manager=m), q, issues)
            for n, c, m, q, issues in BRANCHES
        ]
        surveys = [(Survey.objects.create(title=t, period=p), start) for t, p, start in SURVEYS]

        total = 0
        for s_index, (survey, start) in enumerate(surveys):
            for branch, quality, issues in branches:
                # Branches improve a little in the second survey.
                q = min(0.95, quality + 0.05 * s_index)
                for _ in range(rng.randint(45, 70)):
                    happy = rng.random() < q
                    if happy:
                        rating = rng.choice([4, 4, 5, 5, 5])
                        recommend = rng.choice([8, 9, 9, 10, 10])
                        comment = rng.choice(POSITIVE)
                    else:
                        rating = rng.choice([1, 2, 2, 3, 3])
                        recommend = rng.choice([0, 2, 4, 5, 6, 6, 7])
                        if rating <= 3 and rng.random() < 0.85:
                            topic = rng.choice(issues) if rng.random() < 0.8 else rng.choice(list(NEGATIVE))
                            comment = rng.choice(NEGATIVE[topic])
                        else:
                            comment = rng.choice(NEUTRAL)
                    submitted = timezone.make_aware(start + timedelta(days=rng.randint(0, 27),
                                                                      minutes=rng.randint(0, 1439)))
                    Response.objects.create(survey=survey, branch=branch, rating=rating,
                                            recommend_score=recommend, comment=comment,
                                            submitted_at=submitted)
                    total += 1

        self.stdout.write(self.style.SUCCESS(
            f"Demo data created: {len(branches)} branches, {len(surveys)} surveys, {total} responses."
        ))
