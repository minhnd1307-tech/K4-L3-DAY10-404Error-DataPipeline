# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Dũng                     |
| MSSV               | [Điền MSSV của Dũng]      |
| Khóa/Lớp         | AI-ENGINEER-K4           |
| Tên nhóm         | [Điền tên nhóm của bạn]   |
| Vai trò chính    | Trưởng nhóm / Pipeline Lead & Integrator |
| Repository         | K4-L3-DAY10-TenNhom-DataPipeline |
| Ngày hoàn thành | 2026-09-25               |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | :---: |
| Pipeline Settings & Config | `src/core/config.py`, `.env` | Environment variables, `.env.example` | Object `Settings`, `Paths` chuẩn hóa | Hoàn thành |
| Baseline Pipeline Orchestration | `src/pipelines/phase1.py` (`main()`) | Dữ liệu từ Ingestion, Cleaning, ChromaDB, Testset | `phase1_report.md`, `baseline_metrics.json`, `papers-baseline` collection | Hoàn thành |
| Corruption & Repair Orchestration | `src/pipelines/corruption_flow.py` (`main()`) | Clean dataset, raw records snapshot, corruption suite | `corruption_report.md`, `corrupted_metrics.json`, `repaired_metrics.json` | Hoàn thành |
| Pipeline Entrypoints | `script/run_phase1.py`, `script/run_corruption_flow.py` | Lệnh CLI từ terminal | Luồng thực thi end-to-end hoàn chỉnh | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --------- | ----------------------------- | ------- |
| Thống nhất Contract & Schema | Hỗ trợ Khánh (`cleaning.py`), Minh (`index.py`), Ngọc (`quality.py`) | Định hình bộ cột chuẩn (`paper_id`, `text_for_embedding`, `age_days`, v.v.) |
| Quản lý Git & Branching | Cả nhóm 4 thành viên | Thiết lập branch, review pull request và bảo đảm 100% commit vào nhánh `main` |
| Quản trị Bí mật & Môi trường | Cả nhóm | Thiết lập `.env` bảo mật, không để lộ API Key lên GitHub |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ---------------- | ------------- |
| Thiết lập cấu hình hệ thống | `src/core/config.py`, `.env` | Định nghĩa toàn bộ đường dẫn artifact, thông số LLM provider, Chroma collection | `python -c "from core.config import load_settings; s=load_settings(); print(s.model_name)"` |
| Điều phối Baseline Pipeline | `src/pipelines/phase1.py` | Kết nối 7 bước: Ingestion -> Clean -> Index -> Testset -> Eval -> Quality -> Report | `python script/run_phase1.py` |
| Điều phối Corruption & Repair | `src/pipelines/corruption_flow.py` | Kết nối 6 bước: Load baseline -> Corruption -> Corrupted Eval -> Idempotent Repair -> Comparison Table | `python script/run_corruption_flow.py` |

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Xây dựng khung điều phối (orchestration framework) kết nối các mắt xích rời rạc của các thành viên trong nhóm thành một hệ thống dữ liệu tự động, nhất quán, có khả năng xử lý ngoại lệ và tự phục hồi (Idempotent).

### Cách triển khai
1. **Pha 1 (`phase1.py`):** Thiết lập luồng tuyến tính 7 bước có log thời gian chi tiết cho từng giai đoạn. Sử dụng `LocalEmbeddingIndex` và `evaluate_pipeline` để đo đạc metrics nền.
2. **Pha 2 (`corruption_flow.py`):** Thực thi luồng tiêm lỗi có chủ đích, đánh giá sự sụt giảm chỉ số RAG (Silent Failure), ghi nhận cảnh báo chất lượng từ Great Expectations 1.x, sau đó kích hoạt **Idempotent Repair** từ nguồn snapshot nguyên thủy `data/raw/crossref_records.json` để khôi phục hoàn toàn chỉ số và tính đúng đắn của dữ liệu.

### Input, output và contract

