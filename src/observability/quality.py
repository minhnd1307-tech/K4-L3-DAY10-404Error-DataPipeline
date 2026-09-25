from __future__ import annotations

from typing import Any
import json
import pandas as pd
import great_expectations as gx

from core.config import Settings


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})
    
    suite = context.suites.add(gx.ExpectationSuite(name="papers_suite"))
    
    suite.add_expectation(
        gx.expectations.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000)
    )
    
    for col in ["paper_id", "title", "text_for_embedding"]:
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToNotBeNull(column=col)
        )
        
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id")
    )
    
    suite.add_expectation(
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30)
    )
    
    validation_result = batch.validate(suite)
    
    result = {
        "success": validation_result.success,
        "results": [r.to_json_dict() for r in validation_result.results]
    }
    
    settings.paths.quality_dir.mkdir(parents=True, exist_ok=True)
    report_path = settings.paths.quality_dir / f"{report_name}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
        
    return result


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    if df.empty:
        return {}
        
    latest_published = df["published"].max()
    oldest_published = df["published"].min()
    
    stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())
    total_rows = len(df)
    
    is_fresh = True
    if total_rows > 0:
        if stale_rows / total_rows > 0.25:
            is_fresh = False
            
    payload = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "is_fresh": is_fresh
    }
    
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        
    return payload
