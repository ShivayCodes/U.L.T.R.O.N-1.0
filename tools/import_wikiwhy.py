#!/usr/bin/env python3
"""Download WikiWhy v1.1 and format compact retrieval passages for ULTRON.

This prepares local search data; it does not train or fine-tune a model.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from urllib.request import Request, urlopen

REVISION = "2739d74043e9e97e53974e9c25b6e9f82f5b71dc"
DATA_URL = (
    "https://raw.githubusercontent.com/matt-seb-ho/WikiWhy/"
    f"{REVISION}/dataset/v1.1"
)
DATASET_SOURCE = f"https://github.com/matt-seb-ho/WikiWhy/tree/{REVISION}/dataset/v1.1"
FILES = {
    "context.json": ("ctx", "title", "topic", "split"),
    "question.json": ("question",),
    "cause.json": ("cause",),
    "effect.json": ("effect",),
    "explanation.json": ("explanation",),
}

# Keep the query and answer-bearing fields intact ahead of optional background.
FIELD_LIMITS = {
    "question": 1_200,
    "cause": 2_000,
    "effect": 2_000,
    "explanation": 6_000,
    "topic": 300,
    "title": 500,
    "ctx": 1_200,
    "split": 30,
}


def _download(path: Path, url: str) -> None:
    request = Request(url, headers={"User-Agent": "ULTRON-WikiWhy-import/1.0"})
    with urlopen(request, timeout=30) as response, path.open("wb") as output:
        output.write(response.read())


def _column_values(payload: object, wanted: tuple[str, ...], filename: str) -> dict[str, list[object]]:
    """Normalize common JSON record and column-oriented layouts."""
    if isinstance(payload, list):
        if not all(isinstance(row, dict) for row in payload):
            raise ValueError(f"Unexpected row format in {filename}")
        return {name: [row.get(name, "") for row in payload] for name in wanted}

    if isinstance(payload, dict):
        # pandas' column-oriented layout: {column: {row_id: value}}.
        if any(name in payload for name in wanted):
            result: dict[str, list[object]] = {}
            for name in wanted:
                values = payload.get(name, [])
                result[name] = (
                    list(values.values()) if isinstance(values, dict)
                    else list(values) if isinstance(values, list)
                    else [values]
                )
            return result

        # Index-oriented records: {row_id: {column: value}}.
        rows = list(payload.values())
        if all(isinstance(row, dict) for row in rows):
            return {name: [row.get(name, "") for row in rows] for name in wanted}

    raise ValueError(f"Unsupported JSON layout in {filename}")


def _bounded(value: object, max_chars: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def format_ultron_passage(record: dict[str, object]) -> str:
    """Make one compact, labeled passage; place the answer before context."""
    labels = (
        ("question", "Question"),
        ("cause", "Cause"),
        ("effect", "Effect"),
        ("explanation", "Explanation"),
        ("topic", "Topic"),
        ("title", "Article"),
        ("ctx", "Context excerpt"),
    )
    parts = ["WikiWhy cause-and-effect example (dataset reference; verify before relying on it)."]
    for key, label in labels:
        value = _bounded(record.get(key, ""), FIELD_LIMITS[key])
        if value:
            parts.append(f"{label}: {value}")
    return "\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("wikiwhy_ultron.csv"))
    parser.add_argument("--cache-dir", type=Path, default=Path(".wikiwhy-cache"))
    parser.add_argument("--limit", type=int, default=5000,
                        help="maximum rows to export (default: 5000; use 0 for all)")
    parser.add_argument("--split", choices=("all", "train", "validation", "test"), default="all",
                        help="optional dataset split filter; default exports all splits")
    args = parser.parse_args()

    if args.limit < 0:
        parser.error("--limit must be zero (unlimited) or a positive integer")
    args.cache_dir.mkdir(parents=True, exist_ok=True)

    columns: dict[str, list[object]] = {}
    for filename, names in FILES.items():
        cached = args.cache_dir / filename
        if not cached.exists():
            _download(cached, f"{DATA_URL}/{filename}")
        with cached.open("r", encoding="utf-8") as source:
            columns.update(_column_values(json.load(source), names, filename))

    lengths = {len(values) for values in columns.values()}
    if len(lengths) != 1:
        raise ValueError(f"WikiWhy files have inconsistent row counts: {sorted(lengths)}")

    row_count = lengths.pop() if lengths else 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with args.output.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=("text", "source"))
        writer.writeheader()
        for index in range(row_count):
            record = {name: values[index] for name, values in columns.items()}
            if args.split != "all" and str(record.get("split", "")).casefold() != args.split:
                continue
            writer.writerow({"text": format_ultron_passage(record), "source": DATASET_SOURCE})
            written += 1
            if args.limit and written >= args.limit:
                break

    print(f"Exported {written} compact WikiWhy passages to {args.output}")
    print("Import with /ingest; this adds retrieval knowledge and does not train a model.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
