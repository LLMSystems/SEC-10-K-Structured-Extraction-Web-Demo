<div align="center">

# SEC-10-K-Structured-Extraction-Web-Demo

**A demo that converts SEC 10-K filings into structured data and human-readable Markdown**

[English](README.md) | [中文](README_zh-CN.md)

https://github.com/user-attachments/assets/02e51b12-4362-44bf-afa3-aca48c5852c0

</div>

---

## 1. Features

A one-stop service for parsing SEC 10-K annual reports — extracting structured data from raw EDGAR filings and rendering them into human-readable formats.

- **Structured Item Extraction**: Automatically identifies and splits all Items in a 10-K (Part I / II / III / IV), outputting a standardized `FilingOutput` JSON
- **Item Status Labeling**: Distinguishes five statuses — `extracted` / `incorporated_by_reference` / `not_applicable` / `reserved` / `missing`
- **XBRL Financial Data Extraction**: Reconstructs Item 8 financial statements directly from XBRL Instance + Presentation + Label Linkbase
- **Markdown Rendering**: Renders XBRL facts into readable Markdown, including primary statements (Income Statement, Balance Sheet, Cash Flow, etc.), numeric footnotes, and text disclosures
- **Async Job Queue**: Returns a `job_id` immediately upon submission; poll to retrieve results after background processing completes
- **Caching**: Uses `accession_number` as the cache key — identical filings are only processed once
- **Dual Input Modes**: Accepts either `cik + accession_number` or a direct EDGAR URL
- **Admin Panel**: System health dashboard (job status distribution, recent failures), flag analytics (rule trigger frequency, problematic items, per-parser performance, stage timing), validator rule reference, and an item detail drawer with lazy-loaded content

---

## 2. Project Structure

```
SEC-10-K-Structured-Extraction-Web-Demo/
├── api/                              # FastAPI backend
│   ├── main.py                       # FastAPI app entrypoint, lifespan, CORS
│   ├── routes.py                     # POST /jobs, GET /jobs/{id}, POST /xbrl-markdown ...
│   ├── worker.py                     # Background job worker (asyncio)
│   ├── cache.py                      # CacheService (filings / jobs read-write wrapper)
│   ├── db.py                         # aiosqlite schema initialization
│   ├── utils.py                      # SEC URL parsing and utilities
│   ├── item8_markdown.py             # One-step XBRL → Markdown convenience function
│   ├── models/
│   │   └── job.py                    # API request/response schemas
│   ├── sec_10k_pipeline/             # Parsing engine
│   │   ├── pipeline.py               # Synchronous pipeline
│   │   ├── async_pipeline.py         # Async version (httpx + executor)
│   │   ├── postprocessor.py          # Item post-processing (cleanup, status labeling)
│   │   ├── patterns.py               # Regex patterns
│   │   ├── models.py                 # FilingInput / FilingOutput / ItemResult
│   │   ├── item8_xbrl_facts.py       # XBRL parsing (Instance + Presentation + Label)
│   │   ├── render_item8_markdown.py  # XBRL → Markdown rendering
│   │   └── parsers/
│   │       ├── regex_parser.py       # Regex parser
│   │       ├── llm_parser.py         # LLM-assisted parser
│   │       └── hybrid.py             # Hybrid parser (regex + LLM fallback)
│   └── requirements.txt
│
├── frontend/                         # Vue 3 frontend
│   ├── src/
│   │   ├── views/                    # Page components
│   │   ├── components/               # Shared components (including shadcn-vue)
│   │   ├── stores/                   # Pinia stores
│   │   ├── router/                   # Vue Router
│   │   ├── types/                    # TypeScript types
│   │   └── lib/                      # API client, utils
│   ├── package.json
│   └── vite.config.ts
│
├── docs/
│   ├── api.md                        # API usage documentation
│   ├── api-design.md                 # API architecture design
│   └── frontend-design.md            # Frontend design documentation
│
├── assets/                           # README screenshots
└── README.md
```

## 3. Tech Stack

### Backend

| Category | Technology | Purpose |
|---|---|---|
| Web Framework | **FastAPI** | Routing, automatic OpenAPI docs, Pydantic validation |
| ASGI Server | **Uvicorn** | Development and production server |
| HTTP Client | **httpx** / **requests** | SEC EDGAR document downloads |
| Database | **SQLite** (`aiosqlite`) | Jobs / filings cache; portable to PostgreSQL |
| Task Queue | **asyncio.Queue** | Lightweight background job queue |
| HTML / XML Parsing | **lxml** / **BeautifulSoup** | XBRL and 10-K HTML processing |
| Fuzzy Matching | **rapidfuzz** | Item title fuzzy matching |
| Table Rendering | **tabulate** / **tabulate_html** | HTML table to Markdown conversion |
| Data Models | **Pydantic** | Strongly typed FilingInput / FilingOutput |

