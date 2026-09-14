#!/usr/bin/env python3
"""Build the public, metadata-only database from the private corpus catalog."""

from __future__ import annotations

import csv
import html
import io
import json
import re
import sqlite3
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE = Path("/Users/liwen/Desktop/zz/wechat-research-corpus")
SOURCE_REPOSITORY = "chuanchenge-ship-it/wechat-research-corpus"
PUBLIC_FIELDS = (
    "article_id",
    "research_stream_id",
    "research_stream",
    "publisher_account",
    "publisher_relation",
    "title",
    "published_at",
    "source_url",
    "content_status",
    "quality_status",
    "identity_status",
    "figure_count",
    "normalized_characters",
    "quality_flags",
)
OUTPUT_FIELDS = tuple(field for field in PUBLIC_FIELDS if field != "published_at") + ("published_date",)
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}")


def git_file(path: str) -> str:
    return subprocess.run(
        ["git", "show", f"HEAD:{path}"],
        cwd=PRIVATE,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def jsonl(text: str) -> list[dict]:
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def clean(row: dict) -> dict:
    record = {field: row.get(field) for field in PUBLIC_FIELDS}
    published_at = record.pop("published_at") or ""
    match = DATE_PATTERN.match(published_at)
    record["published_date"] = match.group(0) if match else None
    if "cubox" in (record["identity_status"] or "").lower():
        record["identity_status"] = "verified_from_source"
    record["quality_flags"] = record["quality_flags"] or []
    return record


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=OUTPUT_FIELDS)
    writer.writeheader()
    for row in rows:
        item = dict(row)
        item["quality_flags"] = "|".join(item["quality_flags"])
        writer.writerow(item)
    path.write_text(output.getvalue(), encoding="utf-8-sig")


def write_sqlite(path: Path, rows: list[dict], stats: dict) -> None:
    path.unlink(missing_ok=True)
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE articles (
            article_id TEXT PRIMARY KEY,
            research_stream_id TEXT,
            research_stream TEXT,
            publisher_account TEXT,
            publisher_relation TEXT,
            title TEXT NOT NULL,
            source_url TEXT NOT NULL,
            content_status TEXT NOT NULL,
            quality_status TEXT NOT NULL,
            identity_status TEXT,
            figure_count INTEGER,
            normalized_characters INTEGER,
            quality_flags TEXT NOT NULL,
            published_date TEXT
        );
        CREATE INDEX idx_articles_date ON articles(published_date);
        CREATE INDEX idx_articles_stream ON articles(research_stream_id);
        CREATE INDEX idx_articles_publisher ON articles(publisher_account);
        CREATE INDEX idx_articles_quality ON articles(quality_status);
        CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """
    )
    values = []
    for row in rows:
        item = dict(row)
        item["quality_flags"] = json.dumps(item["quality_flags"], ensure_ascii=False)
        values.append(tuple(item.get(field) for field in OUTPUT_FIELDS))
    placeholders = ",".join("?" for _ in OUTPUT_FIELDS)
    columns = ",".join(OUTPUT_FIELDS)
    connection.executemany(f"INSERT INTO articles ({columns}) VALUES ({placeholders})", values)
    connection.executemany(
        "INSERT INTO metadata (key, value) VALUES (?, ?)",
        ((key, json.dumps(value, ensure_ascii=False)) for key, value in stats.items()),
    )
    connection.commit()
    connection.close()


def main() -> None:
    rows = [clean(row) for row in jsonl(git_file("catalog/v2/articles.jsonl"))]
    rows.sort(key=lambda row: (row["published_date"] is not None, row["published_date"] or "", row["article_id"]), reverse=True)
    source_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=PRIVATE, check=True, capture_output=True, text=True
    ).stdout.strip()
    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    counts = Counter(row["research_stream"] for row in rows)
    status = Counter(row["content_status"] for row in rows)
    dated = [row["published_date"] for row in rows if row["published_date"]]
    years = Counter(date[:4] for date in dated)
    stats = {
        "generated_at": generated,
        "source_repository": SOURCE_REPOSITORY,
        "source_commit": source_commit,
        "article_count": len(rows),
        "figure_count": sum(int(row["figure_count"] or 0) for row in rows),
        "date_min": min(dated),
        "date_max": max(dated),
        "unknown_date_count": len(rows) - len(dated),
        "by_research_stream": dict(sorted(counts.items())),
        "by_content_status": dict(sorted(status.items())),
        "by_year": dict(sorted(years.items())),
        "license": "ODC-By-1.0 (database metadata only)",
    }
    write_jsonl(ROOT / "data" / "articles.jsonl", rows)
    write_csv(ROOT / "data" / "articles.csv", rows)
    (ROOT / "data" / "articles.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    (ROOT / "data" / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    write_sqlite(ROOT / "data" / "articles.sqlite", rows, stats)

    options = "".join(f'<option value="{html.escape(name)}">{html.escape(name)} ({count})</option>' for name, count in sorted(counts.items()))
    page = (ROOT / "docs" / "template.html").read_text(encoding="utf-8")
    page = page.replace("__STATS__", json.dumps(stats, ensure_ascii=False))
    page = page.replace("__ROWS__", json.dumps(rows, ensure_ascii=False).replace("</", "<\\/"))
    page = page.replace("__OPTIONS__", options)
    (ROOT / "index.html").write_text(page, encoding="utf-8")
    print(f"built {len(rows)} articles, {stats['figure_count']} figures from {source_commit[:12]}")


if __name__ == "__main__":
    main()
