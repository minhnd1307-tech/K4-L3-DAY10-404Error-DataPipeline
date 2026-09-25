# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                             |
| ------------------ | --------------------------------------------------------------------- |
| Họ và tên       | Hoàng Bích Ngọc                                                      |
| MSSV               | 2A202602766                                                           |
| Email              | hoangngoc12022004@gmail.com                                          |
| Khóa/Lớp         | AI-ENGINEER-K4 / L3A                                                  |
| Tên nhóm         | 404Error                                                              |
| Vai trò chính    | Observability & Evaluation Lead                                       |
| Repository         | https://github.com/minhnd1307-tech/K4-L3-DAY10-404Error-DataPipeline |
| Ngày hoàn thành | 2026-09-25                                                            |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | :---: |
| Data Quality Gate (GX 1.x) | `src/observability/quality.py` — `run_data_quality_checks()` | `pd.DataFrame` (cleaned), `Settings`, `report_name` | `data/quality/{name}_quality_report.json` + dict validation | Hoàn thành |
| Freshness SLA Monitoring | `src/observability/quality.py` — `build_freshness_report()` | `pd.DataFrame` (có cột `age_days`, `published`), `report_path` | `data/quality/freshness_report.json` với `is_fresh`, `stale_ratio` | Hoàn thành |
| Benchmark Test Set | `src/evaluation/testset.py` — `build_test_set()` | `pd.DataFrame` (cleaned), `output_path` | `data/eval/test_set.json` — 10 câu hỏi Ground Truth | Hoàn thành |
| Phase 1 Markdown Report | `src/observability/reporting.py` — `generate_phase1_report()` | `source_summary`, `metrics`, `quality`, `freshness` dicts | `data/reports/phase1_report.md` — 4 sections | Hoàn thành |
| Corruption Comparison Report | `src/observability/reporting.py` — `generate_corruption_report()` | Baseline/corrupted/repaired metrics + quality + freshness | `data/reports/corruption_report.md` — bảng 3 trạng thái | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Sửa lỗi `AttributeError: 'Paths' object has no attribute 'clean_dir'` — mapping đúng tên path từ `config.py` | Pipeline Lead — `src/pipelines/phase1.py`, `corruption_flow.py` | Cả hai pipeline khởi chạy được, không còn AttributeError |
| Gỡ lỗi tương thích môi trường package | Toàn nhóm — môi trường | Môi trường in ra "Môi trường sẵn sàng" |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Triển khai GX 1.x ephemeral context, 6 Expectations | `src/observability/quality.py` | `data/quality/baseline_quality_report.json` | Chạy lệnh verify GX sau khi pipeline hoàn tất |
| Freshness SLA (ngưỡng 180 ngày, 25%) | `src/observability/quality.py` | `data/quality/freshness_report.json` với `is_fresh=True` | Kiểm tra JSON sau khi chạy pipeline |
| Sinh 10 câu hỏi Ground Truth đa dạng | `src/evaluation/testset.py` | `data/eval/test_set.json` — đủ 4 loại câu hỏi | Đọc file và đếm 10 items |
| Báo cáo Markdown Phase 1 | `src/observability/reporting.py` | `data/reports/phase1_report.md` | Mở file kiểm tra 4 sections |
| Báo cáo đối chiếu 3 trạng thái | `src/observability/reporting.py` | `data/reports/corruption_report.md` | Mở file kiểm tra bảng so sánh |

Artifact quan trọng nhất là **`data/reports/corruption_report.md`** — bằng chứng trực quan về Silent Failure và Idempotent Repair, deliverable bắt buộc cho CP5 và CP6.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Hệ thống RAG không tự báo lỗi khi dữ liệu xấu — hiện tượng **Silent Failure**. Phần việc tôi xây dựng hai lớp kiểm soát:
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
Khác cú pháp cũ `context.sources.pandas_default` (deprecated GX 1.x), cú pháp mới tách DataSource $\rightarrow$ DataAsset $\rightarrow$ BatchDefinition $\rightarrow$ Batch. Định nghĩa 6 Expectations: row count, null (`paper_id`, `title`, `text_for_embedding`), uniqueness (`paper_id`), summary length >= 30.

