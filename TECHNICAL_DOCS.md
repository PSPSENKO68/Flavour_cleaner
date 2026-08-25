# TÀI LIỆU KỸ THUẬT CHI TIẾT — DỰ ÁN FLAVOUR CLEANER (BẢN CẬP NHẬT TÍCH HỢP AI)
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
* **Đầu ra (Output):** Tên thương mại tiếng Anh chính xác của sản phẩm, được cập nhật trực tiếp vào file Excel gốc mà vẫn giữ nguyên hoàn toàn cấu trúc, định dạng của file.

### 1.2. Mô hình kiến trúc hệ thống (Kiến trúc Mới: Single Cascading Pipeline)
Hệ thống xử lý file Excel thông qua một giao diện người dùng (GUI) độc lập và sử dụng luồng Pipeline tự động:
1. **AI NER Extraction (Chủ đạo):** Sử dụng mô hình Machine Learning (Transformers ONNX) được huấn luyện riêng để nhận diện thực thể (Named Entity Recognition - NER). Mô hình này sẽ quét qua toàn bộ văn bản và "bắt" lấy cụm từ mang ý nghĩa sản phẩm.
2. **Regex Post-Processing (Dọn rác):** Dữ liệu thô AI bóc tách ra thường bị dính các dấu câu thừa ở hai đầu. Dữ liệu này sẽ chảy qua một bộ lọc Regex để gọt sạch dấu ngoặc, dấu phẩy, v.v.
3. **Rules Fallback (Chữa cháy):** Nếu AI hoàn toàn thất bại không tìm ra kết quả, hệ thống tự động rơi xuống (fallback) bộ luật Regex cơ sở (Heuristic truyền thống) để "cứu vớt" dữ liệu.

### 1.3. Cấu trúc thư mục hiện tại
* **Giao diện & Pipeline chính:** `ml_trainer/test_model/gui_2.py`
* **Mô hình Trí tuệ Nhân tạo:** Thư mục `ml_trainer/flavour_ner_onnx` (Chứa mô hình định dạng ONNX)
* **Lõi xử lý dự phòng (Legacy):** `run_clean.py`, `clean_flavour.py`, `detect.py`, `patterns.txt`

---

## 2. CƠ CHẾ XỬ LÝ NGÔN NGỮ & THUẬT TOÁN ĐẶC BIỆT

### 2.1. Ứng dụng Mô Hình Token Classification (NER)
Hệ thống không còn quá phụ thuộc vào các từ khóa tĩnh, mà sử dụng AI để hiểu **ngữ cảnh**. 
- Mô hình sử dụng cấu trúc `XLMRobertaForTokenClassification`, được tối ưu hóa ở định dạng `ONNX` để chạy cục bộ (offline) nhanh chóng mà không cần GPU.
- **Labels (Nhãn):** Mô hình được dạy để đánh dấu các token thuộc nhóm `PROD` (Sản phẩm). Pipeline của thư viện `transformers` sẽ tự động gom các token `B-PROD` và `I-PROD` lại thành một cụm từ hoàn chỉnh (thông qua `aggregation_strategy="simple"`).

### 2.2. Kỹ Thuật Regex Post-Processing
Bản thân AI làm rất tốt việc định vị nhưng làm rất tệ việc cắt gọt chính xác từng ký tự rìa.
Một thuật toán Regex được áp dụng ngay sau AI:
```python
text = re.sub(r'^[\(\)\:\;\-\,]+', '', text)
text = re.sub(r'[\(\)\:\;\-\,]+$', '', text)
```
- **Tác dụng:** Cắt bỏ các dấu ngoặc `)`, dấu `:` lẻ loi mà AI lỡ gắp thừa. Đẩy độ chính xác của AI lên mức 98-99%.

### 2.3. Cơ chế Fallback với Thuật Toán Heuristic (Cũ)
Chỉ kích hoạt khi AI không trả về kết quả. 
- Sử dụng **chấm điểm thống kê đa tiêu chí** và **phân tách ngôn ngữ**. 
- Dùng từ tiếng Việt làm "vách ngăn" để tách cụm tiếng Anh. Cộng điểm nếu chứa các từ khóa ngành hàng (FLAVOUR, OIL) định nghĩa trong `patterns.txt`.

---

## 3. LUỒNG CHẠY & PHÂN TÍCH CHI TIẾT TỪNG FILE (FILE-BY-FILE DEEP DIVE)

