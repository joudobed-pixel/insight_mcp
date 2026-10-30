"""Insight MCP server.

Exposes the three MCP building blocks:
  * TOOLS     - executable analysis operations (satisfaction, NPS, ...)
  * RESOURCES - read-only reference data (branches, surveys, benchmarks)
  * PROMPTS   - reusable report / recommendation templates

Django starts this file automatically as a subprocess (stdio transport);
you do not need to run it yourself.
"""

import json
import os
import sys
from pathlib import Path

# Make the project folder importable and load Django so the tools can use the ORM.
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from asgiref.sync import sync_to_async  # noqa: E402
from mcp.server.fastmcp import FastMCP  # noqa: E402

from insight.models import Branch, Response, Survey  # noqa: E402
from mcp_server import analytics  # noqa: E402
from mcp_server.knowledge import BENCHMARKS, COMPLAINT_TOPICS  # noqa: E402

mcp = FastMCP("Insight Survey Analytics", log_level="WARNING")


# ---------------------------------------------------------------------------
# Database helpers (synchronous Django ORM, wrapped with sync_to_async below)
# ---------------------------------------------------------------------------
def _responses(branch_id=None, survey_id=None):
    qs = Response.objects.all()
    if branch_id is not None:
        qs = qs.filter(branch_id=branch_id)
    if survey_id is not None:
        qs = qs.filter(survey_id=survey_id)
    return qs


def _branch_name(branch_id):
    branch = Branch.objects.filter(pk=branch_id).first()
    if branch is None:
        raise ValueError(f"Branch {branch_id} does not exist.")
    return branch.name


def _check_survey(survey_id):
    if survey_id is not None and not Survey.objects.filter(pk=survey_id).exists():
        raise ValueError(f"Survey {survey_id} does not exist.")


def _satisfaction(branch_id, survey_id):
    name = _branch_name(branch_id)
    _check_survey(survey_id)
    ratings = list(_responses(branch_id, survey_id).values_list("rating", flat=True))
    return {"branch_id": branch_id, "branch": name, "survey_id": survey_id, **analytics.satisfaction(ratings)}


def _nps(branch_id, survey_id):
    name = _branch_name(branch_id)
    _check_survey(survey_id)
    scores = list(_responses(branch_id, survey_id).values_list("recommend_score", flat=True))
    return {"branch_id": branch_id, "branch": name, "survey_id": survey_id, **analytics.nps(scores)}


def _complaints(branch_id, survey_id, limit):
    name = _branch_name(branch_id)
    _check_survey(survey_id)
    comments = list(
        _responses(branch_id, survey_id)
        .filter(rating__lte=3)
        .exclude(comment="")
        .values_list("comment", flat=True)
    )
    return {"branch_id": branch_id, "branch": name, "survey_id": survey_id, **analytics.complaint_topics(comments, limit)}


def _compare(survey_id):
    _check_survey(survey_id)
    ranking = []
    for branch in Branch.objects.all():
        qs = _responses(branch.id, survey_id)
        sat = analytics.satisfaction(list(qs.values_list("rating", flat=True)))
        net = analytics.nps(list(qs.values_list("recommend_score", flat=True)))
        ranking.append({
            "branch_id": branch.id,
            "branch": branch.name,
            "responses": sat["responses"],
            "avg_rating": sat["avg_rating"],
            "satisfaction_pct": sat["satisfaction_pct"],
            "satisfaction_level": sat["level"],
            "nps": net["nps"],
            "nps_level": net["level"],
        })
    ranking.sort(key=lambda row: (row["satisfaction_pct"] or -1, row["nps"] or -101), reverse=True)
    for position, row in enumerate(ranking, start=1):
        row["rank"] = position
    return {"survey_id": survey_id, "ranking": ranking}


# ---------------------------------------------------------------------------
# TOOLS: executable operations
# ---------------------------------------------------------------------------
@mcp.tool()
async def satisfaction_score(branch_id: int, survey_id: int | None = None) -> dict:
    """Average rating and % of satisfied customers (rating 4-5) for one branch."""
    return await sync_to_async(_satisfaction)(branch_id, survey_id)


@mcp.tool()
async def nps_score(branch_id: int, survey_id: int | None = None) -> dict:
    """Net Promoter Score (promoters minus detractors) for one branch."""
    return await sync_to_async(_nps)(branch_id, survey_id)


@mcp.tool()
async def top_complaints(branch_id: int, survey_id: int | None = None, limit: int = 3) -> dict:
    """Most frequent complaint topics in negative comments, with a suggested action."""
    return await sync_to_async(_complaints)(branch_id, survey_id, limit)


@mcp.tool()
async def compare_branches(survey_id: int | None = None) -> dict:
    """Rank all branches by satisfaction and NPS."""
    return await sync_to_async(_compare)(survey_id)


# ---------------------------------------------------------------------------
# RESOURCES: read-only reference data
# ---------------------------------------------------------------------------
@mcp.resource("insight://branches")
async def branches_resource() -> str:
    """All branches of the establishment."""
    rows = await sync_to_async(lambda: list(Branch.objects.values("id", "name", "city", "manager")))()
    return json.dumps({"branches": rows})


@mcp.resource("insight://surveys")
async def surveys_resource() -> str:
    """All surveys with their period."""
    rows = await sync_to_async(lambda: list(Survey.objects.values("id", "title", "period")))()
    return json.dumps({"surveys": rows})


@mcp.resource("insight://benchmarks")
async def benchmarks_resource() -> str:
    """Score thresholds, metric definitions and complaint topics used by the tools."""
    return json.dumps({"benchmarks": BENCHMARKS, "complaint_topics": COMPLAINT_TOPICS})


# ---------------------------------------------------------------------------
# PROMPTS: reusable templates
# ---------------------------------------------------------------------------
@mcp.prompt()
def analysis_report(branch: str, period: str, satisfaction_pct: str, satisfaction_level: str,
                    nps: str, nps_level: str, main_complaint: str) -> str:
    """Executive summary template for one branch analysis."""
    return (
        f"Branch performance report - {branch} ({period})\n"
        f"Customer satisfaction is {satisfaction_pct}% ({satisfaction_level}) "
        f"and the Net Promoter Score is {nps} ({nps_level}).\n"
        f"The most frequent complaint topic is: {main_complaint}.\n"
        "Focus the next action plan on this topic, then re-measure in the next survey."
    )


@mcp.prompt()
def recommendation_guide() -> str:
    """Rules for turning analysis results into recommendations."""
    return (
        "1. If satisfaction is below 70% or NPS is below 20, mark the branch as a priority.\n"
        "2. Address the top complaint topic first using its suggested action.\n"
        "3. Compare with the best-ranked branch and copy its practices.\n"
        "4. Re-run the survey next period to measure the effect."
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
