# TÀI LIỆU KỸ THUẬT CHI TIẾT — DỰ ÁN FLAVOUR CLEANER
*(System Technical Documentation & Code Deep Dive)*

---

## MỤC LỤC
1. [TỔNG QUAN KIẾN TRÚC & CƠ SỞ LÝ THUYẾT](#1-tổng-quan-kiến-trúc--cơ-sở-lý-thuyết)
2. [CƠ CHẾ XỬ LÝ NGÔN NGỮ & THUẬT TOÁN ĐẶC BIỆT](#2-cơ-chế-xử-lý-ngôn-ngữ--thuật-toán-đặc-biệt)
3. [LUỒNG CHẠY & PHÂN TÍCH CHI TIẾT TỪNG FILE (FILE-BY-FILE DEEP DIVE)](#3-luồng-chạy--phân-tích-chi-tiết-từng-file)
4. [BẢNG TỔNG KẾT RỦI RO KHI THAY ĐỔI](#4-bảng-tổng-kết-rủi-ro-khi-thay-đổi)

---

## 1. TỔNG QUAN KIẾN TRÚC & CƠ SỞ LÝ THUYẾT

### 1.1. Mục tiêu và bài toán
**Bài toán:** Trích xuất tên tiếng Anh chuẩn của sản phẩm/hương liệu (Flavour/Product Name) từ cột mô tả hàng hóa tự do trong tờ khai hải quan Việt Nam.
* **Đầu vào (Input):** File Excel tờ khai hải quan chứa cột mô tả hàng hóa tự do, có văn bản tiếng Việt lẫn tiếng Anh, kèm theo quy cách đóng gói, nhà sản xuất, v.v.
* **Đầu ra (Output):** Giao diện lưới (Grid) hiển thị kết quả trích xuất, cho phép người dùng kiểm tra trực quan, sau đó xuất ra file Excel mới mà vẫn giữ nguyên hoàn toàn cấu trúc, định dạng của file gốc.

### 1.2. Mô hình kiến trúc hệ thống
Hệ thống xử lý file Excel cục bộ, bao gồm các bước theo đường ống (Cascading Pipeline):
1. **AI NER (Chủ đạo):** Sử dụng mô hình Machine Learning (định dạng ONNX) trích xuất thực thể (NER). AI đọc văn bản và trích xuất cụm từ mang nhãn `PROD`.
2. **Regex Post-Processing (Tiền xử lý & Chuẩn hóa):** Dùng biểu thức chính quy gọt bỏ các ký tự thừa và lọc bỏ phần tiếng Việt bị dính vào kết quả của AI.
3. **Rules Fallback (Dự phòng):** Nếu AI trả về kết quả rỗng, hệ thống dùng thuật toán Heuristic tĩnh (`clean_flavour.py`) để chữa cháy.

### 1.3. Cấu trúc thư mục hiện tại
Toàn bộ dự án được thiết kế chạy Offline hoàn toàn.
* **Giao diện & Lõi AI:** `gui_2.py`
* **Mô hình Trí tuệ Nhân tạo:** Thư mục `ml_trainer/model_version4/flavour_ner_onnx`
* **Xử lý ngoại lệ & Dự phòng:** `run_clean.py`, `clean_flavour.py`, `patterns.txt`

## 2. CƠ CHẾ XỬ LÝ NGÔN NGỮ & THUẬT TOÁN ĐẶC BIỆT

### 2.1. Nhận dạng Thực thể bằng Trí tuệ Nhân tạo (AI - NER)
Hệ thống sử dụng mô hình học sâu cấu trúc `XLMRobertaForTokenClassification` đã được huấn luyện riêng biệt.
- **Cơ chế:** Mô hình phân rã văn bản, tính toán xác suất cho từng đoạn nhỏ (token), và gán nhãn `B-PROD` (Bắt đầu sản phẩm) hoặc `I-PROD` (Bên trong sản phẩm). Thư viện AI sẽ tự động gom các token này thành cụm từ hoàn chỉnh.
- **Sức mạnh ngữ cảnh:** Nhờ cơ chế học sâu, AI có khả năng tự động phớt lờ các cụm từ tiếng Việt không liên quan.
  - *Ví dụ:* `Hương Bò BEEF EXTRACT POWDER PFE-123` -> Trích xuất: `BEEF EXTRACT POWDER PFE-123` (Không cần dùng luật cắt tiếng Việt).

### 2.2. Thuật toán gọt tiếng Việt bằng Biểu thức chính quy (Anchor Regex)
Vì mô hình AI thỉnh thoảng bắt nhầm một từ tiếng Việt liền kề vào cụm tiếng Anh, thuật toán Regex (trong `gui_2.py`) hoạt động như một lớp màng lọc:
1. **Tìm mỏ neo (Anchor):** Xác định vị trí chữ `FLAVOUR` hoặc `FLAVOR` trong chuỗi kết quả.
2. **Quét ngược:** Từ vị trí mỏ neo, quét ngược về đầu câu từng từ một.
3. **Chặn và Cắt:** Dừng lại ngay lập tức khi phát hiện từ chứa dấu tiếng Việt (vd: chữ `Hương`), hoặc từ nằm trong danh sách cấm `[viet-no-diacrit]` (vd: chữ `CAM`, chữ `HEO`). Toàn bộ phần chuỗi từ điểm dừng hất về trước sẽ bị cắt bỏ.
- **Ví dụ logic:** 
  - *Đầu vào:* `Hương CAM ORANGE FLAVOUR L-9999`
  - *Luồng chạy:* Neo tại `FLAVOUR` -> Quét ngược -> Gặp chữ `CAM` (nằm trong `[viet-no-diacrit]`) -> Cắt bỏ `Hương CAM`. 
  - *Đầu ra:* `ORANGE FLAVOUR L-9999`.

### 2.3. Thuật toán nối chuỗi và dọn rác
- **Nối chuỗi:** Nếu AI chẻ cụm từ làm đôi do đọc nhầm dấu câu (vd: `CHOCOLATE` và `FLAVOUR`), thuật toán tự động thay thế ký tự ngăn cách bằng khoảng trắng để nối lại nguyên trạng (`CHOCOLATE FLAVOUR`).
- **Dọn rác đuôi:** Dùng Regex để tự động gọt bỏ dấu ngoặc đóng bất đối xứng `)` ở cuối câu, và cắt bỏ mọi thông tin rác nằm sau các cụm từ như `QUY CÁCH`, `DÙNG CHO`.

## 3. LUỒNG CHẠY & PHÂN TÍCH CHI TIẾT TỪNG FILE

### Luồng thực thi (Execution Flow)
1. **Khởi chạy:** Mở terminal chạy `python gui_2.py` (Hoặc click đúp file `.bat` / `.exe`). Giao diện Desktop xuất hiện.
2. **Nạp mô hình:** Giao diện tự động nạp mô hình AI từ thư mục `flavour_ner_onnx` vào RAM.
3. **Phân tích Excel:** Người dùng chọn file Excel, chọn Sheet và Cột chứa dữ liệu hải quan. Nhấn "Bắt đầu".
4. **Bóc tách:** Vòng lặp duyệt qua từng ô trong cột. Đầu tiên, truyền chuỗi vào mô hình AI (Lớp 1). Sau đó, truyền kết quả thô của AI qua bộ lọc Regex (Lớp 2).
5. **Dự phòng (Fallback):** Nếu cả Lớp 1 và 2 đều thất bại, hệ thống gọi hàm `clean_description` từ `clean_flavour.py` (Lớp 3) để tính điểm Heuristic (dựa trên thuật toán cũ) và trả về kết quả vớt vát.
6. **Ghi nhận & Hiển thị:** Cập nhật kết quả lên lưới (Grid). Dòng xử lý bằng AI hiện chữ Xanh, dòng lỗi hiện chữ Vàng.
7. **Lưu file:** Người dùng nhấn `Save As`, hệ thống sao chép file gốc và chèn kết quả chuẩn xác vào cột tương ứng.

### 3.1. `gui_2.py` (Giao diện & Động cơ AI cốt lõi)
- **Nhiệm vụ:** Quản lý giao diện, luồng sự kiện I/O, và là trung tâm thực thi Pipeline AI.
- **Bên trong:**
  - Khai báo giao diện bằng thư viện `tkinter`.
  - Hàm `_run_pipeline_thread()` xử lý đa luồng (Threading) để không làm đơ giao diện khi AI đang chạy.
  - Tích hợp nội tuyến hàm `regex_post_processing` để thực thi thuật toán quét ngược (Anchor Regex) dọn rác tiếng Việt và chuẩn hóa chuỗi.

### 3.2. Thư mục `flavour_ner_onnx` (Trọng số AI)
- **Nhiệm vụ:** Chứa các tệp cấu hình và bản đồ ma trận học sâu (Deep Learning).
- **Bên trong:** Chứa `model.onnx` (trọng số mô hình tĩnh), `config.json` (quy định tập nhãn `PROD`), và `tokenizer.json` (từ điển băm token). Việc dùng định dạng ONNX giúp hệ thống chạy nhanh gấp 3 lần bình thường mà không cần Card đồ họa (GPU).

### 3.3. `clean_flavour.py` và `patterns.txt` (Hệ thống dự phòng)
- **Nhiệm vụ:** Đóng vai trò mạng lưới an toàn (Safety Net) khi AI gặp các ngành hàng chưa từng học.
- **Bên trong:** `clean_flavour.py` là bộ thư viện dùng để chấm điểm chuỗi văn bản bằng các luật IF-ELSE truyền thống. `patterns.txt` lưu trữ danh sách các từ vựng tiếng Việt không dấu (`[viet-no-diacrit]`) để bộ lọc Anchor Regex trong `gui_2.py` lấy làm từ điển cắt chuỗi.

## 4. BẢNG TỔNG KẾT RỦI RO KHI THAY ĐỔI

| Thành phần thay đổi | Nguy cơ / Rủi ro | Giải pháp khuyến nghị |
| :--- | :--- | :--- |
| **Logic Anchor Regex trong `gui_2.py`** | Sửa sai biểu thức Regex có thể khiến phần tiếng Việt không được cắt bỏ, hoặc cắt thấu vào tận tên tiếng Anh (ví dụ cắt mất mã lô hàng). | Tuyệt đối không sửa Regex nếu không nắm vững cú pháp Lookbehind/Lookahead. Phải kiểm tra thử (test) lại với các chuỗi phức tạp ngay sau khi sửa. |
| **Cập nhật `patterns.txt` (`[viet-no-diacrit]`)** | Thêm một từ vựng sai vào danh sách (vd như: TOM, NHO) sẽ làm biến mất từ đó trong tên tiếng Anh (vd: Tom Yum -> Yum). | Không đưa các danh từ chỉ thực phẩm quốc tế, tên riêng hoặc tên đa nghĩa vào danh sách cấm của tiếng Việt. |
| **Đổi nhãn mô hình `flavour_ner_onnx`** | Nếu mô hình mới đổi nhãn từ `PROD` sang tên khác (ví dụ: `FLAV`), mã nguồn sẽ không trích xuất được thực thể. | Đảm bảo mô hình mới giữ nguyên nhãn `PROD`. Nếu bắt buộc đổi, phải cập nhật biến `ent['entity_group'] == 'PROD'` trong `gui_2.py`. |
| **Đóng gói file `.exe` bằng PyInstaller** | Tiến trình sinh ra vô hạn luồng (Infinite Child Processes) làm treo đứng hệ điều hành Windows do cơ chế `multiprocessing` của thư viện tokenizers. | Lập trình viên bắt buộc phải chèn dòng lệnh `multiprocessing.freeze_support()` ngay dưới khối `if __name__ == '__main__':` trong mã nguồn trước khi biên dịch. |
