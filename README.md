<div align="center">

# SEC-10-K-Structured-Extraction-Web-Demo

**將 SEC 10-K 申報文件轉換為結構化資料與可讀 Markdown 的 Demo**

![web0](assets/image0.png)

![web1](assets/image1.png)

![web2](assets/image2.png)

</div>

---

## 一、功能概覽

本專案提供一站式的 SEC 10-K 年報解析服務，從原始 EDGAR 文件抽取結構化資料並渲染為人類可讀的格式。

- **Item 結構化抽取**：自動識別並分割 10-K 內各個 Item（Part I / II / III / IV），輸出標準化的 `FilingOutput` JSON
- **Item Status 標註**：區分 `extracted` / `incorporated_by_reference` / `not_applicable` / `reserved` / `missing` 五種狀態
- **XBRL 財報擷取**：從 XBRL Instance + Presentation + Label Linkbase 直接還原 Item 8 主要財務報表
- **Markdown 渲染**：將 XBRL Facts 渲染為可讀的 Markdown，包含主表（Income Statement、Balance Sheet、Cash Flow 等）、數字附註與文字揭露
- **非同步 Job Queue**：請求送出後立即取得 `job_id`，背景處理完成後可輪詢取回結果
- **Cache 機制**：以 `accession_number` 作為 Cache Key，相同申報文件只處理一次
- **雙輸入模式**：支援 `cik + accession_number` 或直接給 EDGAR URL 兩種輸入方式

---

## 二、專案架構

```
SEC-10-K-Structured-Extraction-Web-Demo/
├── api/                              # 後端 FastAPI 服務
│   ├── main.py                       # FastAPI app 入口、lifespan、CORS
│   ├── routes.py                     # POST /jobs, GET /jobs/{id}, POST /xbrl-markdown ...
│   ├── worker.py                     # 背景 Job Worker（asyncio）
│   ├── cache.py                      # CacheService（filings / jobs 讀寫封裝）
│   ├── db.py                         # aiosqlite schema 初始化
│   ├── utils.py                      # SEC URL 解析等工具
│   ├── item8_markdown.py             # 一步式 XBRL → Markdown 便利函數
│   ├── models/
│   │   └── job.py                    # API 專用 request/response schema
│   ├── sec_10k_pipeline/             # 解析引擎
│   │   ├── pipeline.py               # 同步 Pipeline
│   │   ├── async_pipeline.py         # 非同步版本（httpx + executor）
│   │   ├── postprocessor.py          # Item 後處理（清理、標註 status）
│   │   ├── patterns.py               # 正則樣式
│   │   ├── models.py                 # FilingInput / FilingOutput / ItemResult
│   │   ├── item8_xbrl_facts.py       # XBRL 解析（Instance + Presentation + Label）
│   │   ├── render_item8_markdown.py  # XBRL → Markdown 渲染
│   │   └── parsers/
│   │       ├── regex_parser.py       # Regex parser
│   │       ├── llm_parser.py         # LLM-assisted parser
│   │       └── hybrid.py             # Hybrid parser（regex + LLM fallback）
│   └── requirements.txt
│
├── frontend/                         # Vue 3 前端
│   ├── src/
│   │   ├── views/                    # 頁面元件
│   │   ├── components/               # 共用元件（含 shadcn-vue）
│   │   ├── stores/                   # Pinia stores
│   │   ├── router/                   # Vue Router
│   │   ├── types/                    # TypeScript 型別
│   │   └── lib/                      # API client、utils
│   ├── package.json
│   └── vite.config.ts
│
├── docs/
│   ├── api.md                        # API 使用文檔
│   ├── api-design.md                 # API 架構設計
│   └── frontend-design.md            # 前端設計文檔
│
├── assets/                           # README 截圖
└── README.md
```

### 後端資料流

```
Client ──POST /jobs──▶ Router ──▶ Cache 查 accession_number?
                                    │
                          ┌─ hit ──▶ 直接建 done job ──▶ 回 cache_hit=true
                          │
                          └─ miss ─▶ 建 pending job ──▶ JobQueue
                                                          │
                                                          ▼
                                                      Worker（asyncio）
                                                          │
                                                          ├── AsyncPipeline（httpx fetch）
                                                          ├── Parser（regex / LLM / hybrid）
                                                          └── Postprocessor
                                                          │
                                                          ▼
                                                      寫入 filings cache
```

---

## 三、技術選型

### 後端

