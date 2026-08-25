# TÀI LIỆU KỸ THUẬT: HỆ THỐNG TRÍCH XUẤT TÊN HƯƠNG LIỆU TỰ ĐỘNG
*(Technical Documentation: Flavour Name Extraction System)*

---

## 1. TỔNG QUAN HỆ THỐNG
**Mục tiêu:** Trích xuất tên thương mại tiếng Anh của sản phẩm từ cột mô tả hàng hóa tự do trong tờ khai hải quan.
**Đầu vào:** File Excel (Cột mô tả hải quan chứa văn bản hỗn hợp Anh-Việt, quy cách đóng gói).
**Đầu ra:** Tên tiếng Anh chuẩn xác của sản phẩm, xuất ra file Excel mới giữ nguyên cấu trúc gốc.

## 2. KIẾN TRÚC VÀ LUỒNG XỬ LÝ (PIPELINE)
Hệ thống hoạt động theo mô hình tuần tự 3 lớp (3-Layer Cascading Pipeline):

### Lớp 1: Nhận dạng Thực thể bằng Trí tuệ Nhân tạo (AI - NER)
- **Công nghệ:** Mô hình ngôn ngữ (Transformers) được huấn luyện chuyên biệt và tối ưu hóa ở định dạng ONNX.
- **Cơ chế:** Quét văn bản đầu vào và đánh dấu các chuỗi ký tự (token) thuộc nhãn `PROD` (Sản phẩm).
- **Ví dụ:**
  - *Input:* `Chất tạo hương CHERRY FLAVOUR PFE-99, 25kg`
  - *Output Lớp 1:* `CHERRY FLAVOUR PFE-99`

### Lớp 2: Chuẩn hóa bằng Biểu thức chính quy (Regex Post-Processing)
- **Công nghệ:** Regular Expressions (Regex).
- **Cơ chế:**
  - Nối các từ bị Lớp 1 phân tách nhầm bằng khoảng trắng (thay vì dấu phẩy).
  - Xóa bỏ dấu ngoặc đơn bất đối xứng và các thông tin quy cách đóng gói (vd: `QUY CÁCH`, `HIỆU`).
  - **Quy tắc neo (Anchor Rule):** Lấy từ khóa `FLAVOUR`/`FLAVOR` làm mỏ neo, quét ngược về đầu chuỗi. Dừng lại và cắt bỏ phần phía trước ngay khi gặp một từ tiếng Việt có dấu, hoặc một từ thuộc danh sách cấm `[viet-no-diacrit]` (quy định trong tệp `patterns.txt`).

### Lớp 3: Cơ chế Dự phòng (Rules Fallback)
- **Cơ chế:** Nếu Lớp 1 không trả về kết quả hợp lệ, hệ thống sẽ tự động chuyển sang sử dụng thuật toán dựa trên từ điển cơ sở (`clean_flavour.py` và `patterns.txt`) để giảm thiểu tỷ lệ rỗng dữ liệu.

---

## 3. PHÂN TÍCH CA KIỂM THỬ (CASE STUDIES)

Nhằm đánh giá giới hạn của thuật toán, tập dữ liệu `unseen_test_data.xlsx` chứa các trường hợp phức tạp (edge cases). Dưới đây là phân tích logic:

### 3.1. Các trường hợp hệ thống xử lý thành công

**Ca 1: Lặp mã sản phẩm**
- **Input gốc:** `PFE-12345 - APPLE FLAVOUR PFE-12345, HÀNG MỚI`
- **Output:** `APPLE FLAVOUR PFE-12345`
- **Giải thích logic:** Lớp 1 trích xuất toàn bộ cụm từ. Lớp 2 đối chiếu mẫu chuỗi ở đầu và cuối, tự động loại bỏ đoạn mã lặp dư thừa ở đầu chuỗi.

