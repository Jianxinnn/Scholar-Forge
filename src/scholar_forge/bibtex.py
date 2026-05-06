from __future__ import annotations

import re

from .models import SourceRecord, TriageRecord


def _cite_key(source: SourceRecord) -> str:
    author = "source"
    if source.authors:
        author = re.sub(r"[^A-Za-z0-9]", "", source.authors[0].split()[-1]) or "source"
    year = str(source.year or "nd")
    title_word = "paper"
    for word in re.findall(r"[A-Za-z0-9]+", source.title):
        if len(word) > 3:
            title_word = word
            break
    return f"{author}{year}{title_word}"


def write_references(sources: list[SourceRecord], triage: list[TriageRecord]) -> str:
    included = {row.source_id for row in triage if row.decision == "include"}
    entries: list[str] = []
    used: set[str] = set()
    for source in sources:
        if source.source_id not in included:
            continue
        key = _cite_key(source)
        base = key
        suffix = 2
        while key in used:
            key = f"{base}{suffix}"
            suffix += 1
        used.add(key)
        fields = {
            "title": source.title,
            "author": " and ".join(source.authors),
            "year": str(source.year or ""),
            "journal": source.venue,
            "doi": source.doi,
            "url": source.url or source.pdf_url,
        }
        body = []
        for name, value in fields.items():
            if value:
                body.append(f"  {name} = {{{value}}}")
        entry_type = "article" if source.venue else "misc"
        entries.append(f"@{entry_type}{{{key},\n" + ",\n".join(body) + "\n}")
    return "\n\n".join(entries) + ("\n" if entries else "")

