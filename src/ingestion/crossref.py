from __future__ import annotations

import json
import re
import urllib.request
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from core.config import Settings


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    records = []
    items = payload.get("message", {}).get("items", [])
    for item in items:
        paper_id = item.get("DOI", "")
        if not paper_id:
            continue

        title_list = item.get("title", [])
        title = title_list[0].strip() if title_list else ""

        abstract = item.get("abstract", "")
        summary = re.sub(r'<[^>]+>', '', abstract).strip()

        authors = []
        for a in item.get("author", []):
            given = a.get("given", "")
            family = a.get("family", "")
            authors.append(f"{given} {family}".strip())

        categories = item.get("subject", [])
        primary_category = categories[0] if categories else ""

        published = ""
        pub_dict = item.get("published", {})
        if "date-parts" in pub_dict and pub_dict["date-parts"]:
            parts = pub_dict["date-parts"][0]
            if len(parts) >= 3:
                published = f"{parts[0]:04d}-{parts[1]:02d}-{parts[2]:02d}"
            elif len(parts) >= 2:
                published = f"{parts[0]:04d}-{parts[1]:02d}-01"
            elif len(parts) == 1:
                published = f"{parts[0]:04d}-01-01"

        updated = ""
        created_dict = item.get("created", {})
        if "date-time" in created_dict:
            updated = created_dict["date-time"]

        abs_url = item.get("URL", "")
        pdf_url = ""
        comment = ""

        records.append(PaperRecord(
            paper_id=paper_id,
            title=title,
            summary=summary,
            authors=authors,
            categories=categories,
            primary_category=primary_category,
            published=published,
            updated=updated,
            abs_url=abs_url,
            pdf_url=pdf_url,
            comment=comment
        ))
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    query = urllib.parse.quote(settings.source_query)
    filter_param = urllib.parse.quote(settings.source_filter)
    url = f"https://api.crossref.org/works?query={query}&filter={filter_param}&rows={settings.max_results}"

    payload = None
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'K4-L3A-Day10-DataPipeline'})
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                payload = json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Lỗi gọi API Crossref: {e}. Fallback sang snapshot local...")

    if not payload:
        try:
            with open(settings.paths.raw_api_response, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception as e:
            print(f"Không thể load snapshot local: {e}")
            return []

    settings.paths.raw_api_response.parent.mkdir(parents=True, exist_ok=True)
    with open(settings.paths.raw_api_response, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    records = parse_crossref_payload(payload)

    records_dict = [vars(r) for r in records]
    settings.paths.raw_records_json.parent.mkdir(parents=True, exist_ok=True)
    with open(settings.paths.raw_records_json, "w", encoding="utf-8") as f:
        json.dump(records_dict, f, indent=2, ensure_ascii=False)

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    records = []
    for d in data:
        records.append(PaperRecord(**d))
    return records
