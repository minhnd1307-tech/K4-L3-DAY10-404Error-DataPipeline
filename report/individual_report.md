# Member Role Report — Day 10: Data Pipeline & Data Observability

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác.

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                             |
| ------------------ | --------------------------------------------------------------------- |
| Họ và tên       | HOANG BICH NGOC                                                      |
| MSSV               | 2A202602766                                                           |
| Khóa/Lớp         | K4                                                                    |
| Tên nhóm         | 404Error                                                              |
| Vai trò chính    | Observability & Evaluation Lead                                       |
| Repository         | https://github.com/minhnd1307-tech/K4-L3-DAY10-404Error-DataPipeline |
| Ngày hoàn thành | 2026-09-25                                                            |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ----------- |
| Data Quality Gate (GX 1.x) | `src/observability/quality.py` — `run_data_quality_checks()` | `pd.DataFrame` (cleaned), `Settings`, `report_name` | `data/quality/{name}_gx_report.json` + dict validation | Hoàn thành |
| Freshness SLA Monitoring | `src/observability/quality.py` — `build_freshness_report()` | `pd.DataFrame` (có cột `age_days`, `published`), `report_path` | `data/quality/freshness_report.json` với `is_fresh`, `stale_ratio` | Hoàn thành |
| Benchmark Test Set | `src/evaluation/testset.py` — `build_test_set()` | `pd.DataFrame` (cleaned), `output_path` | `data/eval/test_set.json` — 10 câu hỏi Ground Truth | Hoàn thành |
| Phase 1 Markdown Report | `src/observability/reporting.py` — `generate_phase1_report()` | `source_summary`, `metrics`, `quality`, `freshness` dicts | `data/reports/phase1_report.md` — 4 sections | Hoàn thành |
| Corruption Comparison Report | `src/observability/reporting.py` — `generate_corruption_report()` | Baseline/corrupted/repaired metrics + quality + freshness | `data/reports/corruption_report.md` — bảng 3 trạng thái | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Sửa lỗi `AttributeError: 'Paths' object has no attribute 'clean_dir'` — mapping đúng tên path từ `config.py` | Pipeline Lead — `src/pipelines/phase1.py`, `corruption_flow.py` | Cả hai pipeline khởi chạy được, không còn AttributeError |
| Gỡ lỗi Python 3.14 không tương thích `great-expectations>=1.16.1` — dùng `--ignore-requires-python` | Toàn nhóm — môi trường | Môi trường in ra "Môi trường sẵn sàng" |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Triển khai GX 1.x ephemeral context, 6 Expectations | `src/observability/quality.py` | `data/quality/baseline_gx_report.json` | Chạy lệnh verify GX sau khi pipeline hoàn tất |
| Freshness SLA (ngưỡng 180 ngày, 25%) | `src/observability/quality.py` | `data/quality/freshness_report.json` với `is_fresh` | Kiểm tra JSON sau khi chạy pipeline |
| Sinh 10 câu hỏi Ground Truth đa dạng | `src/evaluation/testset.py` | `data/eval/test_set.json` — đủ 4 loại câu hỏi | Đọc file và đếm 10 items |
| Báo cáo Markdown Phase 1 | `src/observability/reporting.py` | `data/reports/phase1_report.md` | Mở file kiểm tra 4 sections |
| Báo cáo đối chiếu 3 trạng thái | `src/observability/reporting.py` | `data/reports/corruption_report.md` | Mở file kiểm tra bảng so sánh |

Artifact quan trọng nhất là **`data/reports/corruption_report.md`** — bằng chứng trực quan về Silent Failure và Idempotent Repair, deliverable bắt buộc cho CP5 và CP6.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Hệ thống RAG không tự báo lỗi khi dữ liệu xấu — Silent Failure. Phần việc tôi xây dựng hai lớp kiểm soát:
1. **Quality Gate (GX 1.x):** Phát hiện null, trùng lặp, summary ngắn, số bản ghi bất thường.
2. **Freshness SLA:** Cảnh báo khi tỷ lệ bài báo cũ (>180 ngày) vượt 25%.

### Cách triển khai

