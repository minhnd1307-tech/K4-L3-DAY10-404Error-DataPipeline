# Data Corruption, Impact & Idempotent Repair Report

## 📊 3-State Comparison Table

| Metric / Status Indicator | 1. Baseline (Clean Data) | 2. Corrupted Data (Injected Errors) | 3. Repaired (Self-Healed Data) |
| :--- | :---: | :---: | :---: |
| **Data Quality Gate (GX 1.x)** | ✅ PASSED | ❌ FAILED | ✅ PASSED |
| **Freshness SLA** | 🟢 FRESH | 🔴 STALE | 🟢 FRESH |
| **Retrieval Hit Rate** | `1.0000` | `0.9000` | `1.0000` |
| **Mean Token F1 Score** | `0.2754` | `0.1577` | `0.2754` |
| **LLM Judge Accuracy** | `0.2000` | `0.1000` | `0.2000` |

## 🔍 Detailed Analysis

### 1. Silent Failure Impact under Corruption
When synthetic data corruption (dropping records, blank summaries, text noise, title truncation, stale dates, duplicate rows) was introduced:
- The Data Quality Gate detected validation failures.
- Retrieval Hit Rate dropped from `1.0000` down to `0.9000`.
- Mean Token F1 Score dropped from `0.2754` down to `0.1577`.
- This demonstrates how bad data silently degrades LLM answer accuracy in production RAG pipelines.

### 2. Idempotent Self-Healing / Repair Verification
- The pipeline re-ingested clean records from the raw preservation layer (`data/raw/`).
- After running the repair procedure, the Data Quality Gate returned to `PASSED`.
- Performance metrics fully recovered back to baseline levels (`1.0000` Hit Rate, `0.2754` Token F1 Score).