**Freshness SLA:** `stale_ratio = count(age_days > 180) / total_rows`. Nếu `stale_ratio > 0.25` $\rightarrow$ `is_fresh = False`.

**Test Set:** Lấy bài báo, chia round-robin 4 loại câu hỏi (`summary`, `authors`, `date`, `categories`). Ground truth trích từ metadata sạch và gán `ground_truth_doc_ids`.

### Input, output và contract

| Thành phần | Mô tả |
| ------------------------------ | ------------------------------------------- |
| Input (Quality Gate) | `pd.DataFrame` có cột: `paper_id`, `title`, `summary`, `text_for_embedding`, `age_days` |
| Output (Quality Gate) | Dict `{success, total_expectations, passed_expectations, details}` + JSON file |
| Input (Test Set) | `pd.DataFrame` cleaned, `output_path: Path` |
| Output (Test Set) | `list[dict]` 10 items + `data/eval/test_set.json` |
| Module phụ thuộc | `ingestion.cleaning`, `core.config` (Settings + Paths) |
| Module sử dụng output | `pipelines.phase1`, `pipelines.corruption_flow`, `evaluation.metrics` |

### Cách xác minh

```bash
python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, 'test'); print(res['success'])"

python -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=build_test_set(df, s.paths.eval_testset); print(len(ts))"
```
- **Kết quả xác minh:** In ra `True` và `10`.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Triển khai GX 1.x — có thể dùng `context.sources.pandas_default` (cú pháp cũ) hoặc `context.data_sources.add_pandas()` (chuẩn GX 1.x mới).
- **Các phương án đã cân nhắc:**
  - *Phương án A:* `context.sources.pandas_default` — đơn giản hơn nhưng deprecated, crash trên GX >= 1.0.
  - *Phương án B:* `gx.get_context(mode="ephemeral")` + `add_pandas()` + `add_dataframe_asset()` — đúng chuẩn GX 1.x, không tạo file rác.
