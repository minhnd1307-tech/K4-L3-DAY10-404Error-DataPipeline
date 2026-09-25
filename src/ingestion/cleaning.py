from __future__ import annotations

from datetime import datetime

import pandas as pd

from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()
        
    data = []
    for r in records:
        title = r.title.strip()
        summary = r.summary.strip()
        authors = ", ".join(r.authors).strip()
        categories = ", ".join(r.categories).strip()
        
        try:
            pub_date = datetime.strptime(r.published, "%Y-%m-%d").replace(tzinfo=run_date.tzinfo)
        except ValueError:
            try:
                pub_date = datetime.fromisoformat(r.published.replace('Z', '+00:00'))
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=run_date.tzinfo)
            except ValueError:
                pub_date = run_date
                
        age_days = (run_date - pub_date).days
        
        text_for_embedding = f"Title: {title}\nAuthors: {authors}\nPublished: {r.published}\nCategories: {categories}\nSummary: {summary}"
        
        data.append({
            "paper_id": r.paper_id,
            "title": title,
            "summary": summary,
            "authors_joined": authors,
            "categories_joined": categories,
            "published": r.published,
            "age_days": age_days,
            "summary_chars": len(summary),
            "text_for_embedding": text_for_embedding
        })
        
    df = pd.DataFrame(data)
    
    if not df.empty:
        df = df.drop_duplicates(subset=["paper_id"], keep="first")
        df = df.sort_values(by="published", ascending=False).reset_index(drop=True)
        
    return df
