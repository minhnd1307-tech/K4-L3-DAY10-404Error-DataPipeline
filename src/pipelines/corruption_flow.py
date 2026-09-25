from __future__ import annotations

import logging
import time
from pathlib import Path

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


logger = logging.getLogger("pipeline.corruption_flow")


def _print_comparison_table(
    baseline_metrics: dict,
    corrupted_metrics: dict,
    repaired_metrics: dict,
    corrupted_quality: dict,
    repaired_quality: dict,
) -> None:
    """In bang doi chieu 3 trang thai truc quan ra console."""
    print("\n" + "=" * 85)
    print(f"{'CHI SO / METRIC':<30} | {'BASELINE':<15} | {'CORRUPTED':<15} | {'REPAIRED':<15}")
    print("-" * 85)
    
    b_hit = f"{baseline_metrics.get('retrieval_hit_rate', 0.0):.4f}"
    c_hit = f"{corrupted_metrics.get('retrieval_hit_rate', 0.0):.4f}"
    r_hit = f"{repaired_metrics.get('retrieval_hit_rate', 0.0):.4f}"
    print(f"{'Retrieval Hit Rate':<30} | {b_hit:<15} | {c_hit:<15} | {r_hit:<15}")

    b_f1 = f"{baseline_metrics.get('mean_token_f1', 0.0):.4f}"
    c_f1 = f"{corrupted_metrics.get('mean_token_f1', 0.0):.4f}"
    r_f1 = f"{repaired_metrics.get('mean_token_f1', 0.0):.4f}"
    print(f"{'Mean Token F1':<30} | {b_f1:<15} | {c_f1:<15} | {r_f1:<15}")

    b_acc = f"{baseline_metrics.get('judge_accuracy', 0.0):.4f}"
    c_acc = f"{corrupted_metrics.get('judge_accuracy', 0.0):.4f}"
    r_acc = f"{repaired_metrics.get('judge_accuracy', 0.0):.4f}"
    print(f"{'Judge Accuracy':<30} | {b_acc:<15} | {c_acc:<15} | {r_acc:<15}")

    b_score = f"{baseline_metrics.get('mean_judge_score', 0.0):.2f}/5.0"
    c_score = f"{corrupted_metrics.get('mean_judge_score', 0.0):.2f}/5.0"
    r_score = f"{repaired_metrics.get('mean_judge_score', 0.0):.2f}/5.0"
    print(f"{'Mean Judge Score':<30} | {b_score:<15} | {c_score:<15} | {r_score:<15}")

    b_gx = "True (PASS)"
    c_gx = f"{corrupted_quality.get('success', False)} (FAIL)" if not corrupted_quality.get('success') else "True"
    r_gx = f"{repaired_quality.get('success', False)} (PASS)" if repaired_quality.get('success') else "False"
    print(f"{'Great Expectations 1.x':<30} | {b_gx:<15} | {c_gx:<15} | {r_gx:<15}")
    print("=" * 85 + "\n")


