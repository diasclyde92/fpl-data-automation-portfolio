"""Unit tests for RawStorage component."""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.storage.raw_storage import RawStorage


def test_generate_run_id_format():
    """Verify run ID generation with and without prefix."""
    storage = RawStorage()
    run_id_no_prefix = storage.generate_run_id()
    assert len(run_id_no_prefix) == 15  # YYYYMMDD_HHMMSS

    run_id_prefixed = storage.generate_run_id(prefix="books")
    assert run_id_prefixed.startswith("books_")
    assert len(run_id_prefixed) == 21


def test_save_page_success(tmp_path: Path):
    """Verify saving a single raw HTML page with proper directory creation."""
    storage = RawStorage(base_dir=tmp_path)
    html_content = "<html><body><h1>Test Page</h1></body></html>"

    saved_path = storage.save_page(
        dataset="test_data",
        run_id="run_001",
        page_number=1,
        html_content=html_content,
    )

    assert saved_path.exists()
    assert saved_path.parent == tmp_path / "test_data" / "run_001"
    assert saved_path.name == "page_001.html"
    assert saved_path.read_text(encoding="utf-8") == html_content


def test_save_multiple_pages_utf8(tmp_path: Path):
    """Verify preserving multiple pages with UTF-8 non-ASCII characters."""
    storage = RawStorage(base_dir=tmp_path)
    run_id = "run_utf8"

    page1 = "<html><body><p>Price: £51.77</p></body></html>"
    page2 = "<html><body><p>Special: Soumission — Émile Zola</p></body></html>"

    path1 = storage.save_page("books", run_id, 1, page1)
    path2 = storage.save_page("books", run_id, 2, page2)

    assert path1.name == "page_001.html"
    assert path2.name == "page_002.html"
    assert "£" in path1.read_text(encoding="utf-8")
    assert "Émile" in path2.read_text(encoding="utf-8")


def test_save_page_handles_os_error(tmp_path: Path):
    """Verify that filesystem write failures raise OSError properly."""
    storage = RawStorage(base_dir=tmp_path)

    with patch.object(Path, "write_text", side_effect=OSError("Disk full")):
        with pytest.raises(OSError):
            storage.save_page("books", "run_fail", 1, "<html></html>")
