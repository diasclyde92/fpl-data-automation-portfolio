# End-to-End Web Scraping & Data Automation Pipeline

> **Portfolio Showcase**: A production-grade demonstration project modeling an end-to-end data engineering pipeline—from web extraction and data transformation to multi-format business reporting, web dashboarding, and automated CI/CD scheduling.

---

## 📌 Project Purpose

Freelance clients frequently need robust, hands-off automation systems: scraping dynamic web data reliably, validating and transforming records, persisting them in a structured store, and automatically generating actionable client deliverables (such as Excel sheets, PDF briefs, or interactive dashboards).

This project demonstrates a production-style, maintainable implementation of that exact lifecycle. While demonstrated using a Fantasy Premier League (FPL) data use case (integrating with an existing GitHub Pages web presence), the architecture is intentionally modular and reusable across e-commerce, real estate, lead generation, financial monitoring, and competitor price tracking.

---

## 🚀 What This Project Demonstrates

- **Resilient Web Extraction**: Handling network requests, rate limiting, and dynamic content extraction.
- **Data Pipeline Engineering**: Structured staging from raw ingested records to validated, cleaned data models.
- **Relational Storage**: Relational schema design and efficient querying with SQLite.
- **Automated Business Reporting**:
  - Formatted multi-tab Excel workbooks (`.xlsx`) with styling and formulas.
  - Automated executive summary PDF generation.
- **Interactive Visualization**: Lightweight dashboard presentation for stakeholder consumption.
- **Scheduled Automation**: Headless workflow orchestration via GitHub Actions.
- **Maintainability & Testing**: Clean project conventions, configuration isolation, and automated tests.

---

## 🔄 High-Level Pipeline

```
Web Source (HTML / API)
       │
       ▼
[ Extraction Layer ] (requests / BeautifulSoup / Playwright)
       │
       ▼
 Raw Data Staging (data/raw)
       │
       ▼
[ Cleaning & Validation ] (pandas / pydantic)
       │
       ▼
 Relational Database (SQLite)
       │
       ▼
[ Analytics & Aggregations ]
       │
       ├─────────────────────────┼─────────────────────────┐
       ▼                         ▼                         ▼
 Excel Report (.xlsx)      PDF Summary (.pdf)       Web Dashboard
       │                         │                         │
       └─────────────────────────┴─────────────────────────┘
                                 │
                   [ Automated Schedule / CI ] (GitHub Actions)
```

---

## 🛠️ Planned Technology Stack

- **Language**: Python 3.10+
- **Extraction**: `requests`, `beautifulsoup4` (Playwright / Selenium introduced only if dynamic rendering is required)
- **Data Processing & Validation**: `pandas`
- **Database**: SQLite (built-in relational engine, zero-config deployment)
- **Reporting**: `openpyxl` (Excel), PDF generation library (e.g. `reportlab` or `weasyprint`)
- **Testing**: `pytest`
- **Automation / Orchestration**: GitHub Actions

---

## 📅 Planned Implementation Phases

- [x] **Phase 1: Project Skeleton & Repository Setup**
  - Project directory conventions, documentation, environment configuration, and entry point.
- [x] **Phase 2: Reusable Scraping Foundation**
  - Resilient HTTP client with retry logic, custom exception taxonomy, BeautifulSoup parsing helper, and abstract base scraper lifecycle.
- [x] **Phase 3: First Concrete Scraper Implementation**
  - Concrete scraper demonstration (`BookScraper`) against a public test target, value normalization, error tolerance, CLI execution, and unit/integration testing.
- [x] **Phase 4: Pagination & Raw Data Storage**
  - Catalog pagination traversal, loop protection, and raw HTML artifact preservation under `data/raw/`.
- [x] **Phase 5: Data Modeling, Validation & SQLite Persistence**
  - Pydantic domain models, data validation/normalization, duplicate upsert handling, and relational persistence with SQLite.
- [x] **Phase 6: Relational Data Analytics (Pandas)**
  - Decoupled analytics layer reading SQLite records into structured DataFrames, computing statistics, ratings distributions, rankings, and data quality diagnostics.
- [x] **Phase 7: Professional Excel Reporting Layer (openpyxl)**
  - Executive multi-tab `.xlsx` client deliverable with KPI summary, catalog data tables, price distributions, rating charts, and inventory breakdowns.
