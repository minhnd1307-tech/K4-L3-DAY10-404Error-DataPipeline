# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Duy Khánh                     |
| MSSV               | 2A202602736      |
| Tên nhóm         |    404Error     |
| Vai trò chính    | Data Foundation Owner & Recovery |
| Repository         | K4-L3-DAY10-TenNhom-DataPipeline |
| Ngày hoàn thành | 2026-09-25               |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | :---: |
| Data Ingestion & Preservation | `src/ingestion/crossref.py` | API URL, query params, raw snapshot file | Danh sách `PaperRecord` đã parse và raw artifacts JSON | Hoàn thành |
| Data Cleaning & Normalization | `src/ingestion/cleaning.py` | Danh sách `PaperRecord` gốc | DataFrame `papers_clean.csv` đã khử nhiễu, nối chuỗi `text_for_embedding` | Hoàn thành |
| Idempotent Repair Logic | Hàm `build_clean_dataframe` | `data/raw/crossref_records.json` | Dữ liệu sạch tái tạo hoàn hảo (Repaired Dataset) | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --------- | ----------------------------- | ------- |
| Great Expectations Gate | Hỗ trợ Ngọc (`quality.py`) | Viết logic khởi tạo Ephemeral Context và 4 Expectations chuẩn bị cho kiểm dịch |
| Fix Contract Schema | Hỗ trợ Minh (`index.py`) | Bổ sung cột `abs_url`, `primary_category` vào Dataframe để vector database chạy ổn định |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ---------------- | ------------- |
| Lấy dữ liệu Crossref | `parse_crossref_payload`, `fetch_source_records` | Parse thành công cấu trúc JATS XML, hỗ trợ offline mode | Chạy lệnh fetch báo `Đã tải 24 bài báo` |
| Làm sạch và Ghép context | `build_clean_dataframe` | Lọc nhiễu, drop duplicates, tính toán `age_days` và `text_for_embedding` | Chạy lệnh clean báo `Clean thành công 24 dòng` |
| Phục hồi dữ liệu | `load_raw_records` | Khôi phục 100% bản ghi chuẩn từ snapshot gốc, sẵn sàng cho luồng Repair | Dữ liệu repaired trùng khớp hoàn toàn với baseline |

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Xây dựng nền móng dữ liệu (Data Foundation) vững chắc, đảm bảo dữ liệu đầu vào không bị rác (Garbage In) trước khi đưa vào kho Vector. Đồng thời, thiết kế cơ chế khôi phục (Self-healing) đảm bảo tính Idempotent khi dữ liệu bị hỏng hóc ở môi trường Production.

### Cách triển khai
1. **Thu thập (`crossref.py`):** Viết logic loại bỏ các thẻ HTML rác như `<jats:p>` trong tóm tắt bằng biểu thức Regex. Bắt lỗi kết nối mạng để tự động kích hoạt Dual-Mode fallback sang local snapshot khi API báo 429.
2. **Làm sạch (`cleaning.py`):** Ghép nối các trường thành khối ngữ cảnh `text_for_embedding` chuẩn hóa. Sử dụng cơ chế `drop_duplicates(subset=["paper_id"])` và parse thời gian với múi giờ đồng nhất.
3. **Phục hồi (Repair):** Thiết kế hàm làm sạch như một *Pure Function*, không phụ thuộc trạng thái ngoài. Do đó, khi bị luồng Corruption làm hỏng, chỉ cần đọc lại từ kho lưu trữ thô (Raw Preservation) và ném vào hàm này, dữ liệu sạch lập tức được tái sinh 100%.

### Input, output và contract

| Thành phần | Mô tả |
| ---------- | ----- |
| Input | JSON response từ Crossref API, Raw snapshot `data/raw/crossref_response.json` |
| Output | Danh sách đối tượng `PaperRecord`, DataFrame sạch (chứa `text_for_embedding`, `age_days`, `abs_url`) |
| Module phụ thuộc | `core.config` (để lấy đường dẫn và thông số) |
| Module sử dụng output | `retrieval` (dùng để index vector), `observability` (để kiểm định GX) |

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Xử lý các bài báo bị rác thẻ XML `<jats:p>` trong phần Tóm tắt (Summary).
- **Các phương án đã cân nhắc:**
  1. *Phương án A:* Giữ nguyên toàn bộ text (kể cả thẻ XML) để embedding model tự học biểu diễn.
  2. *Phương án B:* Sử dụng Regex `re.sub(r'<[^>]+>', '', abstract)` để gọt sạch toàn bộ các thẻ HTML/XML.
- **Phương án đã chọn:** Phương án B (Dùng Regex khử nhiễu).
- **Lý do:** Các mô hình embedding nhẹ như `all-MiniLM-L6-v2` rất nhạy cảm với các token nhiễu không mang ý nghĩa ngữ nghĩa (như các thẻ đóng/mở HTML). Việc dọn dẹp sạch bằng Regex sẽ giúp bảo toàn Token Limit và cải thiện đáng kể độ đo Hit Rate sau này.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `KeyError: 'abs_url'` khi chạy lệnh `python script/run_phase1.py`.
- **Nguyên nhân gốc:** Hàm `build_clean_dataframe` của tôi tạo DataFrame nhưng quên đẩy cột `abs_url` từ bản ghi gốc sang DataFrame sạch. Trong khi đó, module `index.py` của Thành viên 3 lại cần cột này làm Metadata cho ChromaDB.
- **Cách xử lý:** Bổ sung `abs_url` (cùng các trường khác như `pdf_url`, `primary_category`) vào Dict trước khi append vào danh sách dữ liệu.
- **Cách xác minh sau khi sửa:** Chạy lại `python script/run_phase1.py` và luồng pipeline vượt qua được khâu nạp Index mà không bị văng lỗi.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Dữ liệu được tải dạng cục JSON từ Crossref, qua hàm `parse_crossref_payload()` để thành list các `PaperRecord`. Hàm `build_clean_dataframe()` xử lý list này thành pandas DataFrame, làm phẳng thành `text_for_embedding`. Khối text này được model nhúng thành vector số học và lưu vào ChromaDB.
2. **Tại sao lại cần phải lưu trữ Raw Preservation?**
   Đóng vai trò như hòm cấp cứu. Nếu các quá trình transformation (làm sạch/thay đổi) vô tình làm hỏng data, hoặc mạng chết, chúng ta không cần gọi API tải lại từ đầu mà chỉ việc chọc thẳng vào file Raw để tái tạo quá trình làm sạch.
3. **Idempotent Repair nghĩa là gì trong bài lab này?**
   Idempotent là tính chất "thực thi N lần kết quả không đổi". Ở bài lab này, nó có nghĩa là dù file dữ liệu hiện hành có bị tiêm lỗi rác 1 lần hay 100 lần, thì tiến trình Repair luôn đọc lại từ bản ghi Raw gốc, đưa qua logic clean bất biến để cho ra đúng 24 bản ghi sạch chuẩn như lúc ban đầu. 

---

## 8. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.

**Họ và tên:** Khánh  
**Ngày xác nhận:** 2026-09-25  