- **Phương án đã chọn:** Phương án B — ephemeral context với API mới.
- **Lý do:** Rubric trừ -10đ nếu dùng cú pháp cũ gây crash. Ephemeral mode không tạo thư mục `.great_expectations/`, giữ repo sạch sẽ.
- **Bằng chứng:** `docs/Guide.md` dòng 103-110 và slide bài giảng trang 51-52 quy định ephemeral context là bắt buộc.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  AttributeError: 'Paths' object has no attribute 'clean_dir'. Did you mean: 'clean_csv'?
  ```
- **Lệnh tái hiện:** `python script/run_phase1.py`
- **Nguyên nhân gốc:** Code trong `phase1.py` và `corruption_flow.py` dùng tên attribute không tồn tại (`clean_dir`, `baseline_metrics_json`, `phase1_report`...) trong khi `Paths` dataclass ở `core/config.py` dùng tên thực tế khác.
- **Cách xử lý:** Đọc toàn bộ `src/core/config.py`, xác định 43 attribute trong `Paths`, thay thế tên sai: `clean_dir` $\rightarrow$ `clean_csv.parent.mkdir(...)`, `baseline_metrics_json` $\rightarrow$ `baseline_metrics`, `phase1_report` $\rightarrow$ `baseline_report`...
- **Xác minh sau sửa:** `python script/run_phase1.py` không còn `AttributeError`, tiến vào bước chạy trơn tru end-to-end.
- **Bài học:** Đọc data model / config trước khi viết pipeline. Tên attribute nhất quán là điều kiện bắt buộc tránh lỗi runtime.

---

## 7. Hiểu biết về luồng end-to-end

1. **Crossref $\rightarrow$ vector index:** API trả JSON $\rightarrow$ `crossref.py` parse + lưu raw `data/raw/` $\rightarrow$ `cleaning.py` chuẩn hóa, tính `age_days`, tạo `text_for_embedding` $\rightarrow$ `LocalEmbeddingIndex.build()` nhúng vector bằng `all-MiniLM-L6-v2` $\rightarrow$ lưu ChromaDB collection `papers-baseline`.
2. **Test set và ground-truth:** `testset.py` sinh 10 câu hỏi với `ground_truth_doc_ids` (DOI). Khi đánh giá: RAG retrieves top-k docs $\rightarrow$ kiểm tra DOI trong retrieved set (Hit Rate) $\rightarrow$ so sánh câu trả lời bằng Token F1 và LLM Judge.
3. **Quality checks vs Freshness:** GX kiểm tra **cấu trúc** (null, unique, length) tại ingestion. Freshness SLA kiểm tra **tuổi đời** (`age_days`) liên tục — cảnh báo khi dữ liệu lỗi thời dù cấu trúc hợp lệ.
4. **Cùng test set:** Đảm bảo so sánh khách quan (Controlled Experiment) — test set khác nhau sẽ không biết metric thay đổi do data xấu hay câu hỏi khác. Test set cố định là biến kiểm soát.
5. **Repair thành công khi:** GX `success = True`, Freshness `is_fresh = True`, `retrieval_hit_rate` và `mean_token_f1` trong `repaired_metrics.json` phục hồi về mức baseline, `corruption_report.md` có đủ 3 cột chứng minh.

---

## 8. Phân tích kết quả

### Metrics thực tế

| Metric/signal | 1. Baseline | 2. Corrupted | 3. Repaired | Nhận xét |
| ---------------------- | :---: | :---: | :---: | :--- |
| `retrieval_hit_rate` | `1.0000` | `0.9000` | `1.0000` | Giảm do mất tài liệu/nhiễu context, phục hồi 100% sau repair |
| `mean_token_f1` | `0.2754` | `0.1577` | `0.2754` | Nhạy với blank summary và text noise; phục hồi hoàn hảo |
| `judge_accuracy` | `0.2000` | `0.1000` | `0.2000` | LLM judge phát hiện câu trả lời hallucination khi data bẩn |
| `mean_judge_score` | `1.80` | `1.50` | `2.10` | Lấy lại phong độ đánh giá sau khi phục hồi dữ liệu sạch |
| Quality checks (GX) | ✅ PASSED | ❌ FAILED | ✅ PASSED | Báo động tức thì khi có duplicate và blank summary |
| Freshness status | 🟢 FRESH | 🔴 STALE | 🟢 FRESH | Stale date injection vượt ngưỡng 25% (36.36%) $\rightarrow$ Cảnh báo |

### Kết luận từ số liệu

1. **[Data corruption]** $\rightarrow$ Blank summary + truncated title $\rightarrow$ **[GX FAILED, Freshness STALE]** $\rightarrow$ **[Hit Rate giảm từ 1.0000 xuống 0.9000, Token F1 giảm 42.7%]**.
2. **[Repair từ `data/raw/`]** $\rightarrow$ **[GX PASSED, Freshness FRESH]** $\rightarrow$ **[RAG phục hồi về mức baseline]**.

Corruption ảnh hưởng rõ nhất là **blank summary** — `text_for_embedding` mất nội dung ngữ nghĩa cốt lõi, làm vector embedding vô nghĩa và retrieval trích xuất sai tài liệu.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về Data Pipeline:** Pipeline phải luôn tuân thủ nguyên tắc Raw Data Preservation để làm điểm tựa khôi phục (Single Source of Truth), đảm bảo tính Idempotent có thể tái lập bất kỳ lúc nào.
2. **Về Data Observability:** Great Expectations 1.x đóng vai trò như một chốt kiểm dịch (Quality Gate) thiết yếu. Nó ngăn chặn dữ liệu rác tiến sâu vào vector space, chặn đứng hiện tượng Silent Failure trước khi người dùng cuối phát hiện.
3. **Về Tác động của Data đến RAG:** Mô hình ngôn ngữ lớn (LLM) và vector index cực kỳ nhạy cảm với dữ liệu bẩn (Garbage In - Garbage Out). Dù mô hình embedding tốt đến đâu, nếu dữ liệu thiếu hụt hoặc bị cắt cụt thì Retrieval Hit Rate và độ chính xác của câu trả lời sẽ sụt giảm nghiêm trọng.

### Nếu có thêm thời gian

Nhóm sẽ xây dựng cơ chế cảnh báo tự động qua Slack/Discord Webhook tích hợp trực tiếp vào GX checkpoint, kết hợp tự động kích hoạt tiến trình Idempotent Self-Healing ngay trong thời gian thực khi Quality Gate phát hiện vi phạm mà không cần can thiệp thủ công.

---

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Hoàng Bích Ngọc  
**Ngày xác nhận:** 2026-09-25  
