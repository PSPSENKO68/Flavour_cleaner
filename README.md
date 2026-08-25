# Flavour Cleaner AI (Offline Edition)

Hệ thống bóc tách tự động tên thương mại (tiếng Anh) từ cột mô tả hàng hóa tự do trong tờ khai hải quan Việt Nam, được trợ lực bởi trí tuệ nhân tạo (PhoBERT NER).

```
IN:   Hương Bò BEEF EXTRACT POWDER PFE-123, Mới 100%
OUT:  BEEF EXTRACT POWDER PFE-123
```

**⚠️ ĐIỂM ĐẶC BIỆT:** Phiên bản AI này chạy hoàn toàn nội bộ (100% Offline) trên máy tính cá nhân. Dữ liệu hải quan nhạy cảm của bạn sẽ không bao giờ bị gửi lên mạng hay thông qua bất kỳ API bên ngoài nào.

---

## 🚀 Hướng Dẫn Sử Dụng Nhanh (Dành cho Windows)

Hệ thống được thiết kế dưới dạng ứng dụng giao diện (GUI) thân thiện và rất dễ sử dụng.

### Cài đặt lần đầu
1. Máy tính cần được cài đặt sẵn **Python 3.9** trở lên (nhớ tick chọn *"Add Python to PATH"* khi cài đặt).
2. Mở Command Prompt (Terminal) tại thư mục chứa mã nguồn và chạy lệnh cài đặt thư viện:
   ```bash
   pip install -r requirements.txt
   ```

### Chạy ứng dụng
1. Click đúp chuột vào file **`Start_Flavour_Cleaner.bat`** (hoặc chạy lệnh `python gui_2.py` trong terminal).
2. Giao diện Desktop sẽ hiện lên.
3. Bấm **Chọn file** và chỉ đường dẫn tới file Excel hải quan của bạn.
4. Chọn đúng **Sheet** và **Cột chứa dữ liệu mô tả**.
5. Nhấn **Bắt đầu** và chờ AI bóc tách (Tốc độ ~800 dòng / 24 giây trên CPU thường).
6. Khi hoàn tất, các dòng chữ màu Xanh biểu thị kết quả thành công. Bấm **Lưu File** để trích xuất ra một file Excel mới.
   *(File Excel gốc của bạn sẽ không bao giờ bị ghi đè hay thay đổi).*

---

## 🧠 Sức Mạnh Bên Trong (Under The Hood)

Để biết chi tiết về cách hệ thống hoạt động, vui lòng xem tài liệu:
👉 **[TÀI LIỆU KỸ THUẬT CHI TIẾT (TECHNICAL_DOCS.md)](TECHNICAL_DOCS.md)**

Tóm tắt luồng xử lý tự động (Cascading Pipeline):
1. **Lớp 1 (Mô hình Học máy NER):** AI (PhoBERT nén ONNX) đọc hiểu ngữ cảnh và chỉ trích xuất các từ mang ý nghĩa sản phẩm, tự động loại bỏ rác tiếng Việt.
2. **Lớp 2 (Regex Post-Processing):** Nếu AI lấy lầm một chữ tiếng Việt, hệ thống dùng Regex (mỏ neo FLAVOUR) để quét ngược và gọt bỏ tiếng Việt dư thừa, đồng thời dọn rác quy cách (NSX, HSD...).
3. **Lớp 3 (Rules Fallback):** Nếu AI thất bại hoàn toàn, hệ thống tự động kích hoạt thuật toán Heuristic truyền thống để chấm điểm từ khóa và cứu vớt dữ liệu (đảm bảo phần mềm không bao giờ bị đứng).

---

## ⚙️ Cấu Hình Nâng Cao

Hệ thống cho phép bạn tùy chỉnh một số quy tắc gọt tiếng Việt thông qua file `patterns.txt`:
- Mở file `patterns.txt`.
- Tìm đến mục `[viet-no-diacrit]`.
- Bạn có thể thêm các từ tiếng Việt không dấu dễ bị dính vào tên sản phẩm (vd: `HEO`, `BO`, `CHUOI`).
- **LƯU Ý:** Không được thêm các từ tiếng Anh thông dụng trùng với tiếng Việt (ví dụ: Không thêm `TOM` vì sẽ làm hỏng tên sản phẩm `Tom Yum`).
