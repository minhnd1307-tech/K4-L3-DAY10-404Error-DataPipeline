from __future__ import annotations

from datetime import datetime, timezone
import pandas as pd

from core.config import load_settings
from core.utils import read_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Run Corruption, Self-Healing Repair, and 3-State Comparison Flow."""
    settings = load_settings()

    # Load baseline clean DataFrame
    if settings.paths.clean_json.exists():
        clean_df = pd.read_json(settings.paths.clean_json)
    else:
        records = fetch_source_records(settings)
        clean_df = build_clean_dataframe(records, datetime.now(timezone.utc))

    # Load baseline metrics (produced by run_phase1.py)
    baseline_metrics = (
        read_json(settings.paths.baseline_metrics)
        if settings.paths.baseline_metrics.exists()
        else {}
    )

    # Step 1: Corrupt clean DataFrame
    settings.paths.corruption_log.parent.mkdir(parents=True, exist_ok=True)
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    settings.paths.corrupted_clean_csv.parent.mkdir(parents=True, exist_ok=True)
    corrupted_df.to_csv(settings.paths.corrupted_clean_csv, index=False)
    corrupted_df.to_json(settings.paths.corrupted_clean_json, orient="records", indent=2)

    # Step 2: Build Corrupted Index & Evaluate
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df, settings, settings.paths.corrupted_embeddings_json
    )
    settings.paths.corrupted_metrics.parent.mkdir(parents=True, exist_ok=True)
    corrupted_eval = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    settings.paths.corrupted_quality_report.parent.mkdir(parents=True, exist_ok=True)
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, settings.paths.corrupted_quality_report
    )

    # Step 3: Idempotent Repair from Raw Preservation layer
    raw_records = (
        load_raw_records(settings.paths.raw_records_json)
        if settings.paths.raw_records_json.exists()
        else fetch_source_records(settings)
    )
    repaired_df = build_clean_dataframe(raw_records, datetime.now(timezone.utc))
    settings.paths.repaired_clean_csv.parent.mkdir(parents=True, exist_ok=True)
    repaired_df.to_csv(settings.paths.repaired_clean_csv, index=False)
    repaired_df.to_json(settings.paths.repaired_clean_json, orient="records", indent=2)

    # Step 4: Build Repaired Index & Evaluate
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df, settings, settings.paths.repaired_embeddings_json
    )
    settings.paths.repaired_metrics.parent.mkdir(parents=True, exist_ok=True)
    repaired_eval = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(
        repaired_df, settings, settings.paths.freshness_report
    )

    # Step 5: Generate Comparison Report (3 States)
    settings.paths.comparison_report.parent.mkdir(parents=True, exist_ok=True)
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_eval.summary,
        repaired_metrics=repaired_eval.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    print("✅ Corruption, Repair & Comparison Flow executed successfully.")
    print(f"   → Corruption Log    : {settings.paths.corruption_log}")
    print(f"   → Corrupted Metrics : {settings.paths.corrupted_metrics}")
    print(f"   → Repaired Metrics  : {settings.paths.repaired_metrics}")
    print(f"   → Comparison Report : {settings.paths.comparison_report}")


