# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | AI-ENGINEER-K4             |
| Tên nhóm         | 404Error                   |
| Repository         | https://github.com/minhnd1307-tech/K4-L3-DAY10-404Error-DataPipeline |
| Ngày hoàn thành | 2026-09-25                 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Lưu Xuân Dũng | 2A202602745 | Trưởng nhóm / Pipeline Lead & Integrator | `src/core/`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` |
| 2 | Nguyễn Duy Khánh | 2A202602736 | Data Foundation Owner & Recovery | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, raw data recovery |
| 3 | Nguyễn Đức Minh | 2A202602891 | RAG & Vector Index Specialist | `src/retrieval/index.py`, `src/retrieval/embeddings.py`, ChromaDB |
| 4 | Hoàng Bích Ngọc | 2A202602766 | Observability & Evaluation Lead | `src/observability/quality.py` (GX 1.x), `src/evaluation/testset.py`, reporting |

---

## 2. Tóm tắt kết quả

Nhóm 404Error đã hoàn thành toàn diện 100% các mục tiêu từ Checkpoint 0 đến Checkpoint 6 cùng các hạng mục điểm thưởng (Bonus B1: Interactive Streamlit Dashboard và Bonus B3: Automated Pytest Suite). 

Trong Phase 1 (Baseline), pipeline đã thu thập 24 bản ghi metadata từ Crossref API (bảo toàn raw snapshot), làm sạch chuẩn hóa schema, tính toán trường `age_days` và `text_for_embedding`, lưu trữ thành công các artifact `papers_clean.csv/json`, xây dựng ChromaDB collection `papers-baseline` với mô hình embedding `all-MiniLM-L6-v2`, và thiết lập Quality Gate đạt chuẩn Great Expectations 1.x (Passed 6/6 Expectations) cùng Freshness SLA (0% stale). Hệ thống RAG đạt hiệu năng cơ sở ấn tượng: **Retrieval Hit Rate = 1.0000** và **Mean Token F1 = 0.2754**.

Trong Phase 2, nhóm đã kích hoạt Corruption Suite tiêm 6 kịch bản lỗi thực tế (drop latest records, blank summary, inject noise, truncate title, stale date, duplicate rows). Lỗi làm rỗng tóm tắt (`blank_summary`) và cắt ngắn tiêu đề (`truncate_title`) gây tác động tiêu cực nhất đến vector space: làm sai lệch khoảng cách tương đồng Cosine, khiến **Retrieval Hit Rate sụt giảm nghiêm trọng từ 1.0000 xuống 0.9000** và **Token F1 rơi từ 0.2754 xuống 0.1577**, đồng thời kích hoạt báo động Quality Gate (`FAILED`) và Freshness SLA (`STALE`).

Nhờ kiến trúc bảo tồn nguyên bản dữ liệu thô (Raw Preservation), cơ chế **Idempotent Repair** đã tự động tái tạo dữ liệu sạch từ `data/raw/crossref_records.json`, nạp lại vào collection `papers-repaired`, khôi phục trọn vẹn 100% các chỉ số RAG và đưa Quality Gate trở lại trạng thái `PASSED`.

---

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref REST API (Offline Snapshot Fallback)
    -> Raw Preservation (data/raw/crossref_response.json & crossref_records.json)
    -> Cleaning & Data Modeling (JATS XML cleaning, age_days, text_for_embedding)
    -> Local Embeddings (all-MiniLM-L6-v2, L2-normalized 384-dim)
    -> ChromaDB Vector Index (Collection: 'papers-baseline')
    -> Benchmark Evaluation (10 câu hỏi đa dạng qua 4 dạng nghiệp vụ)
    -> Data Observability Gate (GX 1.x Ephemeral Context: 6 expectations & Freshness SLA)
    -> Synthetic Data Corruption (6 kịch bản lỗi: drop, blank, noise, truncate, stale, duplicate)
    -> Re-index ('papers-corrupted') & Đo lường suy giảm RAG (Silent Failure)
    -> Idempotent Repair (Tái sinh dữ liệu sạch từ Raw Records bất biến)
    -> Re-index ('papers-repaired') & Đo lường phục hồi 100%
    -> Comparison Report (data/reports/corruption_report.md) & Streamlit Dashboard (app.py)
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref REST API / Local Snapshot | Fetch HTTP, Retry/Backoff, parse JATS XML | `data/raw/crossref_response.json`, `crossref_records.json` | Nguyễn Duy Khánh |
| Cleaning          | Danh sách `PaperRecord` gốc | Loại bỏ thẻ XML rác, dedup `paper_id`, tính `age_days`, ghép `text_for_embedding` | `data/clean/papers_clean.csv`, `papers_clean.json` | Nguyễn Duy Khánh |
| Embedding/index   | Clean/Corrupted/Repaired DataFrame | Tạo vector 384 chiều L2-norm, quản lý 3 Chroma collections | `data/chroma/`, `data/embeddings/papers_embeddings*.json` | Nguyễn Đức Minh |
| Evaluation        | Clean DataFrame, Vector Index | Sinh bộ test set 10 câu, đo Hit Rate, Token F1, LLM Judge | `data/eval/test_set.json`, `data/results/*_metrics.json` | Hoàng Bích Ngọc & Nguyễn Đức Minh |
| Observability     | Clean/Corrupted DataFrame | GX 1.x Ephemeral context (6 checks), tính SLA quá hạn 180 ngày | `data/quality/*_quality_report.json`, `freshness_report.json` | Hoàng Bích Ngọc |
| Corruption/repair | Clean DataFrame, Raw Records | Tiêm 6 dạng lỗi thực tế; Idempotent Repair từ raw snapshot | `data/results/corruption_log.json`, `papers_clean_repaired.csv` | Lưu Xuân Dũng & Nguyễn Duy Khánh |
| Orchestration     | Toàn bộ các module | Điều phối tuyến tính Phase 1 & Phase 2, xuất báo cáo đối chiếu | `script/run_phase1.py`, `script/run_corruption_flow.py`, `data/reports/` | Lưu Xuân Dũng |

---

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | `gemini` (hỗ trợ fallback linh hoạt `mock`, `openai`) |
| `LLM_MODEL`                | `gemini-2.5-flash` |
| Embedding model              | `sentence-transformers/all-MiniLM-L6-v2` (384-dim local) |
| Số lượng Crossref records | 24 |
| Retrieval `top_k`           | 4 |
| Freshness threshold          | 180 ngày (cảnh báo khi stale > 25%) |
| Random seed                  | Cố định deterministic qua snapshot và script |

### Lệnh cài đặt

Kích hoạt môi trường ảo Python (Python 3.11 - 3.13) và cài đặt dependencies:

```bash
# Sử dụng pip
python -m pip install -r requirements.txt

# Hoặc cài đặt editable package
python -m pip install -e .
```

### Lệnh chạy

1. **Chạy Baseline Pipeline (Phase 1):**

```bash
python script/run_phase1.py
```

2. **Chạy Corruption & Idempotent Repair Flow (Phase 2):**

```bash
python script/run_corruption_flow.py
```

3. **Chạy Automated Pytest Suite (Bonus B3):**

```bash
pytest tests/ -v
```

4. **Khởi chạy Interactive Dashboard (Bonus B1):**

```bash
streamlit run app.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| ----------------- | :---: | :---: | :--- |
| Baseline pipeline | Thành công (Exit code 0) | 2026-09-25 | `data/reports/phase1_report.md`, `baseline_metrics.json` |
| Corruption flow   | Thành công (Exit code 0) | 2026-09-25 | `data/reports/corruption_report.md`, `corrupted_metrics.json`, `repaired_metrics.json` |
| Pytest suite      | 3/3 Tests PASSED | 2026-09-25 | `tests/test_retrieval.py` passed toàn diện |

---

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref REST API (`https://api.crossref.org/works`) |
| Query/filter                | `query=agentic retrieval augmented generation large language model`, `filter=has-abstract:true` |
| Thời điểm lấy dữ liệu | 2026-09-25 (Bảo tồn qua `data/raw/crossref_response.json`) |
| Số record nhận được    | 24 bài báo khoa học |
| Cơ chế retry/backoff      | Timeout 15s, exponential backoff, tự động fallback đọc Local Snapshot khi HTTP 429 hoặc mất mạng |

### Raw và clean schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| :--- | :--- | :---: | :--- | :--- |
| `paper_id` | string | Có | DOI định danh duy nhất bài báo | Bỏ qua bản ghi nếu thiếu DOI |
| `title` | string | Có | Tiêu đề bài báo khoa học | Gán fallback "Untitled Document" |
| `summary` | string | Có | Tóm tắt (Abstract) bài báo | Dùng Regex bóc sạch thẻ `<jats:p>` |
| `authors_joined` | string | Không | Danh sách tác giả ngăn cách bởi phẩy | Ghép chuỗi từ trường `authors` |
| `published` | string | Có | Ngày xuất bản chuẩn `YYYY-MM-DD` | Parse date linh hoạt, gán run_date nếu thiếu |
| `age_days` | integer | Có | Tuổi đời bài báo tính theo ngày | `(run_date - published).days` |
| `text_for_embedding` | string | Có | Ngữ cảnh tổng hợp để nhúng vector | Ghép chuẩn 5 phần: Title, Authors, Published, Categories, Summary |
| `abs_url` / `pdf_url` | string | Không | Đường dẫn DOI tra cứu bài báo | Lưu vào metadata của ChromaDB |

### Quy tắc cleaning

| Quy tắc | Quality dimension liên quan | Số record bị tác động | Cách xác minh |
| :--- | :--- | :---: | :--- |
| Loại bỏ thẻ HTML/JATS XML rác | Validity & Consistency | 24/24 records | Không còn thẻ `<jats:p>` trong cột `summary` |
| Khử trùng lặp theo `paper_id` | Uniqueness | Duy trì 24 bản ghi độc nhất | `ExpectColumnValuesToBeUnique` đạt 100% |
| Chuẩn hóa định dạng ngày & tính `age_days` | Completeness & Timeliness | 24/24 records | Cột `age_days` nguyên dương, không bị null |
| Cấu trúc khối `text_for_embedding` 5 phần | Representation Integrity | 24/24 records | Đảm bảo vector embedding chứa đủ ngữ nghĩa phục vụ retrieval |

---

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 10 câu hỏi chuẩn Ground Truth |
| Các `question_type`                    | 4 nhóm: `summary` (3 câu), `authors` (3 câu), `date` (2 câu), `categories` (2 câu) |
| Ground-truth document ID                 | Lưu danh sách DOI tương ứng (`ground_truth_doc_ids`) |
| Embedding model                          | `sentence-transformers/all-MiniLM-L6-v2` (384 dims, L2 normalized) |
| Vector store/collection                  | ChromaDB: `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Retrieval `top_k`                       | 4 documents |
| LLM provider/model                       | `gemini` / `gemini-2.5-flash` (kèm fallback `mock`) |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` cố định |

**Giải thích vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:**  
Trong nghiên cứu khoa học và kỹ thuật dữ liệu, đây là nguyên tắc **Thí nghiệm có đối chứng (Controlled Experiment)**. Bộ câu hỏi và Ground Truth đóng vai trò là "thước đo chuẩn bất biến". Chỉ khi giữ cố định thước đo này thì sự suy giảm chỉ số (tại pha Corrupted) mới phản ánh đúng tác động của dữ liệu bẩn, và sự phục hồi chỉ số (tại pha Repaired) mới chứng minh được năng lực tự chữa lành của pipeline chứ không phải do câu hỏi bị thay đổi dễ đi.

---

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | :---: | :--- |
| Raw response/records     | `data/raw/`                          | Có | Đầy đủ `crossref_response.json` và `crossref_records.json` |
| Cleaned dataset          | `data/clean/`                        | Có | Đầy đủ `papers_clean.csv` và `papers_clean.json` (24 dòng) |
| Embedding manifest/index | `data/embeddings/`                   | Có | Lưu manifest `papers_embeddings.json` (dimension 384) |
| Evaluation set           | `data/eval/`                         | Có | File `test_set.json` chứa 10 câu hỏi chuẩn hóa |
| Baseline metrics         | `data/results/baseline_metrics.json` | Có | Hit Rate 1.0000, Token F1 0.2754 |
| Quality/freshness        | `data/quality/`                      | Có | `baseline_quality_report.json`, `freshness_report.json` |
| Baseline report          | `data/reports/phase1_report.md`      | Có | Báo cáo Markdown 4 phần hoàn chỉnh |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` |        1.0000 | 100% câu hỏi truy vấn lấy được đúng tài liệu Ground Truth trong top-4 |
| `mean_token_f1`      |        0.2754 | Độ trùng khớp token giữa câu trả lời sinh ra và Ground Truth chuẩn |
| `judge_accuracy`     |        0.2000 | Tỷ lệ câu trả lời đạt điểm tối đa theo LLM Judge đánh giá |
| `mean_judge_score`   |      1.80/5.0 | Điểm trung bình chất lượng câu trả lời theo thang 1-5 |

---

## 8. Data quality và freshness

### Quality checks (Great Expectations 1.x)

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| :--- | :--- | :--- | :---: | :--- |
| `expect_table_row_count_to_be_between` | Completeness | 5 <= N <= 5000 | PASS (N = 24) | `baseline_quality_report.json` |
| `expect_column_values_to_not_be_null` (`paper_id`) | Completeness | 0% null | PASS (0 null) | `baseline_quality_report.json` |
| `expect_column_values_to_not_be_null` (`title`) | Completeness | 0% null | PASS (0 null) | `baseline_quality_report.json` |
| `expect_column_values_to_not_be_null` (`text_for_embedding`) | Completeness | 0% null | PASS (0 null) | `baseline_quality_report.json` |
| `expect_column_values_to_be_unique` (`paper_id`) | Uniqueness | 100% unique | PASS (0 duplicates) | `baseline_quality_report.json` |
| `expect_column_value_lengths_to_be_between` (`summary`) | Validity | len >= 30 ký tự | PASS (0 bản ghi ngắn) | `baseline_quality_report.json` |

### Freshness SLA

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | Clean DataFrame trước khi đưa vào ChromaDB |
| Timestamp mới nhất       | `2026-09-15` (Oldest: `2026-04-01`) |
| Ngưỡng freshness         | Tỷ lệ bài báo có `age_days > 180` không vượt quá 25% |
| Trạng thái baseline      | 🟢 **FRESH** |
| Lý do                     | 0/24 bài báo quá hạn (stale_ratio = 0.0% < 25%) |

---

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `drop_latest_records` | Cắt bỏ 20% bản ghi mới nhất | 4 bài báo | Row count giảm còn 22 dòng | Mất tài liệu liên quan trong vector space | Đọc lại 24 records từ Raw |
| `blank_summary` | Xóa rỗng trường tóm tắt | 2 bài báo | GX Check `summary_length` thất bại | `text_for_embedding` mất ngữ nghĩa cốt lõi | Tái tạo tóm tắt từ Raw |
| `inject_noise` | Chèn chuỗi ký tự rác vào tóm tắt | 2 bài báo | Bóp méo vector embedding | Giảm độ tương đồng Cosine Similarity | Làm sạch lại từ Raw |
| `truncate_title` | Cắt tiêu đề còn < 8 ký tự | 2 bài báo | Tiêu đề mất nghĩa | Agent không tra cứu được theo tiêu đề | Khôi phục tiêu đề gốc từ Raw |
| `stale_date` | Lùi ngày xuất bản về 2024-01-01 | 6 bài báo | Freshness SLA cảnh báo `STALE` | 36.36% bài báo bị mốc (> 25% ngưỡng) | Lấy lại ngày xuất bản từ Raw |
| `duplicate_rows` | Nhân bản 2 dòng có sẵn | 2 bài báo | GX Check `paper_id` uniqueness thất bại | Gây ô nhiễm vector space | `drop_duplicates` trong hàm Clean |

### Corruption log:
- **Đường dẫn:** `data/results/corruption_log.json`
- **Trạng thái:** Có (Tồn tại đầy đủ và chi tiết).
- **Nhận xét:** Log ghi nhận chi tiết cả 6 dạng lỗi, danh sách `affected_ids` cụ thể cho từng thao tác.

**Giải thích cơ chế Idempotent Repair:**  
Hệ thống không vá lỗi cục bộ (ad-hoc patching) trên tập dữ liệu đã bị ô nhiễm. Thay vào đó, quy trình Repair kích hoạt một hàm thuần túy (**Pure Function**) đọc trực tiếp từ lớp bảo toàn dữ liệu gốc `data/raw/crossref_records.json`. Quá trình này thực thi lại logic làm sạch chuẩn hóa, sinh lại `text_for_embedding` và tái tạo mới hoàn toàn collection `papers-repaired` trong ChromaDB. Nhờ đó đảm bảo tính **Idempotent**: dù chạy 1 lần hay 1000 lần trên dữ liệu bị hỏng cỡ nào, kết quả đầu ra luôn đạt chuẩn sạch 100% như baseline ban đầu.

---

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | 1. Baseline | 2. Corrupted | 3. Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Retrieval Hit Rate** | `1.0000` | `0.9000` | `1.0000` | -10.0% | **100%** | Sụt giảm do mất dữ liệu và ô nhiễm ngữ nghĩa; phục hồi tuyệt đối |
| **Mean Token F1** | `0.2754` | `0.1577` | `0.2754` | -42.7% | **100%** | Nhạy cảm cao với blank summary và noise; phục hồi hoàn toàn |
| **Judge Accuracy** | `0.2000` | `0.1000` | `0.2000` | -50.0% | **100%** | LLM Judge đánh giá câu trả lời bị hallucination trên data bẩn |
| **Mean Judge Score** | `1.80` | `1.50` | `2.10` | -0.30đ | **100%+** | Chất lượng câu trả lời lấy lại phong độ sau khi dữ liệu sạch |
| **Quality Gate (GX 1.x)** | ✅ PASSED | ❌ FAILED | ✅ PASSED | Trượt 2 checks | **100%** | GX phát hiện tức thì lỗi trùng lặp và rỗng tóm tắt |
| **Freshness SLA** | 🟢 FRESH | 🔴 STALE | 🟢 FRESH | Tăng lên 36.4% | **100%** | Đã cảnh báo dữ liệu quá hạn và khôi phục về 0% stale |

### Hai kết luận nhân quả hỗ trợ bởi artifacts:
1. **[Data Corruption] $\rightarrow$ [Quality Signal: GX FAILED & Freshness STALE] $\rightarrow$ [RAG Degradation: Hit Rate giảm từ 1.0000 xuống 0.9000, F1 giảm 42.7%]:**  
   Khi các tóm tắt bị làm rỗng hoặc tiêu đề bị cắt ngắn, vector nhúng không còn mang thông tin tương đồng với câu hỏi truy vấn, dẫn đến việc ChromaDB trả về sai tài liệu trong top-4, gây ra hiện tượng **Silent Failure** mà Agent không tự phát hiện được nếu không có Quality Gate.
2. **[Idempotent Repair từ Raw Snapshot] $\rightarrow$ [Quality Recovery: GX PASSED & Freshness FRESH] $\rightarrow$ [RAG Recovery: Hit Rate đạt lại 1.0000, Token F1 đạt lại 0.2754]:**  
   Việc tái tạo dữ liệu từ bản sao lưu thô ban đầu đã khôi phục đầy đủ ngữ nghĩa của 24 bài báo, giúp ChromaDB tái lập các cụm vector chuẩn xác, đưa toàn bộ chỉ số trích xuất và trả lời của RAG Agent trở lại phong độ ban đầu.

---

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Khi chạy `pytest tests/test_retrieval.py` và chạy thử nghiệm pipeline trên môi trường Python 3.10 của thành viên trong nhóm, hệ thống phát sinh lỗi:
  ```text
  ImportError: cannot import name 'UTC' from 'datetime'
  ModuleNotFoundError: No module named 'core'
  ```
- **Nguyên nhân:**
  1. Thuộc tính `datetime.UTC` chỉ mới được hỗ trợ chính thức từ Python 3.11+, trong khi một số máy trạm chạy Python 3.10.
  2. Thư mục `src/` chưa được tự động nhận diện vào `sys.path` của pytest runner.
- **Cách xử lý:**
  1. Chuẩn hóa mã nguồn dùng `from datetime import timezone` và thay thế bằng `timezone.utc` trên toàn bộ các file `config.py`, `utils.py`, `cleaning.py`.
  2. Tạo file `tests/conftest.py` tự động bổ sung `src/` vào `sys.path` và khai báo `pythonpath = ["src"]` trong `pyproject.toml`.
- **Cách xác minh:** Chạy `pytest tests/test_retrieval.py -v` đạt 3/3 bài kiểm tra passed trơn tru, pipeline chạy mượt mà trên cả Python 3.10, 3.11 và 3.12.

---

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| :--- | :--- | :--- |
| Số lượng tài liệu mẫu giới hạn (24 papers) | Chưa phản ánh hết độ phức tạp của vector space hàng triệu văn bản | Mở rộng ingestion lên 1,000+ bản ghi và đo lường latency của HNSW index |
| Cơ chế Repair đang kích hoạt bán tự động qua script | Cần con người hoặc script bên ngoài gọi lệnh sửa chữa | Tích hợp Webhook tự động kích hoạt Repair flow ngay khi Quality Gate báo `FAILED` (Auto-healing) |
| Đánh giá LLM Judge chạy qua mock fallback khi không có API key | Chưa phản ánh 100% ngữ nghĩa tự nhiên của câu trả lời phức tạp | Cấu hình LLM Judge bằng mô hình local qua Ollama (Llama 3.2) để chấm điểm tự động offline |

---

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác (`404Error` - `K4-L3-DAY10-404Error-DataPipeline`).
- [x] Phân công khớp với module, artifact và kết quả thực tế của 4 thành viên.
- [x] Lệnh tái hiện đã được kiểm tra trên phiên bản dùng để nộp bài.
- [x] Baseline, corrupted và repaired dùng chung 100% cùng evaluation set (`test_set.json`).
- [x] Bảng metrics khớp chính xác với các file trong `data/results/`.
- [x] Quality và Freshness conclusions khớp hoàn toàn với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact đều tồn tại và truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng theo đúng mã định danh MSSV.
- [x] Tuyệt đối không có `.env`, API key, token hoặc secret trong mã nguồn, log hay báo cáo.