| Thành phần | Mô tả |
| ---------- | ----- |
| Input | Raw snapshot (`data/raw/`), biến môi trường `.env` |
| Output | Metrics JSON (`baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`), Markdown Reports |
| Module phụ thuộc | `ingestion`, `retrieval`, `evaluation`, `observability` |
| Module sử dụng output | Scripts thực thi `script/run_*.py`, báo cáo nhóm `group_report.md` |

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương thức phục hồi dữ liệu khi Data Quality Gate phát hiện dữ liệu bị hỏng trong `corruption_flow.py`.
- **Các phương án đã cân nhắc:**
  1. *Phương án A:* Gọi lại live API của Crossref để tải dữ liệu mới về.
  2. *Phương án B:* Khôi phục sạch từ bản sao lưu nguyên bản `data/raw/crossref_records.json` (Raw Preservation).
- **Phương án đã chọn:** Phương án B (Tái tạo từ Raw Snapshot ban đầu).
- **Lý do:** Đảm bảo tính **Idempotent** (chạy lại bao nhiêu lần kết quả vẫn đồng nhất 100%), không phụ thuộc vào kết nối mạng bên ngoài, tránh lỗi rate-limit `429 Too Many Requests` từ Crossref và đảm bảo cùng một tập dữ liệu chuẩn để đối chiếu khách quan với baseline ban đầu.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Môi trường ban đầu kích hoạt bị trỏ nhầm vào Python 3.10 thay vì Python 3.12, dẫn đến không tương thích với cấu hình `requires-python = ">=3.11,<3.14"` trong `pyproject.toml`.
- **Nguyên nhân gốc:** Lệnh `python -m venv` mặc định gọi binary Python 3.10 trên máy tính.
- **Cách xử lý:** Sử dụng Windows Python Launcher chỉ định chính xác phiên bản `py -3.12 -m venv .venv` và kích hoạt lại.
- **Cách xác minh sau khi sửa:** Chạy `python --version` in ra `Python 3.12.3`, đáp ứng hoàn hảo yêu cầu của dự án.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Dữ liệu JSON từ Crossref API được tải về và lưu nguyên bản tại `data/raw/` (Raw Preservation). Sau đó, module `cleaning.py` loại bỏ thẻ JATS XML, chuẩn hóa whitespace, tính `age_days` và ghép trường ngữ cảnh `text_for_embedding`. Chuỗi này được mô hình `all-MiniLM-L6-v2` nhúng thành vector và nạp vào collection của ChromaDB cùng các trường metadata truy vấn.
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   File `test_set.json` chứa 10 câu hỏi chuẩn phủ 4 dạng (`summary`, `authors`, `date`, `categories`). Mỗi câu hỏi có `ground_truth` và `ground_truth_doc_ids`. Khi Agent truy vấn, `retrieval_hit_rate` đo tỷ lệ câu hỏi mà ChromaDB lấy được đúng tài liệu chứa đáp án, còn `Token F1` và `LLM Judge` đo độ chính xác và tính trung thực của câu trả lời sinh ra.
3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   Quality checks (Great Expectations 1.x) kiểm tra tính toàn vẹn của cấu trúc dữ liệu (Schema, null values, uniqueness, length). Còn Freshness monitoring giám sát khía cạnh thời gian (độ mới của dữ liệu): nếu tỷ lệ bài báo quá 180 ngày vượt quá 25%, hệ thống cảnh báo dữ liệu đã bị mốc (stale) dù cấu trúc bảng vẫn hoàn toàn hợp lệ.
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để đảm bảo tính khách quan và khoa học (Controlled Experiment). Chỉ khi giữ cố định "thước đo" (Test Set và Ground Truth) thì sự thay đổi trong các chỉ số (Hit Rate, F1, LLM Judge Score) mới phản ánh chính xác tác động tiêu cực của dữ liệu lỗi và hiệu quả phục hồi của cơ chế Idempotent Repair.
5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Repair thành công khi:
   - File `repaired_quality_report.json` đạt `success=True` (vượt qua toàn bộ 4 expectations của GX 1.x).
   - Chỉ số trong `repaired_metrics.json` (Hit Rate, Token F1, Judge Accuracy) hồi phục hoàn toàn về mức xấp xỉ hoặc bằng với `baseline_metrics.json`.
   - Bảng so sánh trong `corruption_report.md` ghi nhận tỷ lệ phục hồi đạt 100%.

---

## 8. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.

**Họ và tên:** Dũng  
**Ngày xác nhận:** 2026-09-25  