- [x] **Phase 8: Automated PDF Executive Briefing (ReportLab)**
  - Multi-page client-ready PDF brief with dynamic narrative insights, KPI scorecard, pricing charts, rating breakdowns, and data governance audit.
- [x] **Phase 9: Target Analysis & Primary Use Case (FPL)**
  - Concrete domain pipeline for Fantasy Premier League: official API extraction, Pydantic data modeling, SQLite relational persistence, and Pandas analytics.
- [x] **Phase 10: Web Dashboard Integration (Streamlit)**
- [x] **Phase 11: Historical Snapshot Storage (FPL)**
  - Immutable historical player snapshots (`fpl_player_snapshots`), pipeline run audit log (`fpl_runs`), dual persistence (current state + historical snapshots), and idempotent transaction boundaries.
- [ ] **Phase 12: Automation & CI/CD Pipeline**
  - GitHub Actions workflow for scheduled headless execution and artifact archiving.

---

## 🏗️ End-to-End Pipeline Architecture

The system enforces strict separation of concerns across extraction, modeling, validation, storage, and analytics:

```
                  Target Website (HTML)
                           │
                           ▼
                      HTTPClient (retries, timeouts, headers)
                           │
                           ▼
                      BookScraper (traverses pagination controls)
                     ┌─────┴────────────────────────┐
                     ▼                              ▼
             Raw HTML Responses             Extracted Records
                     │                     (loose Python dicts)
                     ▼                              │
            [ RawStorage Layer ]                    ▼
                     │                      [ Book Data Model ]
                     ▼                         (Pydantic v2)
          data/raw/books/<run_id>/                  │
              ├── page_001.html                     ▼
              └── page_002.html             [ Data Validation ]
                                            (type checking & rules)
                                             ┌──────┴──────┐
                                             ▼             ▼
                                        Valid Books   Invalid Records
                                             │         (logged/audited)
                                             ▼
                                     [ SQLiteStorage ]
                                  (parameterized upsert)
                                             │
                                             ▼
                                  data/processed/books.db
                                             │
                                             ▼
                                     [ BookAnalytics ]
                                      (Pandas layer)
                                 ┌───────────┴───────────┐
                                 ▼                       ▼
                          AnalyticsResult         Data Quality
                          (stats & rankings)       Diagnostics
                                 │
                                 ▼
                     Downstream Reporting & BI
                       (Excel, PDF, Web UI)
```

### 🧠 Why Separation of Concerns Matters
In professional data engineering:
- **Scraper's Sole Job**: Navigate the web and extract raw values from HTML without caring how data is stored or analyzed.
- **Model & Validation Job**: Enforce domain invariants and clean inputs before downstream persistence without caring about HTML tags.
- **Database Storage Job**: Manage relational schemas, connection lifecycles, and transactions without web or analytical dependencies.
- **Analytics Layer Job**: Consume clean tabular data from SQLite, perform vectorized aggregation with Pandas, compute summary statistics, and provide structured outputs for future Excel/PDF/dashboard consumers.
- **Pipeline Orchestrator**: Coordinates the flow cleanly so scrapers can easily be replaced (e.g. swapping `BookScraper` for `FPLScraper`) while reusing storage, analytics, and reporting patterns.

---

## ⚽ Real-World Data Pipeline: Fantasy Premier League (Phase 9)

In Phase 9, the reusable pipeline architecture built and tested with Books to Scrape was extended to a real-world, rapidly changing sports data target: **Fantasy Premier League (FPL)**.

