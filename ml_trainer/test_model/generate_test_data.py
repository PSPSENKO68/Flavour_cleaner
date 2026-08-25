import pandas as pd
import random

prefixes = [
    "Nguyên liệu sản xuất kẹo: Hương {vi_name} (",
    "Nguyên liệu sx thực phẩm: Hương {vi_name} - ",
    "PHỤ GIA THỰC PHẨM: HƯƠNG {vi_name_upper} ",
    "MẪU HƯƠNG LIỆU THỰC PHẨM: ",
    "Hương liệu thực phẩm dạng lỏng: ",
    "Nguyên liệu dùng trong công nghiệp thực phẩm: Hương {vi_name} ",
    "",
    "Hương {vi_name} "
]

suffixes = [
    "), loại có alcohol, nhưng không có cồn ethanol. Mới 100%",
    " - MẪU HƯƠNG LIỆU LỎNG THỬ NGHIỆM, NSX: T HASEGAWA, F.O.C, MỚI 100%",
    ". Hàng nhập khẩu mới 100%, quy cách 25Kg/Drum.",
    " dùng cho thực phẩm. HSD: 12/2026, 15kg/can.",
    ", nhãn hiệu Hasegawa, đóng gói 10kg/thùng carton.",
    " MỚI 100%",
    " (Dùng trong sản xuất nước giải khát)",
    ""
]

flavours_map = {
    "APPLE": "Táo", "ORANGE": "Cam", "MANGO": "Xoài", "VANILLA": "Vani", 
    "CHICKEN": "Gà", "BEEF": "Bò", "PORK": "Heo", "CHEESE": "Phô mai", 
    "MILK": "Sữa", "COFFEE": "Cà phê", "GREEN TEA": "Trà xanh", 
    "STRAWBERRY": "Dâu", "PEACH": "Đào", "TARO": "Khoai môn", 
    "COCONUT": "Dừa", "BANANA": "Chuối", "MELON": "Dưa lưới", 
    "CHOCOLATE": "Sô-cô-la", "BLUEBERRY": "Việt quất", "SEAFOOD": "Hải sản"
}

code_types = ["HFE", "PFE", "FE", "L", "AC"]

data = []

for i in range(100):
    en_base = random.choice(list(flavours_map.keys()))
    vi_name = flavours_map[en_base]
    code_type = random.choice(code_types)
    code_num = random.randint(10000, 99999)
    suffix_char = random.choice(["", "(V)", "A", "-1"])
    
    # Tạo Expected Target (Tên hương liệu chuẩn theo format AI hay thấy)
    flavour_str = f"{en_base} FLAVOUR {code_type}-{code_num}{suffix_char}"
    # Đôi khi viết là FLAVOR
    if random.random() > 0.7:
        flavour_str = flavour_str.replace("FLAVOUR", "FLAVOR")
        
    prefix = random.choice(prefixes).format(
        vi_name=vi_name, 
        vi_name_upper=vi_name.upper()
    )
    suffix = random.choice(suffixes)
    
    # Ghép chuỗi lại
    # Xử lý trường hợp đóng ngoặc nếu prefix có mở ngoặc
    if "(" in prefix and ")" not in prefix and not suffix.startswith(")"):
        full_text = prefix + flavour_str + ")" + suffix
    else:
        full_text = prefix + flavour_str + suffix
        
    # Làm nhiễu một chút (cố tình viết hoa viết thường lộn xộn hoặc dư khoảng trắng)
    if random.random() > 0.8:
        full_text = full_text.upper()
    
    data.append({
        "Input": full_text.strip(),
        "Expected_Output": flavour_str
    })

# --- TRICKY & EDGE CASES DÀNH CHO SẾP ---
edge_cases = [
    # 1. Tricky nhưng thành công: Mã code bị lặp lại ở đầu
    {"Input": "PFE-12345 - APPLE FLAVOUR PFE-12345, HÀNG MỚI", "Expected_Output": "APPLE FLAVOUR PFE-12345"},
    # 2. Tricky nhưng thành công: Dính liền tiếng Việt không dấu (CAM) nhưng đã được filter qua patterns.txt
    {"Input": "Hương CAM ORANGE FLAVOUR L-9999", "Expected_Output": "ORANGE FLAVOUR L-9999"},
    # 3. Tricky nhưng thành công: Dấu phẩy xen giữa chữ do lỗi AI chẻ từ
    {"Input": "CHẤT TẠO HƯƠNG CHOCOLATE, FLAVOUR PFE-888", "Expected_Output": "CHOCOLATE FLAVOUR PFE-888"},
    # 4. Tricky nhưng thành công: Ngoặc kép dư thừa ở cuối
    {"Input": "HƯƠNG SỮA MILK FLAVOUR PFE-111(V)), QUY CÁCH 25KG", "Expected_Output": "MILK FLAVOUR PFE-111(V)"},
    
    # 5. THẤT BẠI: Thiếu mỏ neo FLAVOUR/FLAVOR (AI lấy luôn tiếng Việt nếu không có mỏ neo để Regex gọt)
    {"Input": "Hương Bò BEEF EXTRACT POWDER PFE-123, Mới 100%", "Expected_Output": "BEEF EXTRACT POWDER PFE-123"},
    
    # 6. THẤT BẠI: Ngành hàng hoàn toàn mới (Máy móc) - AI chưa từng học
    {"Input": "MÁY XAY SINH TỐ CÔNG NGHIỆP BLENDER MODEL-999", "Expected_Output": "BLENDER MODEL-999"},
    
    # 7. THẤT BẠI (Rủi ro cấu hình sai): Nếu đưa nhầm từ TOM vào patterns.txt, chữ TOM YUM sẽ bị cắt mất TOM. 
    # Nhưng vì ta KHÔNG đưa vào, nên AI vẫn giữ được, nhưng có thể dính chữ Tôm tiếng Việt nếu AI bốc nhầm.
    {"Input": "Hương Tôm TOM YUM FLAVOUR PFE-555", "Expected_Output": "TOM YUM FLAVOUR PFE-555"}
]

data.extend(edge_cases)

df = pd.DataFrame(data)
output_path = r"C:\Users\duy.nguyenhk\Downloads\flavour-cleaner_improve\ml_trainer\test_model\unseen_test_data.xlsx"
df.to_excel(output_path, index=False)
print(f"Đã tạo thành công {len(df)} dòng dữ liệu (bao gồm các Edge Cases) tại: {output_path}")
