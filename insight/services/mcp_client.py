"""MCP client used by Django.

Each public method starts the MCP server (mcp_server/server.py) as a
subprocess over stdio, talks to it with the MCP protocol, and returns
plain Python dicts that the views can render as HTML or JSON.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from django.conf import settings
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

BASE_DIR = Path(__file__).resolve().parents[2]


class MCPError(Exception):
    """Raised when the MCP server reports an error (e.g. unknown branch)."""


def _server_params() -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=[str(BASE_DIR / "mcp_server" / "server.py")],
        env={
            **os.environ,
            "PYTHONPATH": str(BASE_DIR) + os.pathsep + os.environ.get("PYTHONPATH", ""),
            "DJANGO_SETTINGS_MODULE": "config.settings",
            "FASTMCP_LOG_LEVEL": "WARNING",  # hide per-request log lines
        },
    )


def _text_of(contents) -> str | None:
    return next((c.text for c in contents if hasattr(c, "text")), None)


def _tool_result(response) -> dict:
    """Extract a dict from a CallToolResult (works across MCP SDK versions)."""
    if response.isError:
        raise MCPError(_text_of(response.content) or "MCP tool failed")
    result = getattr(response, "structuredContent", None)
    if result is None:
        raw = _text_of(response.content)
        if raw is None:
            raise MCPError("Tool returned no content")
        result = json.loads(raw)
    if isinstance(result, dict) and set(result) == {"result"}:
        result = result["result"]
    return result


class _Session:
    """Small wrapper that records every MCP call in a trace list."""

    def __init__(self, session: ClientSession):
        self.session = session
        self.trace: list[dict] = []

    async def tool(self, name: str, arguments: dict) -> dict:
        result = _tool_result(await self.session.call_tool(name=name, arguments=arguments))
        self.trace.append({"type": "Tool", "name": name, "arguments": arguments})
        return result

    async def resource(self, uri: str) -> dict:
        response = await self.session.read_resource(uri)
        self.trace.append({"type": "Resource", "name": uri, "arguments": {}})
        return json.loads(_text_of(response.contents) or "{}")

    async def prompt(self, name: str, arguments: dict | None = None) -> str:
        response = await self.session.get_prompt(name, arguments=arguments or {})
        self.trace.append({"type": "Prompt", "name": name, "arguments": arguments or {}})
        return "\n".join(m.content.text for m in response.messages if hasattr(m.content, "text"))


async def _run(work):
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await work(_Session(session))


def _unwrap(exc: BaseException) -> BaseException:
    """The MCP SDK wraps errors in ExceptionGroups; return the real error."""
    while isinstance(exc, BaseExceptionGroup) and exc.exceptions:
        exc = exc.exceptions[0]
    return exc


def _sync(work):
    try:
        return asyncio.run(asyncio.wait_for(_run(work), timeout=settings.MCP_TIMEOUT_SECONDS))
    except BaseExceptionGroup as group:
        raise _unwrap(group) from None
    except TimeoutError:
        raise MCPError("The MCP server did not answer in time.") from None


# ---------------------------------------------------------------------------
# Public API used by the views
# ---------------------------------------------------------------------------
def get_capabilities() -> dict:
    """Discover everything the MCP server offers."""

    async def work(s: _Session):
        tools = await s.session.list_tools()
        resources = await s.session.list_resources()
        prompts = await s.session.list_prompts()
        return {
            "tools": [{"name": t.name, "description": t.description,
                       "parameters": list((t.inputSchema or {}).get("properties", {}).keys())}
                      for t in tools.tools],
            "resources": [{"uri": str(r.uri), "name": r.name, "description": r.description}
                          for r in resources.resources],
            "prompts": [{"name": p.name, "description": p.description,
                         "arguments": [a.name for a in (p.arguments or [])]}
                        for p in prompts.prompts],
        }

    return _sync(work)


def get_lookups() -> dict:
    """Branches and surveys, read through MCP resources."""

    async def work(s: _Session):
        branches = (await s.resource("insight://branches"))["branches"]
        surveys = (await s.resource("insight://surveys"))["surveys"]
        return {"branches": branches, "surveys": surveys}

    return _sync(work)


def analyze_branch(branch_id: int, survey_id: int | None = None) -> dict:
    """Full branch analysis: 3 tools + 2 resources + 2 prompts in one MCP session."""

    async def work(s: _Session):
        benchmarks = await s.resource("insight://benchmarks")
        surveys = (await s.resource("insight://surveys"))["surveys"]
        args = {"branch_id": branch_id, "survey_id": survey_id}

        sat = await s.tool("satisfaction_score", args)
        net = await s.tool("nps_score", args)
        complaints = await s.tool("top_complaints", {**args, "limit": 3})

        period = "All surveys"
        for survey in surveys:
            if survey["id"] == survey_id:
                period = survey["period"]
        top = complaints["top_complaints"]
        main_complaint = top[0]["topic"] if top else "No major complaints"

        report = await s.prompt("analysis_report", {
            "branch": sat["branch"],
            "period": period,
            "satisfaction_pct": str(sat["satisfaction_pct"]),
            "satisfaction_level": sat["level"],
            "nps": str(net["nps"]),
            "nps_level": net["level"],
            "main_complaint": main_complaint,
        })
        guide = await s.prompt("recommendation_guide")

        # Apply the recommendation guide (rule 1 + rule 2).
        is_priority = (sat["satisfaction_pct"] or 0) < 70 or (net["nps"] or 0) < 20
        recommendations = [c["suggested_action"] for c in top]
        if not recommendations:
            recommendations = ["Keep current practices and keep monitoring the next survey."]

        return {
            "branch": sat["branch"],
            "period": period,
            "satisfaction": sat,
            "nps": net,
            "complaints": complaints,
            "is_priority": is_priority,
            "recommendations": recommendations,
            "report": report,
            "recommendation_guide": guide,
            "definitions": benchmarks["benchmarks"]["definitions"],
            "mcp_trace": s.trace,
        }

    return _sync(work)


def compare_branches(survey_id: int | None = None) -> dict:
    async def work(s: _Session):
        result = await s.tool("compare_branches", {"survey_id": survey_id})
        result["mcp_trace"] = s.trace
        return result

    return _sync(work)
