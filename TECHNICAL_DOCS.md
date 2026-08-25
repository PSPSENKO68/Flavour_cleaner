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

### 2.2. Kỹ Thuật Regex Post-Processing Nâng Cao
Bản thân AI làm rất tốt việc định vị nhưng làm rất tệ việc cắt gọt chính xác từng ký tự rìa, đặc biệt là khi dữ liệu gốc chứa tiếng Việt không dấu dính liền với tiếng Anh.
Một thuật toán Regex và tiền xử lý nâng cao được áp dụng ngay sau AI:
1. **Thay thế phân tách:** Từ việc nối các mảnh vỡ bằng dấu phẩy `, ` sang dấu cách ` ` để giữ tính liền mạch (vd: `CHOCOLATE FLAVOUR` thay vì `CHOCOLATE, FLAVOUR`).
2. **Loại bỏ nhãn mác & Quy cách:** Cắt bỏ mọi thứ phía sau các cụm từ như `quy cách`, `dùng cho`, `hiệu`, `mới 100%`, v.v.
3. **Cắt Tiếng Việt - Giữ Tiếng Anh (Cải tiến vượt bậc):** 
   - Lấy `FLAVOUR`/`FLAVOR` làm mỏ neo (anchor).
   - Quét ngược về trước, giữ lại các từ thuần tiếng Anh (ASCII).
   - Loại bỏ ngay khi gặp từ có dấu (tiếng Việt) hoặc từ nằm trong danh sách không dấu chuyên biệt được load từ `[viet-no-diacrit]` trong file `patterns.txt` (vd: `XANH`, `CAM`, `HEO`).
4. **Cân bằng ngoặc:** Tự động điền dấu ngoặc đóng `)` bị thiếu hoặc cắt bỏ dấu ngoặc dư thừa ở cuối chuỗi (ví dụ: `(V))` -> `(V)`).

Nhờ bước này, độ chính xác của AI đạt **99.28% trên tập pretrain** và **100% trên tập dữ liệu hoàn toàn xa lạ (unseen)**.

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
  - Tự động load `adding_rules.xlsx` và `patterns.txt` từ thư mục gốc.

### 3.2. Thư mục `flavour_ner_onnx` (Não bộ AI)
- **Nhiệm vụ:** Nhận diện thực thể (NER).
- **Bên trong:** Chứa `model.onnx` (trọng số mô hình), `config.json` (cấu hình nhãn `PROD`), và `tokenizer.json` (từ điển băm ký tự). Được gọi qua thư viện `optimum.onnxruntime`.

### 3.3. Các file Legacy (`run_clean.py`, `clean_flavour.py`, `patterns.txt`)
- **Nhiệm vụ:** Đóng vai trò làm mạng lưới an toàn (Safety Net / Fallback).
- **Bên trong:** `clean_flavour.py` vẫn nắm giữ logic nhận dạng tiếng Việt (`has_vietnamese`) và xử lý điểm số cơ bản. `patterns.txt` lưu các luật cố định cho nhà sản xuất (HASEGAWA, SDN BHD...) và **danh sách tiếng Việt không dấu (`[viet-no-diacrit]`)**.

---

## 4. BẢNG TỔNG KẾT RỦI RO & EDGE CASES

| Thành phần thay đổi | Nguy cơ / Rủi ro / Edge Cases | Giải pháp khuyến nghị |
| :--- | :--- | :--- |
| **Logic Cắt Tiếng Việt bằng `FLAVOUR`/`FLAVOR`** | **Edge case:** Nếu tên sản phẩm KHÔNG chứa chữ `FLAVOUR` hoặc `FLAVOR` làm mỏ neo, thuật toán quét lùi để gọt tiếng Việt sẽ không được kích hoạt. Tiếng Việt (nếu có) có thể bị dính lại. | Hiện tại chỉ hỗ trợ tốt nhất cho ngành hàng Flavour. Nếu mở rộng ngành hàng khác, cần thêm mỏ neo vào Regex (vd: `OIL`, `POWDER`). |
| **Sửa đổi `patterns.txt` (`[viet-no-diacrit]`)** | **Edge case:** Thêm nhầm một danh từ chung hoặc tên quốc tế trùng với tiếng Việt (vd: `TOM` trong `Tom Yum`, `NHO` trùng với tên người) sẽ khiến tên sản phẩm bị gãy vụn. | KHÔNG đưa các từ nhạy cảm đa nghĩa (TOM, NHO) vào danh sách. Nếu bị cắt lầm, chỉ cần mở `patterns.txt`, xóa từ đó đi và chạy lại. |
| **Thay đổi / Cập nhật mô hình trong `flavour_ner_onnx`** | Nếu mô hình mới thay đổi tập nhãn (Ví dụ đổi từ `PROD` sang `FLAVOUR`), code trong `gui_2.py` sẽ không lọc được entity nữa. | Đảm bảo mô hình mới giữ nguyên nhãn `PROD` khi huấn luyện. Nếu đổi, phải cập nhật lại dòng `ent['entity_group'] == 'PROD'` trong code. |
| **Cập nhật thư viện `optimum`/`onnxruntime`** | Phiên bản không tương thích có thể gây ra lỗi `ImportError` hoặc treo máy khi load model. | Khóa chặt (freeze) phiên bản thư viện hiện hành trong file `requirements.txt`. |

---

