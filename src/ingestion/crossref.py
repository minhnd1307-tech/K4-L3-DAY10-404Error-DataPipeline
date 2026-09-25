from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import re
from pathlib import Path
import requests

from core.config import Settings
from core.utils import read_json, write_json


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



def _clean_jats_html(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"<[^>]+>", "", text)
    return cleaned.strip()


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref API response payload into a list of PaperRecord instances."""
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        doi = item.get("DOI", "").strip()
        if not doi:
            continue

        titles = item.get("title", [])
        title = titles[0].strip() if titles else "Untitled"

        abstract_raw = item.get("abstract", "")
        summary = _clean_jats_html(abstract_raw)

        authors_raw = item.get("author", [])
        authors = []
        for a in authors_raw:
            given = a.get("given", "").strip()
            family = a.get("family", "").strip()
            name = f"{given} {family}".strip()
            if name:
                authors.append(name)
        if not authors:
            authors = ["Anonymous"]

        subjects = item.get("subject", [])
        categories = [s.strip() for s in subjects] if subjects else ["General"]
        primary_cat = categories[0]

        pub_parts = item.get("published", {}).get("date-parts", [[]])[0]
        if len(pub_parts) >= 3:
            published = f"{pub_parts[0]:04d}-{pub_parts[1]:02d}-{pub_parts[2]:02d}"
        elif len(pub_parts) == 2:
            published = f"{pub_parts[0]:04d}-{pub_parts[1]:02d}-01"
        elif len(pub_parts) == 1:
            published = f"{pub_parts[0]:04d}-01-01"
        else:
            published = "2026-01-01"

        updated = published
        url = item.get("URL", f"https://doi.org/{doi}")

        record = PaperRecord(
            paper_id=doi,
            title=title,
            summary=summary,
            authors=authors,
            categories=categories,
            primary_category=primary_cat,
            published=published,
            updated=updated,
            abs_url=url,
            pdf_url=url,
            comment=f"Crossref record {doi}",
        )
        records.append(record)

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch source records from Crossref REST API or load from local offline snapshot."""
    raw_response_path = settings.paths.raw_api_response
    raw_records_path = settings.paths.raw_records_json

    # Attempt fetching from Crossref REST API first unless using offline snapshot
    try:
        url = "https://api.crossref.org/works"
        params = {
            "query": settings.source_query,
            "rows": settings.max_results,
            "filter": settings.source_filter,
        }
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            payload = resp.json()
            write_json(raw_response_path, payload)
            records = parse_crossref_payload(payload)
            if records:
                write_json(raw_records_path, [asdict(r) for r in records])
                return records
    except Exception:
        pass

    # Fallback to local raw_records_json snapshot if available
    if raw_records_path.exists():
        return load_raw_records(raw_records_path)

    # Fallback to raw_api_response snapshot if available
    if raw_response_path.exists():
        payload = read_json(raw_response_path)
        records = parse_crossref_payload(payload)
        write_json(raw_records_path, [asdict(r) for r in records])
        return records

    return []


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load JSON snapshot of PaperRecord list."""
    data = read_json(path)
    records: list[PaperRecord] = []
    for item in data:
        record = PaperRecord(
            paper_id=item["paper_id"],
            title=item["title"],
            summary=item["summary"],
            authors=item["authors"],
            categories=item["categories"],
            primary_category=item.get("primary_category", item["categories"][0] if item["categories"] else "General"),
            published=item["published"],
            updated=item.get("updated", item["published"]),
            abs_url=item.get("abs_url", ""),
            pdf_url=item.get("pdf_url", ""),
            comment=item.get("comment", ""),
        )
        records.append(record)
    return records