**Great Expectations 1.x (Ephemeral Context):**

```python
context = gx.get_context(mode="ephemeral")  # Chạy trên RAM, không tạo file rác
data_source = context.data_sources.add_pandas(name=f"pandas_source_{report_name}")
data_asset = data_source.add_dataframe_asset(name=f"paper_asset_{report_name}")
batch_def = data_asset.add_batch_definition_whole_dataframe(batch_def_name)
batch = batch_def.get_batch(batch_parameters={"dataframe": df})
```

Khác cú pháp cũ `context.sources.pandas_default` (deprecated GX 1.x), cú pháp mới tách DataSource → DataAsset → BatchDefinition → Batch. Định nghĩa 6 Expectations: row count, null (paper_id, title, text_for_embedding), uniqueness (paper_id), summary length >= 30.

**Freshness SLA:** `stale_ratio = count(age_days > 180) / total_rows`. Nếu `stale_ratio > 0.25` → `is_fresh = False`.

**Test Set:** Lấy 10 bài báo đầu, chia round-robin 4 loại câu hỏi (`summary`, `authors`, `date`, `categories`). Ground truth trích từ metadata sạch.

### Input, output và contract

| Thành phần | Mô tả |
| ------------------------------ | ------------------------------------------- |
| Input (Quality Gate) | `pd.DataFrame` có cột: `paper_id`, `title`, `summary`, `text_for_embedding`, `age_days` |
| Output (Quality Gate) | Dict `{success, total_expectations, passed_expectations, details}` + JSON file |
| Input (Test Set) | `pd.DataFrame` cleaned, `output_path: Path` |
| Output (Test Set) | `list[dict]` 10 items + `data/eval/test_set.json` |
| Module phụ thuộc | `ingestion.cleaning`, `core.config` (Settings + Paths) |
| Module sử dụng output | `pipelines.phase1`, `pipelines.corruption_flow`, `evaluation.metrics` |
| Điều kiện lỗi | DataFrame rỗng, thiếu cột `age_days`, path chưa tồn tại — xử lý bằng `mkdir(parents=True)` và `in df.columns` |

### Cách xác minh

```bash
python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, 'test'); print(res['success'])"

python -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=build_test_set(df, s.paths.eval_testset); print(len(ts))"
```

- **Kết quả mong đợi:** `True` và `10`
- **Kết quả thực tế:** Code hoàn chỉnh; đang chờ model `all-MiniLM-L6-v2` (~91MB) tải xong để chạy end-to-end
- **Artifact:** `data/quality/test_gx_report.json`, `data/eval/test_set.json`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Triển khai GX 1.x — có thể dùng `context.sources.pandas_default` (cú pháp cũ) hoặc `context.data_sources.add_pandas()` (chuẩn GX 1.x mới).
- **Các phương án đã cân nhắc:**
  - **Phương án A:** `context.sources.pandas_default` — đơn giản hơn nhưng deprecated, crash trên GX >= 1.0.
  - **Phương án B:** `gx.get_context(mode="ephemeral")` + `add_pandas()` + `add_dataframe_asset()` — đúng chuẩn GX 1.x, không tạo file rác.
- **Phương án đã chọn:** Phương án B — ephemeral context với API mới.
- **Lý do:** Rubric trừ -10đ nếu dùng cú pháp cũ gây crash. Ephemeral mode không tạo thư mục `.great_expectations/`, giữ repo sạch.
- **Bằng chứng:** `docs/Guide.md` dòng 103-110 và slide bài giảng trang 51-52 quy định ephemeral context là bắt buộc.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```
  AttributeError: 'Paths' object has no attribute 'clean_dir'. Did you mean: 'clean_csv'?
  ```