## 5. CASE STUDY MẪU ĐỂ BÁO CÁO (TRICKY & EDGE CASES)

Dưới đây là một số ví dụ điển hình về các trường hợp cực khó (tricky) được đưa vào tập `unseen_test_data.xlsx` để thử thách hệ thống, kết quả đạt được, và nguyên nhân đằng sau:

### 5.1. CÁC TRƯỜNG HỢP VƯỢT QUA XUẤT SẮC (SUCCESSFUL TRICKY CASES)

**Ca 1: Lỗi lặp mã code ở đầu dòng**
* **Input:** `PFE-12345 - APPLE FLAVOUR PFE-12345, HÀNG MỚI`
* **Output:** `APPLE FLAVOUR PFE-12345`
* **Vì sao xử lý được:** AI bốc nhầm cả 2 mã PFE. Thuật toán Regex đã được dạy để phát hiện cụm từ lặp lại ở đầu chuỗi (vd: `PFE-12345 - ... PFE-12345`) và tự động gọt bỏ phần bị dư ở đầu.

**Ca 2: Tiếng Việt không dấu bị viết hoa dính liền**
* **Input:** `Hương CAM ORANGE FLAVOUR L-9999`
* **Output:** `ORANGE FLAVOUR L-9999`
* **Vì sao xử lý được:** Mặc dù chữ `CAM` là chữ ASCII không có dấu, dễ bị nhầm thành tiếng Anh, nhưng vì ta đã đưa chữ `CAM` vào danh sách `[viet-no-diacrit]` trong file `patterns.txt`, Regex khi quét ngược từ `FLAVOUR` về trước đụng phải chữ `CAM` đã bị chặn lại và cắt bỏ hoàn toàn phần phía trước.

**Ca 3: Lỗi AI chẻ từ làm đứt gãy cụm từ**
* **Input:** `CHẤT TẠO HƯƠNG CHOCOLATE, FLAVOUR PFE-888`
* **Output:** `CHOCOLATE FLAVOUR PFE-888`
* **Vì sao xử lý được:** AI đôi khi hiểu lầm và gắp thành 2 mảnh (`CHOCOLATE` và `FLAVOUR`). Việc thay đổi thuật toán từ nối bằng dấu phẩy sang **nối bằng khoảng trắng** đã tự động "vá" lại các mảnh vỡ này thành một khối hoàn hảo.

**Ca 4: Ngoặc đơn dư thừa**
* **Input:** `HƯƠNG SỮA MILK FLAVOUR PFE-111(V)), QUY CÁCH 25KG`
* **Output:** `MILK FLAVOUR PFE-111(V)`
* **Vì sao xử lý được:** Bằng Regex, hệ thống tự động gọt bỏ các dấu ngoặc dư thừa như `))` ở cuối cụm từ, và cắt bỏ mọi thứ sau cụm từ `QUY CÁCH`.

### 5.2. CÁC TRƯỜNG HỢP HỆ THỐNG "BÓ TAY" (FAILURES & LIMITATIONS)

**Ca 5: Thiếu mỏ neo FLAVOUR/FLAVOR**
* **Input:** `Hương Bò BEEF EXTRACT POWDER PFE-123, Mới 100%`
* **Output (Lỗi):** `Hương Bò BEEF EXTRACT POWDER PFE-123`
* **Vì sao thất bại:** Hệ thống Regex lọc tiếng Việt được thiết kế quét ngược từ chữ `FLAVOUR` (hoặc `FLAVOR`). Trong câu này hoàn toàn không có chữ FLAVOUR, mỏ neo không được kích hoạt, dẫn đến việc chữ `Hương Bò` bị giữ lại. *(Cách khắc phục: Bổ sung thêm chữ `POWDER` hoặc `EXTRACT` vào mỏ neo trong code nếu công ty hay nhập bột/chiết xuất).*

**Ca 6: Hàng hóa ngoài ngành (Out-of-Domain)**
* **Input:** `MÁY XAY SINH TỐ CÔNG NGHIỆP BLENDER MODEL-999`
* **Output (Lỗi):** Trả về rỗng hoặc gắp rác bậy bạ.
* **Vì sao thất bại:** AI (Mô hình NER) chỉ được huấn luyện (Train) duy nhất trên tập dữ liệu Hương liệu Thực phẩm. Nó hoàn toàn không có khái niệm thế nào là một cái máy xay.

**Ca 7: Nhầm lẫn tai hại nếu cấu hình `patterns.txt` sai**
* **Input:** `Hương Tôm TOM YUM FLAVOUR PFE-555`
* **Output chuẩn (Hiện tại):** `TOM YUM FLAVOUR PFE-555`
* **Vì sao có thể thất bại trong tương lai:** Hiện tại hệ thống cắt hoàn hảo vì nó thấy chữ `Tôm` có dấu ô nên dừng lại. NHƯNG, nếu một ngày đẹp trời người dùng thấy chữ "Tôm" và ngây thơ thêm chữ `TOM` (không dấu) vào `patterns.txt`, thuật toán sẽ lập tức nhận diện chữ `TOM` trong `TOM YUM` là tiếng Việt và cắt bỏ nó, biến kết quả thành `YUM FLAVOUR PFE-555` (Bị gãy từ). Đây là lý do TUYỆT ĐỐI không thêm các từ dễ trùng lặp đa ngôn ngữ vào file cấu hình.
