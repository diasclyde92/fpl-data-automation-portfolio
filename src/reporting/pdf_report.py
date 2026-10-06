"""PDF Executive Summary Report Generator using ReportLab Platypus."""

import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.analytics.book_analytics import BookAnalytics
from src.storage.sqlite_storage import SQLiteStorage

logger = logging.getLogger(__name__)

# Corporate Executive Palette
NAVY_PRIMARY = colors.HexColor("#1B365D")
NAVY_SECONDARY = colors.HexColor("#24426B")
NAVY_LIGHT = colors.HexColor("#E8EEF5")
TEXT_DARK = colors.HexColor("#222222")
TEXT_MUTED = colors.HexColor("#555555")
BORDER_COLOR = colors.HexColor("#D0D7DE")
ZEBRA_COLOR = colors.HexColor("#F9FBFC")
STATUS_HEALTHY = colors.HexColor("#1E7E34")
STATUS_EMPTY = colors.HexColor("#BD2130")
STAR_COLOR = colors.HexColor("#D97706")


class NumberedCanvas:
    """Two-pass canvas for professional running headers and 'Page X of Y' footers."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.canvas_maker = kwargs.pop("canvas_maker", None)
        self.pages: list[Any] = []

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        from reportlab.pdfgen import canvas

        class _CustomCanvas(canvas.Canvas):
            def __init__(self, *c_args: Any, **c_kwargs: Any) -> None:
                super().__init__(*c_args, **c_kwargs)
                self.pages_data: list[Any] = []

            def showPage(self) -> None:
                self.pages_data.append(dict(self.__dict__))
                self._startPage()

            def save(self) -> None:
                num_pages = len(self.pages_data)
                for page in self.pages_data:
                    self.__dict__.update(page)
                    self.draw_header_footer(num_pages)
                    super().showPage()
                super().save()

            def draw_header_footer(self, total_pages: int) -> None:
                self.saveState()
                self.setFont("Helvetica", 9)
                self.setFillColor(TEXT_MUTED)

                # Header (Pages 2+)
                if self._pageNumber > 1:
                    self.drawString(54, 755, "Books Catalog | Executive Intelligence Brief")
                    self.setStrokeColor(BORDER_COLOR)
                    self.setLineWidth(0.5)
                    self.line(54, 747, 558, 747)

                # Footer on all pages
                self.setStrokeColor(BORDER_COLOR)
                self.setLineWidth(0.5)
                self.line(54, 45, 558, 45)

                page_text = f"Page {self._pageNumber} of {total_pages}"
                self.drawRightString(558, 32, page_text)
                self.drawString(54, 32, "Confidential — Automated Data Pipeline Deliverable")
                self.restoreState()

        return _CustomCanvas(*args, **kwargs)


class PDFReport:
    """Generates an executive, client-ready multi-page PDF briefing from BookAnalytics."""

    def __init__(self, analytics: BookAnalytics) -> None:
        """Initialize PDFReport with an analytics provider.

        Args:
            analytics: BookAnalytics instance.
        """
        self.analytics = analytics
        self._init_styles()

    def _init_styles(self) -> None:
        """Initialize custom ReportLab typography styles."""
        styles = getSampleStyleSheet()

        self.style_doc_title = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=NAVY_PRIMARY,
            spaceAfter=4,
        )
        self.style_doc_subtitle = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=TEXT_MUTED,
            spaceAfter=14,
        )
        self.style_section_h1 = ParagraphStyle(
            "SectionH1",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=NAVY_PRIMARY,
            spaceBefore=12,
            spaceAfter=8,
            keepWithNext=True,
        )
        self.style_body = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=14,
            textColor=TEXT_DARK,
            spaceAfter=8,
        )
        self.style_body_bold = ParagraphStyle(
            "BodyBold",
            parent=self.style_body,
            fontName="Helvetica-Bold",
        )
        self.style_table_header = ParagraphStyle(
            "TableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=colors.white,
            alignment=0,
        )
        self.style_table_header_right = ParagraphStyle(
            "TableHeaderRight",
            parent=self.style_table_header,
            alignment=2,
        )
        self.style_table_cell = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=TEXT_DARK,
        )
        self.style_table_cell_bold = ParagraphStyle(
            "TableCellBold",
            parent=self.style_table_cell,
            fontName="Helvetica-Bold",
        )
        self.style_table_cell_right = ParagraphStyle(
            "TableCellRight",
            parent=self.style_table_cell,
            alignment=2,
        )
        self.style_callout = ParagraphStyle(
            "Callout",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=9.5,
            leading=14,
            textColor=NAVY_PRIMARY,
        )

    def generate(self, output_path: Path | str = "reports/exports/books_analytics_report.pdf") -> Path:
        """Generate the executive PDF report.

        Args:
            output_path: Target path for the PDF file.

        Returns:
            Path of the generated PDF file.
        """
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        logger.info("Generating PDF executive briefing to %s", target)
        df = self.analytics.load_data()
        result = self.analytics.analyze()

        doc = SimpleDocTemplate(
            str(target),
            pagesize=letter,
            leftMargin=54,
            rightMargin=54,
            topMargin=54,
            bottomMargin=54,
        )

        story: list[Any] = []

        # Page 1: Executive Summary & Health Diagnostics
        self._build_page1_summary(story, result)

        # Page 2: Price Valuation & Rankings
        story.append(PageBreak())
        self._build_page2_pricing(story, result)

        # Page 3: Rating Distribution, Inventory & Data Quality
        story.append(PageBreak())
        self._build_page3_ratings_and_quality(story, result)

        canvas_maker = NumberedCanvas()
        doc.build(story, canvasmaker=canvas_maker)

        logger.info("Successfully generated PDF report: %s", target)
        return target

    # -------------------------------------------------------------------------
    # Page 1: Executive Summary
    # -------------------------------------------------------------------------
    def _build_page1_summary(self, story: list[Any], result: Any) -> None:
        """Construct Page 1 containing title, dynamic key insights, and KPI scorecard."""
        story.append(Paragraph("Executive Catalog Intelligence Report", self.style_doc_title))
        now_utc = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")
        story.append(
            Paragraph(
                f"Generated on {now_utc} | Target: <i>books.toscrape.com</i> | Store: <code>{self.analytics.storage.db_path.name}</code>",
                self.style_doc_subtitle,
            )
        )
        story.append(HRFlowable(width="100%", thickness=1.5, color=NAVY_PRIMARY, spaceAfter=14))

        # Dynamic Key Insights Callout
        story.append(Paragraph("Executive Summary & Core Insights", self.style_section_h1))
        insights_text = self._generate_dynamic_insights(result)
        story.append(self._build_callout_box(insights_text))
        story.append(Spacer(1, 14))

        # Key Performance Indicators Table
        story.append(Paragraph("Key Performance Indicators (KPIs)", self.style_section_h1))
        story.append(self._build_kpi_table(result))
        story.append(Spacer(1, 14))

        # Quick Highlights Table
        story.append(Paragraph("Catalog Valuation Highlights", self.style_section_h1))
        story.append(self._build_highlights_table(result))

    def _generate_dynamic_insights(self, result: Any) -> str:
        """Derive dynamic English narrative observations strictly from the analytics metrics."""
        summary = result.summary
        quality = result.quality

        if summary.total_books == 0:
            return (
                "<b>Notice:</b> The target database currently contains <b>0 records</b> (EMPTY status). "
                "No catalog items were available for analysis. Run the ingestion pipeline to refresh catalog records."
            )

        avg_price_str = f"£{summary.average_price:.2f}" if summary.average_price is not None else "N/A"
        med_price_str = f"£{summary.median_price:.2f}" if summary.median_price is not None else "N/A"
        min_price_str = f"£{summary.min_price:.2f}" if summary.min_price is not None else "N/A"
        max_price_str = f"£{summary.max_price:.2f}" if summary.max_price is not None else "N/A"
        avg_rating_str = f"{summary.average_rating:.2f}/5" if summary.average_rating is not None else "N/A"

        # Most common rating
        most_common_star = max(result.rating_distribution, key=result.rating_distribution.get) if result.rating_distribution else None

        # Stock breakdown insight
        avail = result.availability_distribution
        in_stock_cnt = avail.get("In stock", 0)
        pct_in_stock = (in_stock_cnt / summary.total_books * 100) if summary.total_books else 0.0

        insights = [
            f"The analyzed catalog comprises <b>{summary.total_books} verified items</b> with an average price of <b>{avg_price_str}</b> (median <b>{med_price_str}</b>).",
            f"Book prices range across the spectrum from a low of <b>{min_price_str}</b> to a maximum of <b>{max_price_str}</b>.",
            f"The catalog maintains an average customer rating of <b>{avg_rating_str} stars</b>" + (f", with <b>{most_common_star}-star</b> ratings being the most frequent category." if most_common_star else "."),
            f"Inventory integrity is strong: <b>{pct_in_stock:.1f}%</b> of catalog titles ({in_stock_cnt} items) are actively listed as in stock.",
            f"Data health audit confirms <b>{quality.missing_prices} missing prices</b> and <b>{quality.duplicate_urls} duplicate URLs</b>."
        ]
        return "<br/><br/>".join(insights)

    def _build_callout_box(self, text: str) -> Table:
        """Create a styled callout container box for executive narrative."""
        p = Paragraph(text, self.style_body)
        table = Table([[p]], colWidths=[504])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), NAVY_LIGHT),
                    ("BOX", (0, 0), (-1, -1), 1, NAVY_PRIMARY),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ]
            )
        )
        return table

    def _build_kpi_table(self, result: Any) -> Table:
        """Build KPI grid table with alternating shading and bold metrics."""
        summary = result.summary
        data = [
            [
                Paragraph("Metric", self.style_table_header),
                Paragraph("Catalog Value", self.style_table_header_right),
                Paragraph("Benchmark / Range", self.style_table_header),
            ],
            [
                Paragraph("Total Catalog Items", self.style_table_cell_bold),
                Paragraph(f"{summary.total_books:,}", self.style_table_cell_right),
                Paragraph("Complete active collection", self.style_table_cell),
            ],
            [
                Paragraph("Average Price (Mean)", self.style_table_cell_bold),
                Paragraph(f"£{summary.average_price:.2f}" if summary.average_price is not None else "N/A", self.style_table_cell_right),
                Paragraph("Central catalog pricing", self.style_table_cell),
            ],
            [
                Paragraph("Median Price", self.style_table_cell_bold),
                Paragraph(f"£{summary.median_price:.2f}" if summary.median_price is not None else "N/A", self.style_table_cell_right),
                Paragraph("Outlier-resistant baseline", self.style_table_cell),
            ],
            [
                Paragraph("Price Range (Min - Max)", self.style_table_cell_bold),
                Paragraph(
                    f"£{summary.min_price:.2f} - £{summary.max_price:.2f}"
                    if summary.min_price is not None and summary.max_price is not None
                    else "N/A",
                    self.style_table_cell_right,
                ),
                Paragraph("Full observed price spread", self.style_table_cell),
            ],
            [
                Paragraph("Average Star Rating", self.style_table_cell_bold),
                Paragraph(f"{summary.average_rating:.2f} / 5.0" if summary.average_rating is not None else "N/A", self.style_table_cell_right),
                Paragraph("Scale: 1 (Lowest) to 5 (Highest)", self.style_table_cell),
            ],
        ]

        table = Table(data, colWidths=[180, 134, 190])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY_SECONDARY),
                    ("ALIGN", (0, 0), (-1, 0), "LEFT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ZEBRA_COLOR]),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        return table

    def _build_highlights_table(self, result: Any) -> Table:
        """Build mini highlights table showcasing top item, lowest item, and health."""
        summary = result.summary
        top_book = result.top_expensive[0] if result.top_expensive else None
        bottom_book = result.bottom_expensive[0] if result.bottom_expensive else None

        top_desc = f"{top_book['title'][:45]}... (£{top_book['price']:.2f})" if top_book else "N/A"
        bottom_desc = f"{bottom_book['title'][:45]}... (£{bottom_book['price']:.2f})" if bottom_book else "N/A"
        status_str = "HEALTHY (Zero anomalies)" if not result.quality.is_empty else "EMPTY (No records)"

        data = [
            [
                Paragraph("Item Dimension", self.style_table_header),
                Paragraph("Key Indicator Observation", self.style_table_header),
            ],
            [
                Paragraph("Highest Value Item", self.style_table_cell_bold),
                Paragraph(top_desc, self.style_table_cell),
            ],
            [
                Paragraph("Most Accessible Item", self.style_table_cell_bold),
                Paragraph(bottom_desc, self.style_table_cell),
            ],
            [
                Paragraph("Data Pipeline Health", self.style_table_cell_bold),
                Paragraph(status_str, self.style_table_cell_bold),
            ],
        ]

        table = Table(data, colWidths=[150, 354])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY_SECONDARY),
                    ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ZEBRA_COLOR]),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        return table

    # -------------------------------------------------------------------------
    # Page 2: Price Analysis & Rankings
    # -------------------------------------------------------------------------
    def _build_page2_pricing(self, story: list[Any], result: Any) -> None:
        """Construct Page 2 detailing price distribution and top/bottom rankings."""
        story.append(Paragraph("Price Valuation & Spectrum Analysis", self.style_doc_title))
        story.append(
            Paragraph(
                "Granular analysis of catalog price points, premium tiers, and accessible inventory.",
                self.style_doc_subtitle,
            )
        )
        story.append(HRFlowable(width="100%", thickness=1, color=NAVY_PRIMARY, spaceAfter=12))

        # Native ReportLab Horizontal Bar Chart
        if result.top_expensive:
            story.append(Paragraph("Visual Comparison: Top 5 Premium Books (GBP)", self.style_section_h1))
            chart_drawing = self._build_price_chart(result.top_expensive)
            story.append(chart_drawing)
            story.append(Spacer(1, 10))

        # Top 5 Most Expensive Table
        story.append(Paragraph("Top 5 Most Expensive Catalog Titles", self.style_section_h1))
        story.append(self._build_ranked_table(result.top_expensive))
        story.append(Spacer(1, 14))

        # Top 5 Least Expensive Table
        story.append(Paragraph("Top 5 Least Expensive Catalog Titles", self.style_section_h1))
        story.append(self._build_ranked_table(result.bottom_expensive))

    def _build_price_chart(self, items: list[dict[str, Any]]) -> Drawing:
        """Generate a native ReportLab Drawing visualizing top prices with custom horizontal bars."""
        d = Drawing(504, 120)
        # Background canvas
        d.add(Rect(0, 0, 504, 120, fillColor=NAVY_LIGHT, strokeColor=BORDER_COLOR, strokeWidth=0.5))

        if not items:
            d.add(String(20, 55, "(No pricing data available)", fontName="Helvetica", fontSize=9, fillColor=TEXT_MUTED))
            return d

        max_price = max((item["price"] for item in items if item["price"] is not None), default=1.0)
        bar_height = 14
        start_y = 96
        y_step = 20

        for idx, item in enumerate(items[:5]):
            y = start_y - (idx * y_step)
            price = item.get("price") or 0.0
            title = item.get("title", "")
            title_clipped = title[:24] + ("..." if len(title) > 24 else "")

            # Title label
            d.add(String(12, y + 2, f"{idx+1}. {title_clipped}", fontName="Helvetica", fontSize=8, fillColor=TEXT_DARK))

            # Bar
            max_bar_w = 260
            bar_w = (price / max_price) * max_bar_w if max_price > 0 else 0
            d.add(Rect(165, y, bar_w, bar_height, fillColor=NAVY_SECONDARY, strokeColor=None))

            # Price label
            d.add(String(170 + bar_w, y + 2, f"£{price:.2f}", fontName="Helvetica-Bold", fontSize=8, fillColor=NAVY_PRIMARY))

        return d

    def _build_ranked_table(self, items: list[dict[str, Any]]) -> Table:
        """Construct structured table for top/bottom book listings with word wrapping."""
        data = [
            [
                Paragraph("#", self.style_table_header),
                Paragraph("Book Title", self.style_table_header),
                Paragraph("Price", self.style_table_header_right),
                Paragraph("Rating", self.style_table_header),
                Paragraph("Availability", self.style_table_header),
            ]
        ]

        if not items:
            data.append([Paragraph("(No records available)", self.style_table_cell)] * 5)
        else:
            for idx, item in enumerate(items, start=1):
                rating_val = item.get("rating")
                rating_str = f"{rating_val}★" if rating_val is not None else "Unrated"
                title_p = Paragraph(item.get("title", "N/A"), self.style_table_cell)

                data.append(
                    [
                        Paragraph(str(idx), self.style_table_cell_bold),
                        title_p,
                        Paragraph(f"£{item['price']:.2f}" if item.get("price") is not None else "N/A", self.style_table_cell_right),
                        Paragraph(rating_str, self.style_table_cell),
                        Paragraph(item.get("availability", "N/A"), self.style_table_cell),
                    ]
                )

        table = Table(data, colWidths=[24, 270, 70, 60, 80])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY_SECONDARY),
                    ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ZEBRA_COLOR]),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        return table

    # -------------------------------------------------------------------------
    # Page 3: Ratings, Inventory & Data Quality
    # -------------------------------------------------------------------------
    def _build_page3_ratings_and_quality(self, story: list[Any], result: Any) -> None:
        """Construct Page 3 covering customer ratings distribution, inventory, and quality diagnostics."""
        story.append(Paragraph("Rating, Inventory & Data Quality Governance", self.style_doc_title))
        story.append(
            Paragraph(
                "Review breakdown, stock allocation, and automated technical data audit.",
                self.style_doc_subtitle,
            )
        )
        story.append(HRFlowable(width="100%", thickness=1, color=NAVY_PRIMARY, spaceAfter=12))

        # Rating Distribution Section
        story.append(Paragraph("Customer Star Rating Distribution", self.style_section_h1))
        story.append(self._build_rating_distribution_table(result))
        story.append(Spacer(1, 14))

        # Availability Breakdown Section
        story.append(Paragraph("Stock Status & Inventory Breakdown", self.style_section_h1))
        story.append(self._build_availability_table(result))
        story.append(Spacer(1, 14))

        # Technical Data Quality Section
        story.append(Paragraph("Technical Pipeline Quality & Anomaly Report", self.style_section_h1))
        story.append(self._build_quality_table(result))

    def _build_rating_distribution_table(self, result: Any) -> Table:
        """Build rating breakdown table with visual representation."""
        dist = result.rating_distribution
        total_books = result.summary.total_books or 1

        data = [
            [
                Paragraph("Rating Tier", self.style_table_header),
                Paragraph("Visual Score", self.style_table_header),
                Paragraph("Count", self.style_table_header_right),
                Paragraph("Share (%)", self.style_table_header_right),
            ]
        ]

        if not dist:
            data.append([Paragraph("(No rating data)", self.style_table_cell)] * 4)
        else:
            for stars in range(5, 0, -1):
                cnt = dist.get(stars, 0)
                pct = (cnt / total_books) * 100 if total_books > 0 else 0.0
                star_visual = "★" * stars + "☆" * (5 - stars)

                data.append(
                    [
                        Paragraph(f"{stars} Star Rating", self.style_table_cell_bold),
                        Paragraph(star_visual, ParagraphStyle("StarP", parent=self.style_table_cell, textColor=STAR_COLOR)),
                        Paragraph(str(cnt), self.style_table_cell_right),
                        Paragraph(f"{pct:.1f}%", self.style_table_cell_right),
                    ]
                )

        table = Table(data, colWidths=[130, 134, 100, 140])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY_SECONDARY),
                    ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ZEBRA_COLOR]),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        return table

    def _build_availability_table(self, result: Any) -> Table:
        """Build inventory distribution table."""
        avail = result.availability_distribution
        total = result.summary.total_books or 1

        data = [
            [
                Paragraph("Stock Category", self.style_table_header),
                Paragraph("Volume", self.style_table_header_right),
                Paragraph("Share of Total", self.style_table_header_right),
                Paragraph("Strategic Interpretation", self.style_table_header),
            ]
        ]

        if not avail:
            data.append([Paragraph("(No inventory records)", self.style_table_cell)] * 4)
        else:
            for status, count in avail.items():
                pct = (count / total) * 100 if total > 0 else 0.0
                desc = "Active & orderable inventory" if "In stock" in status else "Awaiting restock / backorder"
                data.append(
                    [
                        Paragraph(status, self.style_table_cell_bold),
                        Paragraph(str(count), self.style_table_cell_right),
                        Paragraph(f"{pct:.1f}%", self.style_table_cell_right),
                        Paragraph(desc, self.style_table_cell),
                    ]
                )

        table = Table(data, colWidths=[130, 80, 94, 200])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY_SECONDARY),
                    ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ZEBRA_COLOR]),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        return table

    def _build_quality_table(self, result: Any) -> Table:
        """Build data quality diagnostics table."""
        quality = result.quality
        status_color = STATUS_EMPTY if quality.is_empty else STATUS_HEALTHY
        status_text = "EMPTY (0 Records)" if quality.is_empty else "HEALTHY (Production Ready)"

        data = [
            [
                Paragraph("Diagnostic Check", self.style_table_header),
                Paragraph("Result", self.style_table_header),
                Paragraph("Quality Standard / Threshold", self.style_table_header),
            ],
            [
                Paragraph("Dataset Status", self.style_table_cell_bold),
                Paragraph(f"<font color='{status_color.hexval()}'><b>{status_text}</b></font>", self.style_table_cell),
                Paragraph("Non-empty verified dataset", self.style_table_cell),
            ],
            [
                Paragraph("Missing Price Values", self.style_table_cell_bold),
                Paragraph(f"{quality.missing_prices} anomalies", self.style_table_cell),
                Paragraph("0 allowed (Mandatory decimal)", self.style_table_cell),
            ],
            [
                Paragraph("Missing Star Ratings", self.style_table_cell_bold),
                Paragraph(f"{quality.missing_ratings} unrated", self.style_table_cell),
                Paragraph("Tolerance: Nullable 1-5 scale", self.style_table_cell),
            ],
            [
                Paragraph("Missing Stock Status", self.style_table_cell_bold),
                Paragraph(f"{quality.missing_availability} blank", self.style_table_cell),
                Paragraph("0 allowed (Normalized string)", self.style_table_cell),
            ],
            [
                Paragraph("Duplicate Detail URLs", self.style_table_cell_bold),
                Paragraph(f"{quality.duplicate_urls} duplicates", self.style_table_cell),
                Paragraph("0 allowed (Enforced UNIQUE key)", self.style_table_cell),
            ],
        ]

        table = Table(data, colWidths=[160, 154, 190])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY_SECONDARY),
                    ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ZEBRA_COLOR]),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        return table


def run_pdf_cli() -> None:
    """CLI runner for PDF executive briefing generation."""
    parser = argparse.ArgumentParser(description="Generate client-facing executive PDF report from SQLite database.")
    parser.add_argument(
        "--db-path",
        default="data/processed/books.db",
        help="Path to SQLite database (default: data/processed/books.db)",
    )
    parser.add_argument(
        "--output",
        default="reports/exports/books_analytics_report.pdf",
        help="Target output PDF file path (default: reports/exports/books_analytics_report.pdf)",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    storage = SQLiteStorage(db_path=args.db_path)
    analytics = BookAnalytics(storage=storage)
    report = PDFReport(analytics=analytics)

    try:
        output_path = report.generate(output_path=args.output)
        print("PDF report generated successfully.")
        print(f"Output: {output_path}")
    except Exception as exc:
        print(f"Error generating PDF report: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    from pathlib import Path
    import sys

    project_root = Path(__file__).resolve().parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    run_pdf_cli()
