"""Text/Markdown parser tests."""

from pathlib import Path

from docheck.services.parsers import text


def test_parses_text_into_chunks(tmp_path: Path) -> None:
    f = tmp_path / "sample.md"
    f.write_text("\n".join(f"Line {i}" for i in range(120)), encoding="utf-8")
    chunks = text.parse(f)
    assert len(chunks) == 3  # 40 lines per chunk
    assert chunks[0].line_start == 1
    assert chunks[0].line_end == 40
    assert chunks[2].line_end == 120
    assert all(c.text for c in chunks)


def test_empty_file_returns_one_chunk(tmp_path: Path) -> None:
    f = tmp_path / "empty.txt"
    f.write_text("", encoding="utf-8")
    chunks = text.parse(f)
    assert len(chunks) == 1
