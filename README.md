# Insight MCP – Survey Analytics with Django, DRF and MCP

Insight helps a commercial establishment with several branches understand its
customer-satisfaction surveys. Django stores branches, surveys and customer
responses; an **MCP (Model Context Protocol) server** exposes the analysis as
**Tools**, the reference data as **Resources**, and report templates as
**Prompts**. Django talks to the MCP server as an MCP client and shows the
results as web pages and as a REST API.

> The project uses **fictional demo data** (4 branches, 2 surveys, ~460 responses)
> created by the `seed_demo` command.

## Architecture

```
Browser / API client
        │
        ▼
Django (views + Django REST Framework)
        │  MCP client (stdio)
        ▼
MCP server  (mcp_server/server.py)
   ├── Tools      satisfaction_score · nps_score · top_complaints · compare_branches
   ├── Resources  insight://branches · insight://surveys · insight://benchmarks
   └── Prompts    analysis_report · recommendation_guide
        │
        ▼
SQLite database (Branch, Survey, Response)
```

| MCP part | Name | What it does |
|---|---|---|
| Tool | `satisfaction_score` | Average rating and % of customers who rated 4–5 |
| Tool | `nps_score` | Net Promoter Score = % promoters (9–10) − % detractors (0–6) |
| Tool | `top_complaints` | Most frequent complaint topics in negative comments + suggested action |
| Tool | `compare_branches` | Ranks all branches by satisfaction and NPS |
| Resource | `insight://branches` | List of branches |
| Resource | `insight://surveys` | List of surveys and periods |
| Resource | `insight://benchmarks` | Score thresholds, metric definitions, complaint topics |
| Prompt | `analysis_report` | Executive summary template filled with the results |
| Prompt | `recommendation_guide` | Rules for turning results into recommendations |

## Installation (Windows / PyCharm)

```powershell
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo       # creates the demo data
python manage.py createsuperuser # for /admin/
python manage.py runserver
```

The MCP server starts automatically for each request – do **not** run
`mcp_server/server.py` yourself.

## Pages

| URL | Page |
|---|---|
| `/` | Analyze one branch (KPIs, complaints, report, recommendations, list of MCP calls) |
| `/compare/` | Ranking of all branches |
| `/capabilities/` | Tools, resources and prompts discovered from the MCP server |
| `/admin/` | Django admin for branches, surveys and responses |

## REST API

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/capabilities/` | MCP discovery (tools, resources, prompts) |
| POST | `/api/analyze/` | Body `{"branch_id": 1, "survey_id": 2}` – full branch analysis |
| GET | `/api/compare/?survey_id=2` | Branch ranking |
| GET | `/api/branches/`, `/api/surveys/` | Branch and survey lists |

Invalid input (e.g. unknown branch) returns **400 Bad Request**.

## Tests

```powershell
python manage.py test insight
```

## Project structure

```
insight_mcp/
  manage.py
  requirements.txt
  config/                 Django settings and root URLs
  insight/                Django app
    models.py             Branch, Survey, Response
    admin.py              admin configuration
    serializers.py        DRF serializers + input validation
    views.py              HTML pages and REST API
    urls.py
    services/mcp_client.py   MCP client (stdio)
    management/commands/seed_demo.py
    templates/insight/    base, dashboard, compare, capabilities
    tests.py
  mcp_server/
    server.py             MCP server: tools, resources, prompts
    analytics.py          pure calculations (satisfaction, NPS, complaints)
    knowledge.py          benchmarks and complaint topics
```
