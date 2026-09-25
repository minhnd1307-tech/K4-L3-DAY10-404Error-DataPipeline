from __future__ import annotations

from pathlib import Path
import pandas as pd

from core.utils import write_json



def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path | str) -> pd.DataFrame:
    """Inject 6 synthetic data corruption errors into clean DataFrame and log changes."""
    if df.empty:
        return df

    corrupted_df = df.copy()
    corruption_log: list[dict[str, str]] = []

    # 1. Drop latest 20% records
    n_drop = max(1, int(len(corrupted_df) * 0.2))
    dropped_ids = corrupted_df.tail(n_drop)["paper_id"].tolist()
    corrupted_df = corrupted_df.iloc[:-n_drop].copy()
    corruption_log.append({
        "error_type": "drop_latest_records",
        "description": f"Dropped {n_drop} latest records",
        "affected_ids": str(dropped_ids),
    })

    # 2. Blank summary on 2 rows
    if len(corrupted_df) >= 2:
        target_indices = corrupted_df.index[:2]
        for idx in target_indices:
            pid = str(corrupted_df.loc[idx, "paper_id"])
            corrupted_df.loc[idx, "summary"] = ""
            corruption_log.append({
                "error_type": "blank_summary",
                "description": f"Cleared summary for paper {pid}",
                "affected_ids": pid,
            })

    # 3. Inject noise into text of 2 rows
    if len(corrupted_df) >= 4:
        target_indices = corrupted_df.index[2:4]
        for idx in target_indices:
            pid = str(corrupted_df.loc[idx, "paper_id"])
            corrupted_df.loc[idx, "summary"] = "###NOISE### " + str(corrupted_df.loc[idx, "summary"]) + " @@@CORRUPTED@@@"
            corruption_log.append({
                "error_type": "inject_noise",
                "description": f"Injected noise characters into summary for paper {pid}",
                "affected_ids": pid,
            })

    # 4. Truncate title on 2 rows
    if len(corrupted_df) >= 6:
        target_indices = corrupted_df.index[4:6]
        for idx in target_indices:
            pid = str(corrupted_df.loc[idx, "paper_id"])
            corrupted_df.loc[idx, "title"] = str(corrupted_df.loc[idx, "title"])[:5]
            corruption_log.append({
                "error_type": "truncate_title",
                "description": f"Truncated title to under 8 chars for paper {pid}",
                "affected_ids": pid,
            })

    # 5. Stale date (shift published date back 365 days) on 30% rows
    stale_count = max(1, int(len(corrupted_df) * 0.3))
    stale_indices = corrupted_df.index[:stale_count]
    for idx in stale_indices:
        pid = str(corrupted_df.loc[idx, "paper_id"])
        corrupted_df.loc[idx, "published"] = "2024-01-01"
        corrupted_df.loc[idx, "age_days"] = int(corrupted_df.loc[idx, "age_days"]) + 365
        corruption_log.append({
            "error_type": "stale_date",
            "description": f"Set published date to stale 2024-01-01 for paper {pid}",
            "affected_ids": pid,
        })

    # 6. Add duplicate rows
    if len(corrupted_df) >= 2:
        dup_rows = corrupted_df.iloc[:2].copy()
        corrupted_df = pd.concat([corrupted_df, dup_rows], ignore_index=True)
        corruption_log.append({
            "error_type": "duplicate_rows",
            "description": f"Duplicated {len(dup_rows)} rows",
            "affected_ids": str(dup_rows["paper_id"].tolist()),
        })

    # Rebuild summary_chars & text_for_embedding for all rows
    corrupted_df["summary_chars"] = corrupted_df["summary"].astype(str).str.len()

    def rebuild_embedding_text(row: pd.Series) -> str:
        return (
            f"Title: {row['title']}\n"
            f"Authors: {row['authors_joined']}\n"
            f"Published: {row['published']}\n"
            f"Categories: {row['categories_joined']}\n"
            f"Summary: {row['summary']}"
        )

    corrupted_df["text_for_embedding"] = corrupted_df.apply(rebuild_embedding_text, axis=1)

    log_file = Path(output_log_path)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    write_json(log_file, corruption_log)

    return corrupted_df

