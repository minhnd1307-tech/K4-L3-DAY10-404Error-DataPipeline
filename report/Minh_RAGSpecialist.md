# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Đức Minh                      |
| MSSV               | 2A202602891       |
| Khóa/Lớp         | K4/ L3A   |
| Tên nhóm         | 404Error         |
| Vai trò chính    | RAG & Vector Index Specialist (Thành viên 3) |
| Repository         | K4-L3-DAY10-404Error-DataPipeline |
| Ngày hoàn thành | 2026-09-25                |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ---------- |
| Vector Store & Embeddings Indexing | `src/retrieval/index.py` (`LocalEmbeddingIndex.build`, `search`, `lookup`) | Cleaned/Corrupted/Repaired DataFrame từ TV2 & TV4 | 3 ChromaDB collections (`papers-baseline`, `papers-corrupted`, `papers-repaired`) và các file manifest JSON | Hoàn thành |
| Local Embedding Model Engine | `src/retrieval/embeddings.py` (`MiniLMEmbeddings`) | Danh sách chuỗi `text_for_embedding` / Query string | Vector embedding 384 chiều đã được chuẩn hóa L2-norm (cosine metric) | Hoàn thành |
| Multi-Provider LLM Router & Agent | `src/retrieval/llm.py`, `src/retrieval/agent.py`, `src/retrieval/qa.py` | Settings cấu hình provider (`mock`, `gemini`, `openai`), câu hỏi kiểm thử | Trả về LLM client, QA Agent trang bị 2 tool (`semantic_search_papers`, `lookup_paper`) | Hoàn thành |
| Automated Pytest Suite (Bonus B3) | `tests/test_retrieval.py`, `tests/conftest.py` | Fixture mock data và cấu hình hệ thống | 3 bài unit test tự động kiểm thử toàn diện tầng Retrieval | Hoàn thành (+5đ Bonus) |
| Interactive Observability Dashboard (Bonus B1) | `app.py` | 3 Vector collections, reports JSON từ Phase 1 và Phase 2 | Giao diện Web trực quan tương tác semantic search, kiểm chứng Silent Failure và monitor Quality Gate | Hoàn thành (+5đ Bonus) |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --------- | ----------------------------- | ------- |
| Chuẩn hóa Schema dữ liệu nhúng | TV2 (Khánh) - `src/ingestion/cleaning.py` | Đảm bảo cột `text_for_embedding` chứa đầy đủ 5 trường thông tin ngữ nghĩa (Title, Authors, Published, Categories, Summary) theo chuẩn contract trước khi nạp vào ChromaDB |
| Tích hợp Baseline & Corruption Pipelines | TV1 (Dũng) - `src/pipelines/phase1.py` & `corruption_flow.py` | Cung cấp hàm build index và lookup để chạy trơn tru trong luồng đánh giá tự động |
| Khắc phục lỗi tương thích Python 3.10 / 3.11 | Cả nhóm - `src/core/config.py`, `src/core/utils.py` | Sửa `from datetime import UTC` thành `timezone.utc` để code chạy mượt trên mọi môi trường máy của nhóm |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ---------------- | ------------- |
| Xây dựng và kiểm thử Local Embedding Index | `src/retrieval/index.py`, `src/retrieval/embeddings.py` | Tạo thành công 3 collection ChromaDB độc lập, dimension 384 | `pytest tests/test_retrieval.py -v` |
| Xây dựng QA Agent & Extraction Logic | `src/retrieval/qa.py`, `src/retrieval/agent.py` | Trích xuất câu trả lời chuẩn xác (authors, date, summary) | Chạy thử nghiệm với `answer_question` |
| Phát triển Interactive Dashboard phục vụ Live Demo (CP6) | `app.py` | Ứng dụng Streamlit demo 3 trạng thái và quan sát Quality Gate | `streamlit run app.py` |

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Hệ thống RAG cần một không gian vector (Vector Space) chuẩn xác để ánh xạ ngữ nghĩa của các bài báo khoa học. Nếu không gian vector bị ô nhiễm (do dữ liệu rác, tiêu đề bị cắt cụt, hoặc bị trùng lặp), độ tương đồng Cosine giữa câu hỏi và tài liệu liên quan sẽ sụt giảm nghiêm trọng, dẫn đến việc Agent trích xuất nhầm tài liệu (hiện tượng **Silent Failure**). Ngoài ra, tầng Retrieval cần phải hỗ trợ cô lập hoàn toàn giữa 3 trạng thái (Baseline vs Corrupted vs Repaired) để so sánh khách quan.

### Cách triển khai
1. **Embedding Engine:** Sử dụng mô hình `all-MiniLM-L6-v2` từ thư viện `sentence-transformers`. Thiết lập `normalize_embeddings=True` ngay khi sinh vector để đảm bảo mọi vector đều có L2-norm bằng 1.0. Khi đó, phép tính Cosine Similarity tương đương với tích vô hướng (Dot Product), giúp tăng tốc độ tính toán tối đa.
2. **Quản lý ChromaDB Collections:** Khởi tạo `chromadb.PersistentClient` tại đường dẫn `data/chroma`. Thiết lập không gian metric `{"hnsw": {"space": "cosine"}}`. Để đảm bảo tính Idempotent (tái lập), hàm `build` tự động xóa và tái tạo collection nếu đã tồn tại, sau đó ghi file manifest JSON lưu lại lineage của collection.
3. **Multi-Provider QA Agent:** Đóng gói LangChain Agent tích hợp 2 tools: `semantic_search_papers` (tìm kiếm vector theo top-k) và `lookup_paper` (tra cứu chính xác theo Paper ID hoặc Title). Cung cấp cơ chế `mock` fallback với `FakeListChatModel` để pipeline luôn chạy trơn tru ngay cả khi rớt mạng hoặc hết quota API.

