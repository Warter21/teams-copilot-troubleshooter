from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from typing import Any

import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from teams_copilot_troubleshooter.config import MANIFEST_PATH, SNAPSHOT_PATH  # noqa: E402

ALLOWED_HOSTS = {"support.microsoft.com", "learn.microsoft.com"}
CONTENT_TAGS = {"p", "li", "td", "th"}
HEADING_TAGS = {"h1", "h2", "h3", "h4"}


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def extract_chunks(html: str, source: dict[str, Any], retrieved_at: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style", "nav", "footer", "header", "aside", "button", "noscript"]):
        element.decompose()
    main = soup.find("main") or soup.find("article") or soup.body or soup
    sections: list[tuple[str, list[str]]] = []
    current_heading = source["title"]
    current_paragraphs: list[str] = []
    for element in main.find_all(list(HEADING_TAGS | CONTENT_TAGS)):
        tag = element.name.lower()
        text = clean_text(element.get_text(" ", strip=True))
        if not text:
            continue
        if tag in HEADING_TAGS:
            if current_paragraphs:
                sections.append((current_heading, current_paragraphs))
                current_paragraphs = []
            current_heading = text
        elif text not in current_paragraphs:
            current_paragraphs.append(text)
    if current_paragraphs:
        sections.append((current_heading, current_paragraphs))

    output: list[dict[str, Any]] = []
    chunk_number = 0
    for heading, paragraphs in sections:
        group: list[str] = []
        chars = 0
        for paragraph in paragraphs:
            if group and chars + len(paragraph) > 1800:
                chunk_number += 1
                output.append(
                    _make_chunk(source, heading, group, chunk_number, retrieved_at)
                )
                group, chars = [], 0
            group.append(paragraph)
            chars += len(paragraph)
        if group:
            chunk_number += 1
            output.append(_make_chunk(source, heading, group, chunk_number, retrieved_at))
    return output


def _make_chunk(
    source: dict[str, Any],
    heading: str,
    paragraphs: list[str],
    chunk_number: int,
    retrieved_at: str,
) -> dict[str, Any]:
    return {
        "id": f"{source['source_id']}-web-{chunk_number}",
        "source_id": source["source_id"],
        "title": source["title"],
        "source_url": source["url"],
        "source_type": source["source_type"],
        "area": source["area"],
        "section": heading,
        "text": " ".join(paragraphs),
        "retrieved_at": retrieved_at,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refresh an uncommitted local snapshot of the allowlisted Microsoft pages."
    )
    parser.add_argument("--timeout", type=float, default=25.0)
    args = parser.parse_args()

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    retrieved_at = datetime.now(timezone.utc).isoformat()
    all_chunks: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    with httpx.Client(
        timeout=args.timeout,
        follow_redirects=True,
        headers={"User-Agent": "TeamsCopilotTroubleshooter/0.1 (documentation refresh)"},
    ) as client:
        for source in manifest:
            host = urlparse(source["url"]).hostname or ""
            if host not in ALLOWED_HOSTS:
                failures.append({"source_id": source["source_id"], "error": "Host is not allowlisted."})
                continue
            try:
                response = client.get(source["url"])
                response.raise_for_status()
                chunks = extract_chunks(response.text, source, retrieved_at)
                if not chunks:
                    raise ValueError("No readable article sections were extracted.")
                digest = hashlib.sha256(response.content).hexdigest()
                for chunk in chunks:
                    chunk["source_sha256"] = digest
                all_chunks.extend(chunks)
                print(f"{source['source_id']}: extracted {len(chunks)} chunks")
            except Exception as exc:
                failures.append({"source_id": source["source_id"], "error": str(exc)})
                print(f"{source['source_id']}: failed: {exc}")

    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SNAPSHOT_PATH.open("w", encoding="utf-8") as stream:
        for chunk in all_chunks:
            stream.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    print(f"Saved {len(all_chunks)} local chunks to {SNAPSHOT_PATH}")
    if failures:
        print(json.dumps({"failed_sources": failures}, indent=2))
    return 1 if not all_chunks else 0


if __name__ == "__main__":
    raise SystemExit(main())