### Luồng thực thi tự động (Execution Flow)
1. **Khởi chạy UI:** Người dùng mở `python gui_2.py`.
2. **Chọn Dữ liệu:** Người dùng load file `.xlsx`, chọn Sheet và Column. Bấm "Load Data Preview" để tải lên bảng Treeview. Các dòng sẽ hiển thị nền màu Vàng (Pending).
3. **Kích hoạt Pipeline:** Người dùng bấm `Run Full Auto Clean (AI + Regex)`.
4. **Xử lý ngầm (Background Thread):** 
   - Load mô hình ONNX lên bộ nhớ.
   - Chạy từng dòng qua AI. Nếu thành công -> Regex Cleanup -> Chuyển màu Xanh (`Cleaned (AI + Regex)`).
   - Nếu AI thất bại -> Đưa qua `run_clean.apply_custom_rules` và `clean_description` -> Chuyển màu Xanh (`Cleaned (Rules Fallback)`).
5. **Nghiệm thu & Lưu:** Người dùng bấm `Save As...`. Hệ thống mở ngầm file Excel gốc, ghi đè kết quả vừa xử lý vào đúng tọa độ của cột đã chọn, sau đó xuất ra file mới, bảo toàn 100% định dạng cũ.

### 3.1. `gui_2.py` (Trái tim của hệ thống mới)
- **Nhiệm vụ:** Quản lý giao diện, luồng sự kiện, và là trung tâm kết nối AI với bộ rules cũ.
- **Bên trong:** 
  - Khởi tạo giao diện bằng `tkinter`.
  - Hàm `_run_pipeline_thread()` triển khai toàn bộ logic AI đi trước, Regex theo sau.
  - Hàm `save_as()` sử dụng `openpyxl` để bảo toàn định dạng file.

### 3.2. Thư mục `flavour_ner_onnx` (Não bộ AI)
- **Nhiệm vụ:** Nhận diện thực thể (NER).
- **Bên trong:** Chứa `model.onnx` (trọng số mô hình), `config.json` (cấu hình nhãn `PROD`), và `tokenizer.json` (từ điển băm ký tự). Được gọi qua thư viện `optimum.onnxruntime`.

### 3.3. Các file Legacy (`run_clean.py`, `clean_flavour.py`, `patterns.txt`)
- **Nhiệm vụ:** Đóng vai trò làm mạng lưới an toàn (Safety Net / Fallback).
- **Bên trong:** `clean_flavour.py` vẫn nắm giữ logic nhận dạng tiếng Việt (`has_vietnamese`) và xử lý điểm số cơ bản. `patterns.txt` lưu các luật cố định cho nhà sản xuất (HASEGAWA, SDN BHD...).

---

## 4. BẢNG TỔNG KẾT RỦI RO KHI THAY ĐỔI

| Thành phần thay đổi | Nguy cơ / Rủi ro | Giải pháp khuyến nghị |
| :--- | :--- | :--- |
| **Thay đổi / Cập nhật mô hình trong `flavour_ner_onnx`** | Nếu mô hình mới thay đổi tập nhãn (Ví dụ đổi từ `PROD` sang `FLAVOUR`), code trong `gui_2.py` sẽ không lọc được entity nữa. | Đảm bảo mô hình mới phải giữ nguyên cấu trúc nhãn `PROD` khi huấn luyện. Nếu đổi, phải cập nhật lại dòng `ent['entity_group'] == 'PROD'` trong code. |
| **Sửa đổi logic Regex trong `regex_post_processing`** | Bắt sai Regex có thể vô tình xóa mất ký tự chữ hoặc số ở đầu/đuôi tên sản phẩm. | Chỉ giới hạn trong việc xóa các ký tự đặc biệt (dấu câu). Bắt buộc test lại với các mã sản phẩm chứa dấu gạch ngang (như `PFE-1234`). |
| **Cập nhật thư viện `optimum`/`onnxruntime`** | Phiên bản không tương thích có thể gây ra lỗi `ImportError` hoặc treo máy khi load model. | Khóa chặt (freeze) phiên bản thư viện hiện hành trong file `requirements.txt`. |
| **Sửa đổi `patterns.txt` (Vùng Legacy)** | Dù AI là chủ đạo, nếu AI thất bại, hệ thống vẫn dùng bộ rule này. Thêm sai từ khóa vào `[vietnamese-words]` vẫn có rủi ro cắt cụt từ. | Không đưa danh từ chỉ thực phẩm, trái cây tiếng Anh (như TOM, CAM) vào danh sách loại bỏ của tiếng Việt. |