### Input, output và contract

| Thành phần | Mô tả |
| ---------- | ----- |
| Input | `pandas.DataFrame` gồm các cột `paper_id`, `title`, `text_for_embedding`, `summary`, `authors_joined`, `categories_joined`, `published` |
| Output | Đối tượng `LocalEmbeddingIndex`, thư mục persist `data/chroma/`, file `papers_embeddings.json` |
| Module phụ thuộc | `src/ingestion/cleaning.py` (cung cấp DataFrame sạch), `src/core/config.py` (cung cấp đường dẫn và tham số) |
| Module sử dụng output | `src/evaluation/metrics.py` (truy vấn top-k để tính Hit Rate), `src/pipelines/` (chạy baseline và corruption flow) |
| Điều kiện lỗi cần xử lý | Xử lý collection đã tồn tại trong ChromaDB; fallback sang heuristic search khi model LLM chưa cấu hình API Key |

### Cách xác minh
```bash
pytest tests/test_retrieval.py -v
```
- **Kết quả mong đợi:** 3 test cases đều PASSED (`test_minilm_embeddings`, `test_chroma_build_and_search`, `test_mock_llm_and_qa_agent`).
- **Kết quả thực tế:** Vector embedding có chiều dài 384, L2-norm $\approx 1.0$, ChromaDB query trả về đúng tài liệu có score tương đồng cao nhất.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn giữa việc dùng dịch vụ Cloud Embedding API (OpenAI `text-embedding-3-small`) hay mô hình Local Embedding (`sentence-transformers/all-MiniLM-L6-v2`).
- **Các phương án đã cân nhắc:**
  1. *OpenAI text-embedding-3-small (1536 chiều):* Hiệu năng cao nhưng phụ thuộc mạng phòng lab, tốn chi phí token và dễ bị chặn rate limit trong các vòng lặp re-indexing liên tục của Phase 2.
  2. *HuggingFace all-MiniLM-L6-v2 (384 chiều) local:* Chạy trực tiếp trên CPU/RAM của máy trạm, hoàn toàn miễn phí, tốc độ tạo embedding cực nhanh (~1-2 giây cho 24 tài liệu) và hoàn toàn offline.
- **Phương án đã chọn:** Sử dụng `sentence-transformers/all-MiniLM-L6-v2` kết hợp với ChromaDB local persistence.
- **Lý do:** Đảm bảo tính **Reproducibility 100%** (tính tái lập) cho bài lab. Khi giám khảo hoặc trợ giảng clone repo về máy chấm thi, hệ thống có thể chạy offline ngay lập tức mà không cần cấu hình credit API cho phần embedding.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  ImportError: cannot import name 'UTC' from 'datetime' (C:\Users\Admin\AppData\Local\Programs\Python\Python310\lib\datetime.py)
  ModuleNotFoundError: No module named 'core'
  ```
- **Lệnh hoặc bước tái hiện:** Chạy `pytest tests/test_retrieval.py` trên môi trường Python 3.10.
- **Nguyên nhân gốc:**
  1. Hằng số `datetime.UTC` chỉ mới được hỗ trợ từ Python 3.11 trở lên, trong khi máy trạm đang chạy Python 3.10.
  2. Thư mục `src/` chưa được nhận diện tự động vào `sys.path` của pytest.
- **Cách xử lý:**
  1. Thay thế `from datetime import UTC` bằng `from datetime import timezone` và dùng `timezone.utc` trong `src/core/config.py` và `src/core/utils.py`.
  2. Tạo file `tests/conftest.py` để bổ sung đường dẫn `src/` vào `sys.path` và thêm cấu hình `pythonpath = ["src"]` vào `pyproject.toml`.
- **Cách xác minh sau khi sửa:** Chạy lại `pytest tests/test_retrieval.py -v`, module `core` và `datetime` được import trơn tru không còn báo lỗi.
- **Điều học được:** Luôn chú ý tính tương thích ngược (backward compatibility) giữa các phiên bản Python nhỏ (3.10 vs 3.11) và cấu hình `conftest.py` chuẩn cho test suite.

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu thô từ Crossref API được tải và bảo toàn nguyên trạng (Raw Preservation) để tạo điểm tựa phục hồi (Data Lineage).
2. Tầng Cleaning làm sạch văn bản, tính toán `age_days` và chuẩn bị `text_for_embedding` trước khi đưa qua Quality Gate của Great Expectations 1.x.
3. Tầng Retrieval (phần việc của tôi) chuyển hóa văn bản thành không gian vector bằng MiniLM và lưu vào ChromaDB. Agent sử dụng không gian này để truy xuất tài liệu và trả lời câu hỏi.
4. Khi dữ liệu bị tiêm độc tố (Data Corruption) ở Phase 2, các bài báo bị cắt ngắn, mất tóm tắt hoặc chèn chuỗi ký tự rác, dẫn đến việc khoảng cách Cosine bị bóp méo $\rightarrow$ Agent tìm kiếm sai $\rightarrow$ Điểm Hit Rate và Token F1 sụt giảm nghiêm trọng (chứng minh **Silent Failure**).
5. Cuối cùng, cơ chế Idempotent Repair nạp lại dữ liệu từ Raw ban đầu, tái xây dựng lại toàn bộ không gian vector ChromaDB, giúp Agent khôi phục lại phong độ 100% như lúc ban đầu.
