from __future__ import annotations

from pathlib import Path

import httpx


def download_pdf(url: str, path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=60, follow_redirects=True, trust_env=False) as client:
        resp = client.get(url)
        resp.raise_for_status()
        p.write_bytes(resp.content)
    return p


def extract_pdf_text(path: str | Path, *, max_pages: int = 12) -> str:
    try:
        import fitz  # type: ignore
    except ImportError as exc:
        raise RuntimeError("PDF reading requires the optional PyMuPDF dependency: pip install 'scholar-forge[pdf]'") from exc

    doc = fitz.open(str(path))
    chunks: list[str] = []
    try:
        for page in doc[:max_pages]:
            chunks.append(page.get_text("text"))
    finally:
        doc.close()
    return "\n\n".join(chunks)
