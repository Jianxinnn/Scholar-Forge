from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORD_RE = re.compile(r"[a-z0-9]+")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def stable_hash(value: str, length: int = 16) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return digest[:length]


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def to_plain_data(value: Any) -> Any:
    if is_dataclass(value):
        return {k: to_plain_data(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): to_plain_data(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_plain_data(v) for v in value]
    return value


def dumps_json(value: Any) -> str:
    return json.dumps(to_plain_data(value), ensure_ascii=False, sort_keys=True)


def title_fingerprint(title: str) -> str:
    text = title.lower()
    text = re.sub(r"\bv\d+\b", " ", text)
    text = re.sub(r"\b(a|an|the)\b", " ", text)
    words = WORD_RE.findall(text)
    return " ".join(words)


def tokenize(text: str) -> set[str]:
    words = set(WORD_RE.findall(text.lower()))
    return {w for w in words if len(w) > 2}


def safe_id(prefix: str, *parts: str) -> str:
    joined = "|".join(p for p in parts if p)
    return f"{prefix}_{stable_hash(joined or prefix, 20)}"


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, value: Any) -> None:
    Path(path).write_text(dumps_json(value) + "\n", encoding="utf-8")

