from __future__ import annotations

from pathlib import Path
from typing import Any
import pandas as pd

from core.utils import write_json


def build_test_set(df: pd.DataFrame, output_path: Path | str) -> list[dict[str, Any]]:
    """Build evaluation test set from cleaned DataFrame.

    Generates test questions across 4 categories: summary, authors, date, categories.
    """
    if df.empty or len(df) < 3:
        raise ValueError("DataFrame does not contain enough records to build evaluation test set.")

    test_set: list[dict[str, Any]] = []
    # Sample up to 10 records deterministically
    sample_df = df.head(10)
    question_types = ["summary", "authors", "date", "categories"]

    for idx, (_, row) in enumerate(sample_df.iterrows(), start=1):
        q_type = question_types[(idx - 1) % len(question_types)]
        paper_id = str(row["paper_id"])
        title = str(row["title"])

        if q_type == "summary":
            question = f"What is the summary of the paper '{title}'?"
            ground_truth = str(row.get("summary", ""))
        elif q_type == "authors":
            question = f"Who wrote the paper '{title}'?"
            ground_truth = str(row.get("authors_joined", row.get("authors", "")))
        elif q_type == "date":
            question = f"When was the paper '{title}' published?"
            ground_truth = str(row.get("published", ""))
        else:  # categories
            question = f"What categories does the paper '{title}' belong to?"
            ground_truth = str(row.get("categories_joined", row.get("categories", "")))

        test_set.append(
            {
                "id": f"eval_{idx:03d}",
                "question_type": q_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [paper_id],
            }
        )

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    write_json(output_file, test_set)

    return test_set