### 🌐 Source Data Architecture
- **Endpoint**: Official FPL API bootstrap static endpoint (`https://fantasy.premierleague.com/api/bootstrap-static/`).
- **Data Flow**:
  1. [`HTTPClient`](file:///src/scraper/http_client.py) performs resilient GET requests with desktop User-Agent simulation and exponential retry backoff.
  2. [`RawStorage`](file:///src/storage/raw_storage.py) preserves immutable raw JSON responses under `data/raw/fpl/<run_id>/bootstrap.json` for auditing and historical backtesting.
  3. [`FPLScraper`](file:///src/scraper/fpl_scraper.py) extracts raw element structures, resolving team IDs to short names (e.g. `ARS`, `MCI`, `LIV`) and element type IDs to standard position abbreviations (`GKP`, `DEF`, `MID`, `FWD`), scaling tenth-million prices (`now_cost` `61` $\to$ `£6.1m`), and parsing percentage strings into floats.
  4. [`FPLPlayer`](file:///src/models/fpl_player.py) model validates domain invariants using Pydantic v2.
  5. [`FPLStorage`](file:///src/storage/fpl_storage.py) executes parameterized upserts (`INSERT ... ON CONFLICT(id) DO UPDATE SET ...`) into `data/processed/fpl.db`.
  6. [`FPLAnalytics`](file:///src/analytics/fpl_analytics.py) computes key fantasy metrics: points-per-million value rankings, points-per-90 rates, positional & team totals, top form leaders, and data hygiene audits.

### 💻 Running the FPL Pipeline CLI
Execute live extraction, validation, raw JSON backup, and relational persistence:

```bash
# Run extraction and persist to SQLite (data/processed/fpl.db)
python -m src.pipeline.fpl_pipeline

# Run extraction with raw JSON preservation under data/raw/fpl/<run_id>/
python -m src.pipeline.fpl_pipeline --save-raw
```

### 📈 Running the FPL Analytics CLI
Run analytical metrics, top value rankings, and data quality diagnostics:

```bash
# Run analytics against the default FPL database
python -m src.analytics.fpl_analytics

# Run analytics with custom database path
python -m src.analytics.fpl_analytics --db-path data/processed/fpl.db
```

---

## 🖥️ Interactive Web Dashboard (Streamlit - Phase 10)

The [`FPL Dashboard`](file:///src/dashboard/fpl_dashboard.py) provides a web-based business and sports analytics application consuming [`FPLAnalytics`](file:///src/analytics/fpl_analytics.py) and SQLite persistence without embedding raw SQL or duplicating metric calculations.

### 🏛️ Dashboard Data Flow & Architecture
```
FPL SQLite Database (data/processed/fpl.db)
       │
       ▼
[ FPLStorage ] (connection & schema lifecycle)
       │
       ▼
[ FPLAnalytics ] (vectorized pandas aggregations & quality audit)
       │
       ▼
[ Dashboard Service Helpers ] (filtering criteria & player cards)
       │
       ▼
[ Streamlit Web Application ] (reactive UI, cached data bundle)
```

### 🌟 Key Dashboard Features
1. **Executive KPI Scorecard**: Total Players, Average Price (£m), Total Points, Average Points, Highest Points, Average Ownership (%).
2. **Interactive Filters**: Dynamic sidebar filtering by Position, Club/Team, Availability Status, Price Slider, Minimum Ownership (%), and Minimum Minutes Played.
3. **Top Player Leaderboards**: Tabbed views for Total Points, Value (Points per Million), Current Form, Goals Scored, and Assists, with configurable display depth (Top 5, 10, 20).
4. **Value Efficiency Analysis**:
   - Interactive scatter plot mapping **Player Price vs Total Points** with position coloring and value scaling.
   - Ranked table of top value assets providing maximum points per million budget spend.
5. **Team & Position Performance**: Bar charts and drill-down tables detailing aggregate points and average prices by club and role.
6. **Individual Player Explorer**: Interactive dropdown selector displaying detailed statistical scorecards (Form, GW Points, Goals, Assists, Clean Sheets, Minutes, Bonus).
7. **Data Quality & Technical Status**: Secondary expander monitoring database path, last scrape timestamp, dataset health, and automated null/duplicate validation checks.
8. **Graceful Empty & Error States**: Detects missing or empty databases cleanly with instructions to run the extraction pipeline rather than throwing raw Python stack traces.

### 🚀 Launching the Dashboard Locally
```bash
# 1. Ensure the FPL pipeline has extracted and stored records
python -m src.pipeline.fpl_pipeline --save-raw

# 2. Launch the Streamlit application
streamlit run src/dashboard/fpl_dashboard.py
```

---

## 🕒 Historical Snapshot & Pipeline Run Storage (Phase 11)

In Phase 11, the FPL pipeline evolved from an ephemeral current-state overwriting store into an **immutable, append-only historical snapshot repository** while preserving the current-state table for the live dashboard.

### 🏛️ Dual Persistence Architecture
```
                         Official FPL API
                                │
                                ▼
                           FPLPipeline
                                │
                                ▼
                       FPLPlayer Validation
                                │
                     Run ID (e.g. fpl_20261006_083932)
                                │
          ┌─────────────────────┴─────────────────────┐
          │                                           │
          ▼                                           ▼
[ Current State Table ]                     [ Run Audit & Snapshots ]
      fpl_players                                   fpl_runs
 (ON CONFLICT DO UPDATE)                      (execution audit log)
          │                                           │
          ▼                                           ▼
    FPLAnalytics                            fpl_player_snapshots
 (vectorized pandas)                     (append-only immutable store)
          │                                 (UNIQUE on run_id, player_id)
          ▼                                           │
   Streamlit Dashboard                                ▼
 (current-state viewer)                  Future Historical Analytics
                                            & Trend Detection
```

### 🗄️ Relational Schema

#### 1. Pipeline Run Audit Table (`fpl_runs`)
Tracks execution health, record counts, and elapsed duration:
```sql
CREATE TABLE IF NOT EXISTS fpl_runs (
    run_id TEXT PRIMARY KEY,
    scraped_at TEXT NOT NULL,
    source TEXT NOT NULL,
    records_extracted INTEGER NOT NULL DEFAULT 0,
    records_valid INTEGER NOT NULL DEFAULT 0,
    records_invalid INTEGER NOT NULL DEFAULT 0,
    records_persisted INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'started',
    duration_seconds REAL,
    error_message TEXT
);
```

#### 2. Immutable Historical Snapshots (`fpl_player_snapshots`)
Stores complete player statistics per execution run:
```sql
CREATE TABLE IF NOT EXISTS fpl_player_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    player_id INTEGER NOT NULL,
    first_name TEXT NOT NULL,
    second_name TEXT NOT NULL,
    web_name TEXT NOT NULL,
    team TEXT NOT NULL,
    position TEXT NOT NULL,
    price REAL NOT NULL,
    total_points INTEGER NOT NULL,
    event_points INTEGER NOT NULL,
    selected_by_percent REAL NOT NULL,
    goals INTEGER NOT NULL,
    assists INTEGER NOT NULL,
    clean_sheets INTEGER NOT NULL,
    minutes INTEGER NOT NULL,
    bonus INTEGER NOT NULL,
    form REAL NOT NULL,
    status TEXT NOT NULL,
    scraped_at TEXT NOT NULL,
    UNIQUE(run_id, player_id),
    FOREIGN KEY(run_id) REFERENCES fpl_runs(run_id)
);
```

### 🔒 Immutability & Duplicate Protection
- **Append-Only History**: Successive pipeline runs append new player snapshot records under new timestamped `run_id`s without modifying or deleting prior run snapshots.
- **Idempotency**: The `UNIQUE(run_id, player_id)` constraint paired with `INSERT OR IGNORE` ensures pipeline retries or accidental re-executions cannot duplicate data within the same run.
- **Atomic Operations**: `FPLStorage.save_current_and_snapshots()` persists both the current-state upsert and the historical snapshot insert within a single database transaction.

### 🧪 Two-Run Verification
Executing the pipeline sequentially verifies dual persistence and snapshot immutability:
- **Run 1 (`fpl_20261006_083932`)**: Extracted 667 $\to$ `fpl_players` (667) $\to$ `fpl_runs` (1) $\to$ `fpl_player_snapshots` (667).
- **Run 2 (`fpl_20261006_083956`)**: Extracted 667 $\to$ `fpl_players` (667 updated) $\to$ `fpl_runs` (2) $\to$ `fpl_player_snapshots` (1,334 total, 667 per run).
- Prior snapshots from Run 1 remain unaltered, providing a complete historical foundation for future time-series analytics and trend detection.

---

## 📊 Relational Data Analytics (Phase 6)

The [`BookAnalytics`](file:///src/analytics/book_analytics.py) component loads SQLite records into typed Pandas DataFrames and computes business metrics without executing ad-hoc queries across reporting scripts.

### 📈 Metrics & Insights Calculated
1. **Descriptive Statistics**: Total book count, average price, median price, minimum price, maximum price, and average star rating.
2. **Frequency Distributions**:
   - Star rating distribution ($1\dots5$ stars).
   - Stock availability breakdown (`"In stock"`, `"Out of stock"`).
3. **Product Rankings**: Top $N$ most expensive books, bottom $N$ least expensive books, and top-rated books (tie-broken by price).
4. **Data Quality Audit**: Checks for missing prices, unrated records, blank availability strings, duplicate detail URLs, and empty datasets.

### 💻 Running the Analytics CLI
Analyze the local SQLite database and view formatted summary metrics:

```bash
python -m src.analytics.book_analytics

# Run against custom database location
python -m src.analytics.book_analytics --db-path data/processed/books.db
```

---

## 📑 Professional Excel Reporting Layer (Phase 7)

Freelance clients frequently demand polished, spreadsheet deliverables (`.xlsx`) ready for stakeholder presentation rather than raw CSV dumps or command-line logs.

The [`ExcelReport`](file:///src/reporting/excel_report.py) component consumes structured analytics from [`BookAnalytics`](file:///src/analytics/book_analytics.py) and builds an executive, multi-worksheet workbook using `openpyxl`.

### 🗂️ Workbook Structure & Worksheets
1. **Summary**: Executive dashboard with high-level KPI cards (Total Books, Average Price, Median Price, Min/Max Price, Average Rating), data health diagnostics (empty status, missing attributes, duplicate checks), and top 5 price and rating leaderboards.
2. **Books Data**: Clean tabular representation of the raw catalog with freeze panes (`A2`), auto-filters (`A1:G41`), currency number formatting (`£#,##0.00`), date/time formatting, and clickable hyperlinks for detail URLs.
3. **Price Analysis**: Pricing metrics table, top 10 most expensive items, top 10 least expensive items, and an embedded column chart (`openpyxl.chart.BarChart`) comparing prices.
4. **Rating Analysis**: Rating frequency counts ($1\dots5$ stars), share of total percentage formatting (`0.0%`), and a native rating distribution column chart.
5. **Availability**: Inventory breakdown table displaying stock status categories, absolute item counts, and percentage shares.

### 🎨 Design & Formatting Highlights
- **Executive Navy Palette**: Consistent typography (`Segoe UI`), restrained navy headers (`#24426B`), alternating row zebra striping (`#F9FBFC`), and clear borders.
- **Graceful Empty State**: Handles empty databases cleanly without crashing—generates valid sheets indicating `"EMPTY"` status with headers intact and zero fabricated data.
- **Decoupled Architecture**: Reporting only handles Excel presentation; zero web requests, SQL queries, or business calculation duplication.

### 💻 Running the Excel Report Generator CLI
Generate the client deliverable directly:

```bash
# Generate report from default SQLite DB to reports/exports/books_analytics_report.xlsx
python -m src.reporting.excel_report

# Custom input DB and output destination
python -m src.reporting.excel_report \
    --db-path data/processed/books.db \
    --output reports/exports/books_analytics_report.xlsx
```

---

## 📄 Automated PDF Executive Briefing (Phase 8)

For stakeholders requiring a print-ready or attachable business memorandum, the [`PDFReport`](file:///src/reporting/pdf_report.py) component compiles [`BookAnalytics`](file:///src/analytics/book_analytics.py) metrics into a multi-page PDF briefing using `reportlab` Platypus flowables.

### 📑 Document Sections & Layout
- **Page 1: Executive Summary & Scorecard**:
  - Title banner, generation timestamp, and data source metadata.
  - **Dynamic Narrative Insights**: Context-rich English paragraphs computed on-the-fly from analytics metrics (catalog size, price spreads, dominant ratings, stock allocation percentages).
  - **KPI Scorecard**: Styled grid detailing Mean Price, Median Price, Range, Average Rating, and total items.
  - **Quick Highlights Table**: Highlights highest/lowest catalog items and pipeline governance status.
- **Page 2: Price Valuation & Spectrum Analysis**:
  - **Visual Price Chart**: Embedded native ReportLab vector graphic (`Drawing` with horizontal bars) comparing top premium book prices.
  - **Ranked Tables**: Detailed rankings for Top 5 Most Expensive and Top 5 Least Expensive books with automatic title text wrapping.
- **Page 3: Customer Ratings, Inventory & Governance**:
  - **Customer Rating Distribution**: Star rating breakdown ($1\dots5$ stars) with counts, percentage shares, and star icons.
  - **Inventory Allocation Table**: Stock status breakdown with strategic operational interpretations.
  - **Technical Pipeline Quality & Anomaly Report**: Production health audit confirming zero missing prices, valid ratings, and zero duplicate URLs.
- **Header & Footer Pagination**: Two-pass canvas (`NumberedCanvas`) dynamically calculating running headers and `"Page X of Y"` footers with confidentiality markers.

### 💻 Running the PDF Report Generator CLI
Generate the executive PDF report directly:

```bash
# Generate PDF from default SQLite DB to reports/exports/books_analytics_report.pdf
python -m src.reporting.pdf_report

# Custom database input and PDF export destination
python -m src.reporting.pdf_report \
    --db-path data/processed/books.db \
    --output reports/exports/books_analytics_report.pdf
```

*(Note: Interactive web dashboard visualization and automated scheduling via GitHub Actions will follow in subsequent phases.)*

---

## 🗄️ Relational Schema & Persistence (Phase 5)

### SQLite Schema (`books` table)
```sql
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    price REAL NOT NULL,
    rating INTEGER,
    availability TEXT NOT NULL,
    detail_url TEXT NOT NULL UNIQUE,
    scraped_at TEXT NOT NULL
);
```

### 🔄 Duplicate Handling Strategy (Upsert)
To handle repeated pipeline runs over dynamic web targets without generating uncontrolled duplicates, the schema enforces a `UNIQUE` constraint on `detail_url`. 

Records are persisted using SQLite's atomic upsert:
```sql
INSERT INTO books (title, price, rating, availability, detail_url, scraped_at)
VALUES (?, ?, ?, ?, ?, ?)
ON CONFLICT(detail_url) DO UPDATE SET
    title = excluded.title,
    price = excluded.price,
    rating = excluded.rating,
    availability = excluded.availability,
    scraped_at = excluded.scraped_at;
```
If a previously scraped book has a price change or rating update in subsequent runs, the row is updated in-place with the latest information and timestamp rather than duplicated.

---

## 💻 Running the Pipeline CLI

Execute the complete end-to-end pipeline (scrape $\rightarrow$ validate $\rightarrow$ SQLite):

```bash
# Scrape 2 pages, validate, and persist to data/processed/books.db
python -m src.pipeline.book_pipeline --max-pages 2 --save-raw --verbose

# Run with custom database destination
python -m src.pipeline.book_pipeline --max-pages 1 --db-path data/processed/test.db
```

### Sample CLI Output
```text
============================================================
Book Data Pipeline Execution Summary
============================================================
Pages scraped:       2
Records extracted:   40
Valid records:       40
Invalid records:     0
Records persisted:   40
Database:            data/processed/books.db
Raw data run ID:     books_20261006_044537
============================================================
```

---

## 🏗️ Scraping Foundation Architecture

The scraping layer is designed around clean separation of concerns and decoupled responsibilities:

```
┌────────────────────────────────────────────────────────┐
│                      HTTPClient                        │
│   • Configurable timeouts & custom User-Agent          │
│   • Transient retry handling (429, 5xx, timeouts)      │
│   • Structured standard-library logging                │
└──────────────────────────┬─────────────────────────────┘
                           │ fetch(url) -> HTML
                           ▼
┌────────────────────────────────────────────────────────┐
│                      BaseScraper                       │
│   • Enforces standard pipeline lifecycle:              │
│     fetch (URL) -> parse (HTML) -> extract (Data)      │
│   • Completely decoupled from specific websites        │
└─────────────┬────────────────────────────┬─────────────┘
              │                            │
              ▼                            ▼
┌───────────────────────────┐ ┌──────────────────────────┐
│        HTML Parser        │ │ Concrete Scraper Impl    │
│  (BeautifulSoup / DOM)    │ │ (e.g. FPLScraper)        │
│  • Tag extraction helper  │ │ • Domain extraction      │
│  • Typed error handling   │ │ • Yields structured data │
└───────────────────────────┘ └──────────────────────────┘
```

- **[HTTPClient](file:///src/scraper/http_client.py)**: Manages network communication, exponential backoff for transient issues (`429`, `5xx`, connection dropped), and standard logging.
- **[BaseScraper](file:///src/scraper/base_scraper.py)**: Orchestrates the `fetch -> parse -> extract` template method. Concrete scrapers only need to implement the domain-specific `extract(soup)` method.
- **[HTML Parser](file:///src/scraper/parser.py)**: Encapsulates BeautifulSoup interaction and isolates parsing exceptions.
- **[Exceptions](file:///src/scraper/exceptions.py)**: Provides a clean hierarchy (`ScraperError`, `RequestError`, `ParsingError`) avoiding untyped or silent failures.

---

## 📖 First Concrete Scraper: BookScraper

To prove the extensibility of `BaseScraper` and the reliability of `HTTPClient`, a concrete implementation—[`BookScraper`](file:///src/scraper/book_scraper.py)—was developed against a stable, public sandbox.

### 🌐 Source Website
- **Target**: [Books to Scrape](http://books.toscrape.com/)
- **Rationale**: An established, freely accessible web-scraping sandbox specifically maintained for testing extraction pipelines. It requires no authentication or bypass mechanisms and permits respectful automated inspection.

### 🔍 Data Fields Extracted
Each item is normalized into a structured dictionary containing 5 fields:
1. `title` (`str`): Full unclipped book title extracted from the link tag.
2. `price` (`float | None`): Parsed numerical price in GBP (stripped of currency symbols).
3. `rating` (`int | None`): Mapped integer rating on a scale from 1 to 5.
4. `availability` (`str`): Standardized whitespace-clean stock status (e.g. `"In stock"`).
5. `detail_url` (`str`): Fully qualified, absolute URL to the product's detail page.

### 📦 Example Output Structure
```json
{
  "title": "A Light in the Attic",
  "price": 51.77,
  "rating": 3,
  "availability": "In stock",
  "detail_url": "http://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
}
```

### 💻 How to Run It
Run the CLI runner to scrape the catalog, control pagination limits, and optionally preserve raw HTML:

```bash
# Basic run (1 page, in-memory)
python -m src.scraper.book_scraper

# Traverse 3 pages and preserve raw HTML responses
python -m src.scraper.book_scraper --max-pages 3 --save-raw --verbose
```

### 🔄 Pagination & Raw Data Architecture

```
                  Target Website (HTML)
                           │
                           ▼
                      HTTPClient (retries, timeouts, headers)
                           │
                           ▼
                      BookScraper (traverses pagination controls)
                     ┌─────┴────────────────────────┐
                     ▼                              ▼
             Structured Records             Raw HTML Responses
            (clean in-memory dicts)                 │
                                                    ▼
                                          [ RawStorage Component ]
                                                    │
                                                    ▼
                                          data/raw/books/<run_id>/
                                              ├── page_001.html
                                              ├── page_002.html
                                              └── ...
```

### 💾 Why Preserve Raw Data?
In enterprise web-scraping and ETL pipelines, raw HTML preservation provides three critical business safeguards:
1. **Auditability**: Verifies exactly what was visible at scrape time if a client questions a price or record.
2. **Reprocessing Without Re-scraping**: Allows modifying downstream parsers or extracting additional fields without incurring additional network traffic or hitting target rate limits.
3. **Debugging Edge Cases**: Provides exact HTML fixtures when upstream website structure drifts or triggers parsing errors.

### 📁 Raw Data Directory Structure
Saved under `data/raw/<dataset>/<run_id>/` (tracked via `.gitkeep` and excluded in `.gitignore`):
```text
data/raw/
└── books/
    └── books_20261006_041630/
        ├── page_001.html
        └── page_002.html
```

### 🧪 Testing Approach
- **Deterministic Unit Tests**: 
  - [`tests/test_book_scraper.py`](file:///tests/test_book_scraper.py): Multi-record parsing, relative URL normalization, 2-page pagination traversal, max page limits, malformed/missing next links, cyclic pagination loop detection, and raw storage integration with `tmp_path`.
  - [`tests/test_raw_storage.py`](file:///tests/test_raw_storage.py): Run ID timestamp generation, directory creation, UTF-8 multi-page saving, and filesystem error handling.
  - [`tests/test_scraper.py`](file:///tests/test_scraper.py): HTTP client timeouts, retries, and base scraper contracts.
- **Isolated Integration Test**: [`tests/test_integration_scraper.py`](file:///tests/test_integration_scraper.py) tests real extraction against the live site (`-m integration`).

### ⚠️ Limitations & Notes
- Raw HTML is saved as individual UTF-8 files per page.
- Database storage and data transformation/validation (e.g. SQLite and pandas) will be introduced in subsequent phases.

---

## 📊 Dashboard & Reports Preview

<!-- Placeholder for screenshots of generated deliverables -->
*Screenshots and live dashboard links will be added in upcoming phases.*

- **Live Dashboard**: *Coming soon*
- **Sample Excel Report**: *Coming soon*
- **Sample PDF Report**: *Coming soon*

---

## 📝 Portfolio Note

*This repository is built as a portfolio and demonstration project exhibiting production-style software engineering and data automation practices for client engagements.*