| 類別 | 技術 | 用途 |
|---|---|---|
| Web Framework | **FastAPI** | 路由、自動 OpenAPI 文檔、Pydantic 驗證 |
| ASGI Server | **Uvicorn** | 開發與正式環境執行 |
| HTTP Client | **httpx** / **requests** | SEC EDGAR 文件下載 |
| 資料庫 | **SQLite** (`aiosqlite`) | Jobs / Filings cache，可平移至 PostgreSQL |
| 任務佇列 | **asyncio.Queue** | 輕量級背景 Job Queue |
| HTML / XML 解析 | **lxml** / **BeautifulSoup** | XBRL 與 10-K HTML 處理 |
| 文字比對 | **rapidfuzz** | Item 標題模糊匹配 |
| 表格渲染 | **tabulate** / **tabulate_html** | HTML 表格轉 Markdown |
| 資料模型 | **Pydantic** | FilingInput / FilingOutput 強型別 |

### 前端

| 類別 | 技術 | 用途 |
|---|---|---|
| Framework | **Vue 3**（`^3.5`） | Composition API + `<script setup>` |
| Language | **TypeScript**（`~6.0`） | 全程強型別 |
| Build Tool | **Vite**（`^8.0`） | 開發伺服器與打包 |
| Router | **Vue Router**（`^5.0`） | SPA 路由 |
| State | **Pinia**（`^3.0`） | 全域狀態管理 |
| UI Kit | **shadcn-vue** + **Tailwind CSS v4** | Zinc 主題、Light/Dark 雙模式 |
| Icons | **lucide-vue-next** | 圖示 |
| Markdown | **markdown-it** + **dompurify** | Item 8 Markdown 渲染與消毒 |

---

## 四、快速開始

### 環境需求

- Python `>= 3.10`
- Node.js `>= 18`
- npm

### 1. 啟動後端

```bash
cd api
pip install -r requirements.txt

# 啟動 API（預設 http://localhost:8000）
uvicorn main:app --reload
```

互動式 API 文檔：`http://localhost:8000/docs`

### 2. 啟動前端

```bash
cd frontend
npm install
npm run dev
# 開發伺服器預設 http://localhost:5173
```

### 3. 環境變數

| 變數 | 預設值 | 說明 |
|---|---|---|
| `DB_PATH` | `./data/sec_extraction.db` | SQLite 資料庫路徑 |
| `CORS_ORIGINS` | `http://localhost:5173` | 允許跨域來源（逗號分隔） |

可在 `api/.env` 設定。

### 4. 端到端測試

```bash
# 送出解析請求
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"cik":"0000320193","accession_number":"0000320193-23-000106"}'
# → { "job_id": "...", "status": "pending", "cache_hit": false }

# 取得 Item 8 XBRL Markdown
curl -X POST http://localhost:8000/xbrl-markdown \
  -H "Content-Type: application/json" \
  -d '{"cik":"0000104169","accession_number":"0000104169-24-000056"}' \
  -o report.md
```

或直接以 Python 使用解析模組：

```python
from api.sec_10k_pipeline.item8_xbrl_facts import get_item8_xbrl_facts
from api.sec_10k_pipeline.render_item8_markdown import render_markdown
from api.item8_markdown import get_item8_markdown

# 兩步式
payload = get_item8_xbrl_facts("0000104169", "0000104169-24-000056")
markdown = render_markdown(payload)

# 一步式
markdown = get_item8_markdown("0000104169", "0000104169-24-000056")
```

---

## 五、API 摘要

完整文檔請見 [docs/api.md](docs/api.md)。

| 方法 | 路徑 | 功能 | 同步性 |
|---|---|---|---|
| `POST` | `/jobs` | 送出 10-K 解析請求，立即取得 `job_id` | 非同步 |
| `GET` | `/jobs/{job_id}` | 輪詢 Job 狀態與 `FilingOutput` 結果 | — |
| `GET` | `/filings/{accession_number}` | 直接從 Cache 取已完成的 `FilingOutput`（cache miss 回 404） | — |
| `POST` | `/xbrl-markdown` | 同步擷取 XBRL 並渲染為 Markdown，回 `text/markdown` | 同步 |

### POST `/jobs`

```json
// Request
{ "cik": "0000320193", "accession_number": "0000320193-23-000106" }
// 或
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

| Status | 說明 |
|---|---|
| `extracted` | 成功抽取內容，`content_text` 有值 |
| `incorporated_by_reference` | 引用其他文件（常見於 Part III） |
| `not_applicable` | 公司明確表示不適用 |
| `reserved` | SEC 規定保留（如 Item 6） |
| `missing` | Parser 找不到此 Item |

---

## 文件索引

- [docs/api.md](docs/api.md) — API 端點使用說明
- [docs/api-design.md](docs/api-design.md) — 後端架構設計
- [docs/frontend-design.md](docs/frontend-design.md) — 前端視覺與互動設計