**Ca 2: Tiếng Việt không dấu viết liền**
- **Input gốc:** `Hương CAM ORANGE FLAVOUR L-9999`
- **Output:** `ORANGE FLAVOUR L-9999`
- **Giải thích logic:** Ký tự `CAM` là chuỗi ASCII không dấu. Tuy nhiên, do `CAM` đã được khai báo trong danh sách `[viet-no-diacrit]` tại `patterns.txt`, thuật toán quét ngược từ mỏ neo `FLAVOUR` sẽ nhận diện `CAM` là tiếng Việt và cắt bỏ toàn bộ phần đứng trước nó.

**Ca 3: Ký tự phân cách bất đối xứng**
- **Input gốc:** `HƯƠNG SỮA MILK FLAVOUR PFE-111(V)), QUY CÁCH 25KG`
- **Output:** `MILK FLAVOUR PFE-111(V)`
- **Giải thích logic:** Lớp 2 tự động phát hiện và loại bỏ dấu `)` bị dư ở cuối cụm từ, đồng thời cắt bỏ thông tin phía sau chuỗi `QUY CÁCH`.

**Ca 4: Xử lý chuỗi không chứa mỏ neo (Anchor)**
- **Input gốc:** `Hương Bò BEEF EXTRACT POWDER PFE-123, Mới 100%`
- **Output:** `BEEF EXTRACT POWDER PFE-123`
- **Giải thích logic:** Mặc dù chuỗi không chứa từ khóa `FLAVOUR`/`FLAVOR` để kích hoạt luật gọt tiếng Việt của Regex (Lớp 2), nhưng Lớp 1 (AI NER) thông qua học sâu đã tự động hiểu ngữ cảnh và chỉ đánh dấu (tag) đoạn tiếng Anh `BEEF EXTRACT POWDER PFE-123` là nhãn `PROD`. Từ `Hương Bò` bị loại bỏ ngay từ bước đầu tiên mà không cần đến Regex.

### 3.2. Các trường hợp hệ thống xử lý lỗi và Nguyên nhân

**Ca 5: Cấu hình tệp từ điển sai quy định**
- **Input gốc:** `Hương Tôm TOM YUM FLAVOUR PFE-555`
- **Output mong đợi:** `TOM YUM FLAVOUR PFE-555`
- **Rủi ro:** Nếu người dùng khai báo thêm từ `TOM` vào danh sách `[viet-no-diacrit]`, hệ thống sẽ nhận diện sai từ tiếng Anh `TOM` (trong cụm Tom Yum) thành tiếng Việt. Kết quả chuỗi sẽ bị cắt gãy thành `YUM FLAVOUR PFE-555`.
- **Nguyên tắc hệ thống:** Nghiêm cấm khai báo các từ đa nghĩa (trùng lặp giữa tiếng Anh và tiếng Việt không dấu) vào tệp cấu hình.

**Ca 6: Dữ liệu ngoài miền huấn luyện (Out-of-Domain)**
- **Input gốc:** `MÁY XAY SINH TỐ CÔNG NGHIỆP BLENDER MODEL-999`
- **Output thực tế (Lỗi):** Trả về giá trị rỗng hoặc kết quả không dự đoán được.
- **Giải thích logic:** Lớp 1 (Mô hình NER) chỉ được huấn luyện trên từ vựng thuộc nhóm ngành Hương liệu thực phẩm. Thuật toán không có bộ trọng số để nhận diện các sản phẩm thuộc ngành cơ khí, điện máy.

---

## 4. TỔNG KẾT RỦI RO KỸ THUẬT

| Rủi ro kỹ thuật | Hệ quả | Giải pháp kiểm soát |
| :--- | :--- | :--- |
| Thay đổi cấu trúc nhãn (Label) của mô hình ONNX | Lớp 1 không lọc được dữ liệu đầu ra từ mô hình. | Đảm bảo mô hình mới luôn sử dụng nhãn `PROD`. Cập nhật biến `entity_group` trong `gui_2.py` nếu có sự thay đổi. |
| Xung đột phiên bản thư viện AI (`onnxruntime`, `transformers`) | Tràn bộ nhớ (Memory Leak), treo tiến trình (Process Hang) trên Windows. | Khóa cố định phiên bản thư viện; áp dụng phương thức `multiprocessing.freeze_support()` khi biên dịch file thực thi (.exe). |
