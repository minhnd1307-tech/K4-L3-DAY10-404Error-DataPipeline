from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import pandas as pd

from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw paper records into a structured DataFrame ready for vector embedding."""
    if not records:
        return pd.DataFrame()

    if run_date.tzinfo is None:
        run_date = run_date.replace(tzinfo=timezone.utc)

    data = []
    for r in records:
        title = r.title.strip()
        summary = r.summary.strip()
        authors_joined = ", ".join(r.authors).strip() if isinstance(r.authors, list) else str(r.authors).strip()
        categories_joined = ", ".join(r.categories).strip() if isinstance(r.categories, list) else str(r.categories).strip()

        # Parse publication date to calculate age_days
        try:
            pub_date = datetime.strptime(r.published, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except Exception:
            try:
                pub_date = datetime.fromisoformat(r.published.replace("Z", "+00:00"))
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
            except Exception:
                pub_date = run_date

        age_days = max(0, (run_date - pub_date).days)
        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {r.published}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary}"
        )

        data.append(
            {
                "paper_id": r.paper_id,
                "title": title,
                "summary": summary,
                "authors": r.authors,
                "categories": r.categories,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "primary_category": r.primary_category,
                "published": r.published,
                "updated": r.updated,
                "abs_url": r.abs_url,
                "pdf_url": r.pdf_url,
                "comment": r.comment,
                "age_days": age_days,
                "summary_chars": len(summary),
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(data)
    if not df.empty:
        df = df.drop_duplicates(subset=["paper_id"], keep="first").copy()
        df = df.sort_values(by="published", ascending=False).reset_index(drop=True)

    return df
