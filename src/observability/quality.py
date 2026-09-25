from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import great_expectations as gx
import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Execute Great Expectations 1.x data quality checks on the provided DataFrame."""
    context = gx.get_context(mode="ephemeral")

    # Add Pandas Data Source and Asset for Great Expectations 1.x using unique names
    data_source_name = f"pandas_source_{report_name}"
    asset_name = f"paper_asset_{report_name}"
    batch_def_name = f"batch_def_{report_name}"

    data_source = context.data_sources.add_pandas(name=data_source_name)
    data_asset = data_source.add_dataframe_asset(name=asset_name)
    batch_def = data_asset.add_batch_definition_whole_dataframe(batch_def_name)
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    # Define core expectation checks
    expectations = [
        gx.expectations.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="paper_id"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="title"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="text_for_embedding"),
        gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id"),
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30),
    ]

    results_list = []
    overall_success = True

    for exp in expectations:
        res = batch.validate(exp)
        res_dict = res.to_json_dict()
        results_list.append(res_dict)
        if not res.success:
            overall_success = False

    payload = {
        "success": overall_success,
        "report_name": report_name,
        "total_expectations": len(expectations),
        "passed_expectations": sum(1 for r in results_list if r.get("success", False)),
        "details": results_list,
    }

    settings.paths.quality_dir.mkdir(parents=True, exist_ok=True)
    report_file = settings.paths.quality_dir / f"{report_name}_gx_report.json"
    write_json(report_file, payload)

    return payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: Path | str) -> dict[str, Any]:
    """Aggregate data freshness metrics and evaluate against the 180-day SLA."""
    report_file = Path(report_path)
    report_file.parent.mkdir(parents=True, exist_ok=True)

    total_rows = len(df)
    if total_rows == 0:
        payload = {
            "latest_published": "N/A",
            "oldest_published": "N/A",
            "stale_rows": 0,
            "total_rows": 0,
            "stale_ratio": 0.0,
            "is_fresh": False,
        }
        write_json(report_file, payload)
        return payload

    threshold = getattr(settings, "freshness_threshold_days", 180)
    stale_rows = int((df["age_days"] > threshold).sum()) if "age_days" in df.columns else 0
    stale_ratio = stale_rows / total_rows
    is_fresh = stale_ratio <= 0.25

    latest_published = str(df["published"].max()) if "published" in df.columns else "N/A"
    oldest_published = str(df["published"].min()) if "published" in df.columns else "N/A"

    payload = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": stale_ratio,
        "is_fresh": is_fresh,
    }
    write_json(report_file, payload)
    return payload
