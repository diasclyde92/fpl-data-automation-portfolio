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
- [ ] **Phase 7: Target Analysis & Primary Use Case (FPL)**
  - Concrete domain scraper for FPL statistics, target schemas, and primary data contracts.
- [ ] **Phase 8: Automated Reporting (Excel & PDF)**
  - Client-ready styled Excel spreadsheets and executive summary PDFs.
- [ ] **Phase 9: Web Dashboard Integration**
  - Lightweight visualization layer connected to the pipeline outputs.
- [ ] **Phase 10: Automation & CI/CD Pipeline**
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