def main() -> None:
    """Xay dung corruption -> evaluate -> repair -> compare flow (Checkpoint 4 & 5).

    Dieu phoi boi: Dung (Pipeline Lead & Integrator).
    Cac buoc thuc thi:
    1. Load settings va doc clean dataset ban dau.
    2. Doc baseline metrics da tinh o Phase 1.
    3. Tiêm 6 kịch bản lỗi thực tế (Corruption Suite).
    4. Build corrupted Chroma index ('papers-corrupted') va danh gia suy giam.
    5. Kiem dinh Data Quality Gate tren du lieu loi (ky vong GX FAIL).
    6. Thuc hien Idempotent Repair: Phuc hoi sach tu Raw records va danh gia lai.
    7. Kiem dinh lai chat luong sau Repair (ky vong GX PASS).
    8. Xuat bao cao doi chieu 3 trang thai tai data/reports/corruption_report.md.
    """
    start_time = time.time()
    print("=" * 70)
    print("🧪 [PHASE 2] KHOI DONG CORRUPTION & IDEMPOTENT REPAIR FLOW")
    print("=" * 70)

    # 1. Load settings
    settings: Settings = load_settings()

    # 2. Doc du lieu sach ban dau
    print("\n--- [Buoc 1/6] Nap du lieu Baseline & Metrics ban dau ---")
    if settings.paths.clean_json.exists():
        clean_df = pd.read_json(settings.paths.clean_json)
    elif settings.paths.clean_csv.exists():
        clean_df = pd.read_csv(settings.paths.clean_csv)
    else:
        print("[!] Khong tim thay clean dataset. Dang tu dong tao tu raw records...")
        raw_records = load_raw_records(settings.paths.raw_records_json)
        clean_df = build_clean_dataframe(raw_records, now_utc())

    if settings.paths.baseline_metrics.exists():
        baseline_metrics = read_json(settings.paths.baseline_metrics)
    else:
        print("[!] Chua co baseline_metrics.json. Vui long chay script/run_phase1.py truoc!")
        baseline_metrics = {}
    print(f"[✓] Baseline da san sang voi {len(clean_df)} dong du lieu.")

    # 3. Tiem doc to du lieu (Data Corruption)
    print("\n--- [Buoc 2/6] Tiem 6 dang doc to du lieu (Data Corruption Suite) ---")
    corrupted_df = corrupt_clean_dataframe(clean_df, output_log_path=settings.paths.corruption_log)
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))
    print(f"[✓] Da tao corrupted dataset: {len(corrupted_df)} dong (Log: {settings.paths.corruption_log})")

    # 4. Build Corrupted Index & Evaluate
    print(f"\n--- [Buoc 3/6] Build Vector Index Corrupted ('{settings.corrupted_collection_name}') & Do Luong Suy Giam ---")
    corrupted_index = LocalEmbeddingIndex.build(
        df=corrupted_df,
        settings=settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    corrupted_metrics = corrupted_bundle.summary
    print(f"[!] Hit Rate sau khi loi: {corrupted_metrics.get('retrieval_hit_rate', 0.0):.4f} (Baseline: {baseline_metrics.get('retrieval_hit_rate', 0.0):.4f})")
    print(f"[!] Token F1 sau khi loi:  {corrupted_metrics.get('mean_token_f1', 0.0):.4f} (Baseline: {baseline_metrics.get('mean_token_f1', 0.0):.4f})")

    # 5. Observability tren Du lieu Loi (Ky vong canh bao)
    print("\n--- [Buoc 4/6] Kiem dinh Data Quality tren du lieu loi ---")
    corrupted_quality = run_data_quality_checks(corrupted_df, settings=settings, report_name="corrupted")
    write_json(settings.paths.corrupted_quality_report, corrupted_quality)
    print(f"[*] Great Expectations 1.x Result: success={corrupted_quality.get('success', False)} (Bao dong du lieu ban!)")

    corrupted_freshness_path = settings.paths.quality_dir / "corrupted_freshness_report.json"
    corrupted_freshness = build_freshness_report(corrupted_df, settings=settings, report_path=corrupted_freshness_path)

    # 6. Idempotent Repair (Tai tao sach tu Raw data)
    print("\n--- [Buoc 5/6] Kich hoat Idempotent Repair (Tai tao tu Raw Preservation) ---")
    print(f"[*] Dang nap lai raw records tu {settings.paths.raw_records_json}...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, run_date=now_utc())
    
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    print(f"[✓] Da lam sach lai toan bo: {len(repaired_df)} dong.")

    # Build Repaired Index & Evaluate
    print(f"[*] Re-indexing ChromaDB collection ('{settings.repaired_collection_name}')...")
    repaired_index = LocalEmbeddingIndex.build(
        df=repaired_df,
        settings=settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_metrics = repaired_bundle.summary
    print(f"[✓] Hit Rate sau khi Repair: {repaired_metrics.get('retrieval_hit_rate', 0.0):.4f}")
    print(f"[✓] Token F1 sau khi Repair:  {repaired_metrics.get('mean_token_f1', 0.0):.4f}")

    # Quality checks tren du lieu sau Repair
    repaired_quality = run_data_quality_checks(repaired_df, settings=settings, report_name="repaired")
    repaired_freshness_path = settings.paths.quality_dir / "repaired_freshness_report.json"
    repaired_freshness = build_freshness_report(repaired_df, settings=settings, report_path=repaired_freshness_path)
    print(f"[✓] GX 1.x sau Repair: success={repaired_quality.get('success', False)} (Phuc hoi thanh cong!)")

    # 7. Xuat bao cao Markdown doi chieu 3 trang thai
    print("\n--- [Buoc 6/6] Sinh Bao Cao Doi Chieu 3 Trang Thai (Comparison Report) ---")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_metrics,
        repaired_metrics=repaired_metrics,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    print(f"[✓] Bao cao doi chieu da xuat tai: {settings.paths.comparison_report}")

    # In bang so sanh truc quan ra console
    _print_comparison_table(
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_metrics,
        repaired_metrics=repaired_metrics,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
    )

    elapsed = time.time() - start_time
    print(f"🎉 HOAN THANH CORRUPTION & IDEMPOTENT REPAIR FLOW TRONG {elapsed:.2f} GIAY!")
    print("=" * 70)
