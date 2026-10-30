from django.shortcuts import render
from rest_framework import status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response as APIResponse

from .models import Branch, Survey
from .serializers import AnalyzeRequestSerializer, BranchSerializer, SurveySerializer
from .services import mcp_client


def _int_or_none(value):
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# HTML pages
# ---------------------------------------------------------------------------
def dashboard(request):
    """Pick a branch and a survey, then analyse it through MCP."""
    context = {"error": None, "result": None}
    try:
        context.update(mcp_client.get_lookups())  # branches + surveys via MCP resources
    except Exception as exc:  # MCP server could not start
        context.update({"branches": [], "surveys": [], "error": f"MCP server error: {exc}"})

    branch_id = _int_or_none(request.GET.get("branch"))
    survey_id = _int_or_none(request.GET.get("survey"))
    context.update({"selected_branch": branch_id, "selected_survey": survey_id})

    if branch_id is not None:
        try:
            context["result"] = mcp_client.analyze_branch(branch_id, survey_id)
        except Exception as exc:
            context["error"] = str(exc)
    return render(request, "insight/dashboard.html", context)


def compare(request):
    survey_id = _int_or_none(request.GET.get("survey"))
    context = {"surveys": Survey.objects.all(), "selected_survey": survey_id, "error": None}
    try:
        context["result"] = mcp_client.compare_branches(survey_id)
    except Exception as exc:
        context["result"], context["error"] = None, str(exc)
    return render(request, "insight/compare.html", context)


def capabilities(request):
    context = {"error": None}
    try:
        context["caps"] = mcp_client.get_capabilities()
    except Exception as exc:
        context["caps"], context["error"] = None, str(exc)
    return render(request, "insight/capabilities.html", context)


# ---------------------------------------------------------------------------
# REST API (Django REST Framework)
# ---------------------------------------------------------------------------
class BranchViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/branches/ and /api/branches/{id}/"""

    queryset = Branch.objects.all()
    serializer_class = BranchSerializer


class SurveyViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/surveys/ and /api/surveys/{id}/"""

    queryset = Survey.objects.all()
    serializer_class = SurveySerializer


@api_view(["GET"])
def api_capabilities(request):
    """Discover the MCP server's tools, resources and prompts."""
    try:
        return APIResponse(mcp_client.get_capabilities())
    except Exception as exc:
        return APIResponse({"error": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(["POST"])
def api_analyze(request):
    """Analyse one branch. Body: {"branch_id": 1, "survey_id": 2}"""
    serializer = AnalyzeRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    try:
        result = mcp_client.analyze_branch(data["branch_id"], data.get("survey_id"))
    except mcp_client.MCPError as exc:
        return APIResponse({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as exc:
        return APIResponse({"error": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return APIResponse(result)


@api_view(["GET"])
def api_compare(request):
    """Rank all branches. Optional: ?survey_id=2"""
    survey_id = _int_or_none(request.query_params.get("survey_id"))
    try:
        return APIResponse(mcp_client.compare_branches(survey_id))
    except mcp_client.MCPError as exc:
        return APIResponse({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as exc:
        return APIResponse({"error": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
