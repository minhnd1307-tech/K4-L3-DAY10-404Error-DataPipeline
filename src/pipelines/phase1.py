from __future__ import annotations

from datetime import datetime, timezone
import pandas as pd

from core.config import load_settings
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Run baseline Data Pipeline End-to-End (Phase 1)."""
    settings = load_settings()

    # 1. Fetch / Load raw records
    records = fetch_source_records(settings)
    source_info = {
        "total_records": len(records),
        "source": "Crossref REST API / Local Snapshot",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # 2. Clean data
    run_date = datetime.now(timezone.utc)
    clean_df = build_clean_dataframe(records, run_date)

    # Save clean artifacts (parent dir = data/clean/)
    settings.paths.clean_csv.parent.mkdir(parents=True, exist_ok=True)
    clean_df.to_csv(settings.paths.clean_csv, index=False)
    clean_df.to_json(settings.paths.clean_json, orient="records", indent=2)

    # 3. Build Vector Store Index (ChromaDB)
    index = LocalEmbeddingIndex.build(clean_df, settings)

    # 4. Build Test Set
    settings.paths.eval_testset.parent.mkdir(parents=True, exist_ok=True)
    test_set = build_test_set(clean_df, settings.paths.eval_testset)

    # 5. Evaluate Baseline
    settings.paths.baseline_metrics.parent.mkdir(parents=True, exist_ok=True)
    eval_bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )

    # 6. Data Observability (GX 1.x)
    quality_res = run_data_quality_checks(clean_df, settings, "baseline")

    # 7. Freshness SLA
    settings.paths.freshness_report.parent.mkdir(parents=True, exist_ok=True)
    freshness_res = build_freshness_report(clean_df, settings, settings.paths.freshness_report)

    # 8. Generate Phase 1 Markdown Report
    settings.paths.baseline_report.parent.mkdir(parents=True, exist_ok=True)
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_info,
        metrics=eval_bundle.summary,
        quality=quality_res,
        freshness=freshness_res,
    )
    print("✅ Baseline Pipeline Phase 1 executed successfully.")
    print(f"   → Clean CSV : {settings.paths.clean_csv}")
    print(f"   → Test Set  : {settings.paths.eval_testset}")
    print(f"   → Metrics   : {settings.paths.baseline_metrics}")
    print(f"   → Report    : {settings.paths.baseline_report}")


