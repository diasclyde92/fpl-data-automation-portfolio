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
- [ ] **Phase 3: Target Analysis & Data Contract**
  - Defining target schemas, extraction scope, and storage models.
- [ ] **Phase 4: Extraction Implementation**
  - Concrete scrapers utilizing the foundation layer with rate limiting and robust error handling.
- [ ] **Phase 5: Transformation, Cleaning & Validation**
  - Data normalization, type checking, anomaly detection, and SQLite persistence.
- [ ] **Phase 6: Automated Reporting (Excel & PDF)**
  - Client-ready styled Excel spreadsheets and executive summary PDFs.
- [ ] **Phase 7: Web Dashboard Integration**
  - Lightweight visualization layer connected to the pipeline outputs.
- [ ] **Phase 8: Automation & CI/CD Pipeline**
  - GitHub Actions workflow for scheduled headless execution and artifact archiving.

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

## 📊 Dashboard & Reports Preview

<!-- Placeholder for screenshots of generated deliverables -->
*Screenshots and live dashboard links will be added in upcoming phases.*

- **Live Dashboard**: *Coming soon*
- **Sample Excel Report**: *Coming soon*
- **Sample PDF Report**: *Coming soon*

---

## 📝 Portfolio Note

*This repository is built as a portfolio and demonstration project exhibiting production-style software engineering and data automation practices for client engagements.*
