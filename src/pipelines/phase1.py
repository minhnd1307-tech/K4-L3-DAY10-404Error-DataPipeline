from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


logger = logging.getLogger("pipeline.phase1")


def main() -> None:
    """Xay dung baseline pipeline end-to-end (Checkpoint 3).

    Dieu phoi boi: Dung (Pipeline Lead & Integrator).
    Cac buoc thuc thi:
    1. Load settings he thong.
    2. Load raw records tu snapshot san co hoac fetch moi tu Crossref API.
    3. Lam sach du lieu (cleaning), tinh age_days va text_for_embedding.
    4. Luu clean dataset (CSV & JSON).
    5. Build Chroma vector index ('papers-baseline').
    6. Sinh hoac load bo benchmark test set (10 cau hoi).
    7. Danh gia Baseline RAG metrics (Hit Rate, Token F1, LLM Judge).
    8. Chay Great Expectations 1.x Quality Gate va Freshness SLA.
    9. Xuat Phase 1 Markdown Report tai data/reports/phase1_report.md.
    """
    start_time = time.time()
    print("=" * 70)
    print("🚀 [PHASE 1] KHOI DONG BASELINE PIPELINE END-TO-END")
    print("=" * 70)

    # 1. Load settings
    settings: Settings = load_settings()
    print(f"[*] Project root: {settings.paths.project_dir}")
    print(f"[*] LLM Provider: {settings.llm_provider} (Model: {settings.model_name})")
    print(f"[*] Embedding: {settings.embedding_model}")

    # 2. Ingestion: Load hoac fetch raw records
    run_date = now_utc()
    print("\n--- [Buoc 1/7] Thu thap & Bao ton du lieu goc (Raw Ingestion) ---")
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        print(f"[*] Dang goi source API: {settings.source_api}...")
        records = fetch_source_records(settings)
    else:
        print(f"[*] Dang nap du lieu tu snapshot offline: {settings.paths.raw_records_json}...")
        records = load_raw_records(settings.paths.raw_records_json)
    print(f"[✓] Da nap thanh cong {len(records)} ban ghi PaperRecord.")

    # 3. Cleaning & Data Modeling
    print("\n--- [Buoc 2/7] Lam sach & Chuan hoa Schema (Data Cleaning) ---")
    df = build_clean_dataframe(records, run_date=run_date)
    print(f"[✓] Clean thanh cong {len(df)} dong du lieu.")

    # 4. Luu clean artifacts
    print(f"[*] Dang luu clean CSV vao {settings.paths.clean_csv}...")
    write_csv(df, settings.paths.clean_csv)
    print(f"[*] Dang luu clean JSON vao {settings.paths.clean_json}...")
    write_json(settings.paths.clean_json, df.to_dict(orient="records"))
    print("[✓] Da luu tru toan ven clean artifacts.")

    # 5. Build Chroma vector index
    print(f"\n--- [Buoc 3/7] Build Vector Store Indexing ('{settings.baseline_collection_name}') ---")
    index = LocalEmbeddingIndex.build(
        df=df,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )
    print(f"[✓] Da index thanh cong {len(index.documents)} documents vao ChromaDB collection.")

    # 6. Benchmark Test Set
    print("\n--- [Buoc 4/7] Chuan bi Benchmark Test Set ---")
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        print(f"[*] Sinh bo test set moi tai {settings.paths.eval_testset}...")
        test_set = build_test_set(df, settings.paths.eval_testset)
    else:
        print(f"[*] Su dung test set san co tai {settings.paths.eval_testset}...")
        test_set = read_json(settings.paths.eval_testset)
    print(f"[✓] Test set san sang voi {len(test_set)} cau hoi danh gia.")

    # 7. Evaluate Baseline RAG
    print("\n--- [Buoc 5/7] Danh gia Chi so Baseline (RAG Evaluation) ---")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    metrics = bundle.summary
    print(f"[✓] Retrieval Hit Rate: {metrics.get('retrieval_hit_rate', 0.0):.4f}")
    print(f"[✓] Mean Token F1:     {metrics.get('mean_token_f1', 0.0):.4f}")
    print(f"[✓] Judge Accuracy:    {metrics.get('judge_accuracy', 0.0):.4f}")
    print(f"[✓] Mean Judge Score:  {metrics.get('mean_judge_score', 0.0):.2f}/5.0")

    # 8. Data Observability (GX 1.x & Freshness)
    print("\n--- [Buoc 6/7] Kiem dinh Data Quality (GX 1.x) & Freshness SLA ---")
    quality_report = run_data_quality_checks(df, settings=settings, report_name="baseline")
    write_json(settings.paths.baseline_quality_report, quality_report)
    print(f"[✓] Great Expectations 1.x status: success={quality_report.get('success', False)}")

    freshness_report = build_freshness_report(df, settings=settings, report_path=settings.paths.freshness_report)
    print(f"[✓] Freshness SLA: is_fresh={freshness_report.get('is_fresh', False)} (stale: {freshness_report.get('stale_rows', 0)}/{freshness_report.get('total_rows', 0)})")

    # 9. Markdown Report Generation
    print("\n--- [Buoc 7/7] Sinh Bao Cao Tong Hop Phase 1 Markdown ---")
    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "total_records": len(df),
        "run_date": run_date.isoformat(),
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=metrics,
        quality=quality_report,
        freshness=freshness_report,
    )
    print(f"[✓] Bao cao Phase 1 da duoc xuat tai: {settings.paths.baseline_report}")

    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print(f"🎉 HOAN THANH PHASE 1 BASELINE PIPELINE TRONG {elapsed:.2f} GIAY!")
    print("=" * 70)

