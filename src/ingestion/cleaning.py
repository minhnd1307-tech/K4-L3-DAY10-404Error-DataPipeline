from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import pandas as pd

from ingestion.crossref import PaperRecord



def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw paper records into a structured DataFrame ready for vector embedding."""
    if not records:
        return pd.DataFrame()

    raw_dicts = [asdict(r) for r in records]
    df = pd.DataFrame(raw_dicts)

    # Remove duplicates by paper_id
    df = df.drop_duplicates(subset=["paper_id"]).copy()

    # Normalize whitespace in text fields
    df["title"] = df["title"].astype(str).str.strip()
    df["summary"] = df["summary"].astype(str).str.strip()

    # Ensure run_date is timezone-aware if needed
    if run_date.tzinfo is None:
        run_date = run_date.replace(tzinfo=timezone.utc)

    # Calculate age_days and helper columns
    def parse_age(pub_str: str) -> int:
        try:
            dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return (run_date - dt).days
        except Exception:
            return 0

    df["age_days"] = df["published"].apply(parse_age)

    df["authors_joined"] = df["authors"].apply(lambda a: ", ".join(a) if isinstance(a, list) else str(a))
    df["categories_joined"] = df["categories"].apply(lambda c: ", ".join(c) if isinstance(c, list) else str(c))
    df["summary_chars"] = df["summary"].str.len()

    # Construct text_for_embedding
    def make_embedding_text(row: pd.Series) -> str:
        return (
            f"Title: {row['title']}\n"
            f"Authors: {row['authors_joined']}\n"
            f"Published: {row['published']}\n"
            f"Categories: {row['categories_joined']}\n"
            f"Summary: {row['summary']}"
        )

    df["text_for_embedding"] = df.apply(make_embedding_text, axis=1)

    return df

