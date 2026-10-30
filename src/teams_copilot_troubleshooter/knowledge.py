from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .config import CARDS_PATH, HUNGARIAN_CARDS_PATH, MANIFEST_PATH, SNAPSHOT_PATH


def normalize_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "")
    return text.strip()


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, dict[str, Any]]:
    items = json.loads(path.read_text(encoding="utf-8"))
    return {item["source_id"]: item for item in items}


def load_knowledge_cards(
    cards_path: Path = CARDS_PATH,
    snapshot_path: Path = SNAPSHOT_PATH,
    manifest_path: Path = MANIFEST_PATH,
) -> list[dict[str, Any]]:
    manifest = load_manifest(manifest_path)
    translations = (
        json.loads(HUNGARIAN_CARDS_PATH.read_text(encoding="utf-8"))
        if HUNGARIAN_CARDS_PATH.exists()
        else {}
    )
    paths = [cards_path]
    if snapshot_path.exists():
        paths.append(snapshot_path)

    cards: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in paths:
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    continue
                card = json.loads(line)
                source = manifest.get(card.get("source_id", ""), {})
                card.setdefault("title", source.get("title", "Microsoft documentation"))
                card.setdefault("source_url", source.get("url", ""))
                card.setdefault("area", source.get("area", "unknown"))
                card["text"] = normalize_text(card.get("text", ""))
                if not card["text"]:
                    continue
                card.setdefault("section", "Overview")
                card.setdefault("source_type", source.get("source_type", "Microsoft documentation"))
                card.setdefault("id", f"{path.stem}-{line_number}")
                if card.get("id") in translations:
                    card["text_hu"] = normalize_text(translations[card["id"]])
                if card["id"] in seen:
                    continue
                seen.add(card["id"])
                cards.append(card)
    return cards
