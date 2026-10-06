"""Unit tests for the PDFReport generation layer using ReportLab and pypdf."""

from pathlib import Path

import pytest
from pypdf import PdfReader

from src.analytics.book_analytics import BookAnalytics
from src.models.book import Book
from src.reporting.pdf_report import PDFReport
from src.storage.sqlite_storage import SQLiteStorage


@pytest.fixture
def empty_storage(tmp_path: Path) -> SQLiteStorage:
    """Fixture providing a SQLite database with 0 records."""
    return SQLiteStorage(db_path=tmp_path / "empty_pdf.db")


@pytest.fixture
def sample_storage(tmp_path: Path) -> SQLiteStorage:
    """Fixture providing a populated SQLite database with known books."""
    storage = SQLiteStorage(db_path=tmp_path / "sample_pdf.db")
    books = [
        Book(
            title="Design Patterns: Elements of Reusable Object-Oriented Software",
            price=45.50,
            rating=5,
            availability="In stock",
            detail_url="http://books.toscrape.com/patterns",
        ),
        Book(
            title="Clean Code: A Handbook of Agile Software Craftsmanship",
            price=35.00,
            rating=4,
            availability="In stock",
            detail_url="http://books.toscrape.com/clean-code",
        ),
        Book(
            title="Refactoring: Improving the Design of Existing Code",
            price=25.00,
            rating=3,
            availability="In stock",
            detail_url="http://books.toscrape.com/refactoring",
        ),
        Book(
            title="The Pragmatic Programmer",
            price=15.00,
            rating=2,
            availability="Out of stock",
            detail_url="http://books.toscrape.com/pragmatic",
        ),
    ]
    storage.insert_books(books)
    return storage


def test_pdf_report_generation_and_file_non_empty(sample_storage: SQLiteStorage, tmp_path: Path):
    """Verify that PDFReport generates a valid, non-empty PDF file at the expected path."""
    analytics = BookAnalytics(storage=sample_storage)
    report = PDFReport(analytics=analytics)
    output_path = tmp_path / "executive_report.pdf"

    result_path = report.generate(output_path=output_path)

    assert result_path.exists()
    assert result_path.is_file()
    assert result_path.stat().st_size > 1000  # Non-trivial PDF size


def test_pdf_report_page_count_and_headers(sample_storage: SQLiteStorage, tmp_path: Path):
    """Verify generated PDF has exactly 3 pages with proper headers/footers."""
    analytics = BookAnalytics(storage=sample_storage)
    report = PDFReport(analytics=analytics)
    output_path = tmp_path / "three_page_report.pdf"

    report.generate(output_path=output_path)
    reader = PdfReader(str(output_path))

    assert len(reader.pages) == 3

    # Check footer presence on page 1
    page1_text = reader.pages[0].extract_text()
    assert "Page 1 of 3" in page1_text
    assert "Executive Catalog Intelligence Report" in page1_text
    assert "Confidential" in page1_text


def test_pdf_report_contains_summary_kpis(sample_storage: SQLiteStorage, tmp_path: Path):
    """Verify Page 1 extracted text contains key summary figures."""
    analytics = BookAnalytics(storage=sample_storage)
    report = PDFReport(analytics=analytics)
    output_path = tmp_path / "kpi_text.pdf"

    report.generate(output_path=output_path)
    reader = PdfReader(str(output_path))
    page1_text = reader.pages[0].extract_text()

    # Total books = 4
    assert "Total Catalog Items" in page1_text
    assert "4" in page1_text
    # Average Price = (45.5 + 35 + 25 + 15) / 4 = 30.125 -> £30.12
    assert "£30.12" in page1_text
    # Min = £15.00, Max = £45.50
    assert "£15.00" in page1_text
    assert "£45.50" in page1_text
    # Average Rating = (5+4+3+2)/4 = 3.50
    assert "3.50 / 5.0" in page1_text


def test_pdf_report_pricing_rankings_page2(sample_storage: SQLiteStorage, tmp_path: Path):
    """Verify Page 2 contains top and bottom ranked titles."""
    analytics = BookAnalytics(storage=sample_storage)
    report = PDFReport(analytics=analytics)
    output_path = tmp_path / "pricing_page.pdf"

    report.generate(output_path=output_path)
    reader = PdfReader(str(output_path))
    page2_text = reader.pages[1].extract_text()

    assert "Price Valuation & Spectrum Analysis" in page2_text
    assert "Top 5 Most Expensive" in page2_text
    assert "Design Patterns" in page2_text
    assert "£45.50" in page2_text

    assert "Top 5 Least Expensive" in page2_text
    assert "The Pragmatic Programmer" in page2_text
    assert "£15.00" in page2_text


def test_pdf_report_ratings_and_quality_page3(sample_storage: SQLiteStorage, tmp_path: Path):
    """Verify Page 3 contains rating distribution, inventory shares, and quality audit."""
    analytics = BookAnalytics(storage=sample_storage)
    report = PDFReport(analytics=analytics)
    output_path = tmp_path / "page3.pdf"

    report.generate(output_path=output_path)
    reader = PdfReader(str(output_path))
    page3_text = reader.pages[2].extract_text()

    assert "Rating, Inventory & Data Quality Governance" in page3_text
    assert "5 Star Rating" in page3_text
    assert "In stock" in page3_text
    assert "Out of stock" in page3_text
    assert "Technical Pipeline Quality & Anomaly Report" in page3_text
    assert "HEALTHY" in page3_text


def test_pdf_report_empty_database_handling(empty_storage: SQLiteStorage, tmp_path: Path):
    """Verify that empty database generates a valid PDF showing EMPTY status without crashing."""
    analytics = BookAnalytics(storage=empty_storage)
    report = PDFReport(analytics=analytics)
    output_path = tmp_path / "empty_report.pdf"

    result_path = report.generate(output_path=output_path)
    assert result_path.exists()

    reader = PdfReader(str(output_path))
    assert len(reader.pages) == 3

    page1_text = reader.pages[0].extract_text()
    assert "EMPTY" in page1_text
    assert "0 records" in page1_text or "Total Catalog Items 0" in page1_text