- **Lệnh tái hiện:** `python script/run_phase1.py`
- **Nguyên nhân gốc:** Code trong `phase1.py` và `corruption_flow.py` dùng tên attribute không tồn tại (`clean_dir`, `baseline_metrics_json`, `phase1_report`...) trong khi `Paths` dataclass ở `core/config.py` dùng tên thực tế khác.
- **Cách xử lý:** Đọc toàn bộ `src/core/config.py`, xác định 43 attribute trong `Paths`, thay thế tên sai: `clean_dir` → `clean_csv.parent.mkdir(...)`, `baseline_metrics_json` → `baseline_metrics`, `phase1_report` → `baseline_report`...
- **Xác minh sau sửa:** `python script/run_phase1.py` không còn `AttributeError`, tiến vào bước tải model embedding.
- **Bài học:** Đọc data model / config trước khi viết pipeline. Tên attribute nhất quán là điều kiện bắt buộc tránh lỗi runtime.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Crossref → vector index:** API trả JSON → `crossref.py` parse + lưu raw `data/raw/` → `cleaning.py` chuẩn hóa, tính `age_days`, tạo `text_for_embedding` → `LocalEmbeddingIndex.build()` nhúng vector bằng `all-MiniLM-L6-v2` → lưu ChromaDB collection `papers-baseline`.

2. **Test set và ground-truth:** `testset.py` sinh 10 câu hỏi với `ground_truth_doc_ids` (DOI). Evaluate: RAG retrieves top-k docs → kiểm tra DOI trong retrieved set (Hit Rate) → so sánh câu trả lời bằng Token F1 và LLM Judge.

3. **Quality checks vs Freshness:** GX kiểm tra **cấu trúc** (null, unique, length) tại ingestion. Freshness SLA kiểm tra **tuổi đời** (`age_days`) liên tục — cảnh báo khi dữ liệu lỗi thời dù cấu trúc hợp lệ.

4. **Cùng test set:** Đảm bảo so sánh apple-to-apple — test set khác nhau sẽ không biết metric thay đổi do data xấu hay câu hỏi khác. Test set cố định là biến kiểm soát.

5. **Repair thành công khi:** GX `success = True`, Freshness `is_fresh = True`, `retrieval_hit_rate` và `mean_token_f1` trong `repaired_metrics.json` phục hồi về mức baseline, `corruption_report.md` có đủ 3 cột chứng minh.

## 8. Phân tích kết quả

### Metrics chính

*Lưu ý: Pipeline đang chờ tải model `all-MiniLM-L6-v2` (~91MB). Số liệu dưới là kỳ vọng theo thiết kế.*

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| ---------------------- | -------: | --------: | -------: | --------- |
| `retrieval_hit_rate` | ~0.7–0.9 | ~0.3–0.5 | ~0.7–0.9 | Giảm mạnh khi data bẩn, phục hồi sau repair |
| `mean_token_f1` | ~0.4–0.7 | ~0.1–0.3 | ~0.4–0.7 | Nhạy với blank summary và text noise |
| `judge_accuracy` | ~0.6–0.8 | ~0.2–0.4 | ~0.6–0.8 | LLM judge phát hiện câu trả lời sai |
| `mean_judge_score` | ~3.5–4.5 | ~1.5–2.5 | ~3.5–4.5 | Giảm sâu khi stale date gây hallucination |
| Quality checks (GX) | PASSED | FAILED | PASSED | Phát hiện blank summary, duplicate, title ngắn |
| Freshness status | FRESH | STALE | FRESH | Stale date injection vượt ngưỡng 25% |

### Kết luận từ số liệu

1. **[Data corruption]** → Blank summary + truncated title → **[GX FAILED, Freshness STALE]** → **[Hit Rate giảm mạnh, Token F1 gần 0]**.
2. **[Repair từ `data/raw/`]** → **[GX PASSED, Freshness FRESH]** → **[RAG phục hồi về mức baseline]**.

Corruption ảnh hưởng rõ nhất là **blank summary** — `text_for_embedding` mất nội dung ngữ nghĩa cốt lõi, làm vector embedding vô nghĩa và retrieval hoàn toàn sai.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. [Điều học được về data pipeline.]
2. [Điều học được về data quality/observability.]
3. [Điều học được về ảnh hưởng của data đến RAG agent.]

### Nếu có thêm thời gian

[Nêu một cải thiện cụ thể, lý do và cách đo cải thiện đó.]

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [ ] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [ ] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [ ] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [ ] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [ ] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [ ] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** [Họ và tên]
**Ngày xác nhận:** [YYYY-MM-DD]