### Frontend

| Category | Technology | Purpose |
|---|---|---|
| Framework | **Vue 3** (`^3.5`) | Composition API + `<script setup>` |
| Language | **TypeScript** (`~6.0`) | End-to-end strong typing |
| Build Tool | **Vite** (`^8.0`) | Dev server and bundling |
| Router | **Vue Router** (`^5.0`) | SPA routing |
| State | **Pinia** (`^3.0`) | Global state management |
| UI Kit | **shadcn-vue** + **Tailwind CSS v4** | Zinc theme, light/dark mode |
| Icons | **lucide-vue-next** | Icons |
| Markdown | **markdown-it** + **dompurify** | Item 8 Markdown rendering |

---

## 4. Quick Start

### Prerequisites

- Python `>= 3.10`
- Node.js `>= 18`
- npm

### 1. Start the backend

```bash
cd api
pip install -r requirements.txt

# Start the API (default: http://localhost:8000)
uvicorn main:app --reload
```

Interactive API docs: `http://localhost:8000/docs`

### 2. Start the frontend

```bash
cd frontend
npm install
npm run dev
# Dev server default: http://localhost:5173
```

### 3. Environment variables

**Backend**

| Variable | Default | Description |
|---|---|---|
| `DB_PATH` | `./data/sec_extraction.db` | SQLite database path |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed CORS origins (comma-separated) |

Configure in `api/.env`.

**Frontend**

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | *(fill in)* | Backend URL |

Configure in `frontend/.env`.

### 4. End-to-end test

```bash
# Submit a parsing request
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"cik":"0000320193","accession_number":"0000320193-23-000106"}'
# → { "job_id": "...", "status": "pending", "cache_hit": false }

# Fetch Item 8 XBRL Markdown
curl -X POST http://localhost:8000/xbrl-markdown \
  -H "Content-Type: application/json" \
  -d '{"cik":"0000104169","accession_number":"0000104169-24-000056"}' \
  -o report.md
```

Or use the parsing module directly in Python:

```python
from api.sec_10k_pipeline.item8_xbrl_facts import get_item8_xbrl_facts
from api.sec_10k_pipeline.render_item8_markdown import render_markdown
from api.item8_markdown import get_item8_markdown

# Two-step
payload = get_item8_xbrl_facts("0000104169", "0000104169-24-000056")
markdown = render_markdown(payload)

# One-step
markdown = get_item8_markdown("0000104169", "0000104169-24-000056")
```

---

## 5. API Reference

See [docs/api.md](docs/api.md) for full documentation.

| Method | Path | Description | Mode |
|---|---|---|---|
| `POST` | `/jobs` | Submit a 10-K parsing request, get `job_id` immediately | Async |
| `GET` | `/jobs/{job_id}` | Poll job status and retrieve `FilingOutput` result | — |
| `GET` | `/filings/{accession_number}` | Fetch a completed `FilingOutput` from cache (404 on miss) | — |
| `POST` | `/xbrl-markdown` | Synchronously extract XBRL and render to Markdown (`text/markdown`) | Sync |

### POST `/jobs`

```json
// Request
{ "cik": "0000320193", "accession_number": "0000320193-23-000106" }
// or
{ "url": "https://www.sec.gov/Archives/edgar/data/320193/.../aapl-20250927.htm" }

// Response 202
{ "job_id": "3fa85f64-...", "status": "pending", "cache_hit": false }
```

### GET `/jobs/{job_id}`

```json
{
  "job_id": "3fa85f64-...",
  "status": "done",          // pending | running | done | failed
  "result": { "filing_info": {...}, "items": [...], "timing": {...} },
  "error": null,
  "created_at": "2026-05-12T10:00:00Z",
  "completed_at": "2026-05-12T10:00:01Z"
}
```

### POST `/xbrl-markdown`

```json
// Request
{ "cik": "0000104169", "accession_number": "0000104169-24-000056" }

// Response 200 (Content-Type: text/markdown)
# Ford Motor Co Item 8 Report
- CIK: `0000104169`
- ...
## Consolidated Statements of Operations
| Line Item | FY2023 ... | FY2022 ... |
...
```

### Item Status

| Status | Description |
|---|---|
| `extracted` | Content successfully extracted; `content_text` is populated |
| `incorporated_by_reference` | References another document (common in Part III) |
| `not_applicable` | Company explicitly states not applicable |
| `reserved` | SEC-reserved item (e.g. Item 6) |
| `missing` | Parser could not locate this item |

---

## Documentation

- [docs/api.md](docs/api.md) — API endpoint reference
- [docs/api-design.md](docs/api-design.md) — Backend architecture design
- [docs/frontend-design.md](docs/frontend-design.md) — Frontend visual and interaction design
- [docs/validator-rules.md](docs/validator-rules.md) — Validator rules and quality report (with data sources)
