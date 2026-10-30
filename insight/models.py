from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Branch(models.Model):
    """A branch of the commercial establishment that collects customer feedback."""

    name = models.CharField(max_length=100, unique=True)
    city = models.CharField(max_length=100)
    manager = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name_plural = "Branches"
        ordering = ["id"]

    def __str__(self):
        return self.name


class Survey(models.Model):
    """A customer-satisfaction survey run during a given period."""

    title = models.CharField(max_length=200)
    period = models.CharField(max_length=50, help_text="For example: October 2026")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.title} ({self.period})"


class Response(models.Model):
    """One customer's answer to a survey at a specific branch."""

    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="responses")
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="responses")
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Overall satisfaction from 1 (very bad) to 5 (excellent).",
    )
    recommend_score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="How likely the customer is to recommend us, from 0 to 10 (used for NPS).",
    )
    comment = models.TextField(blank=True)
    submitted_at = models.DateTimeField()

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.branch} - {self.rating}/5"
