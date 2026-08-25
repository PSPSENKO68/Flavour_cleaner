import openpyxl
import json
import re
import argparse
import sys

sys.stdout.reconfigure(encoding='utf-8')

def simple_tokenize(text):
    # Tách từ dựa trên khoảng trắng và dấu câu
    # Giữ lại các từ và dấu câu riêng biệt
    tokens = re.findall(r"[\w']+|[.,!?;:()\[\]{}-]", text)
    return tokens

def prepare_data(excel_path, output_jsonl):
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    sheet = wb.active
    
    # Giả định file excel có cột chứa "Original text" (Input) và "Final name" / "Cleaned name" (Output)
    # Tự động dò tìm cột
    headers = [str(cell.value).lower().strip() if cell.value else "" for cell in sheet[1]]
    
    # Tìm cột Input (original, description, input)
    input_col = None
    for i, h in enumerate(headers):
        if "original" in h or "input" in h or "mô tả" in h or "description" in h:
            input_col = i
            break
            
    # Tìm cột Output (final name, cleaned, output)
    output_col = None
    for i, h in enumerate(headers):
        if "final" in h or "clean" in h or "output" in h:
            output_col = i
            break
            
    # Fallback cho adding_rules.xlsx (Input cột 0, Output cột 1)
    if input_col is None or output_col is None:
        input_col, output_col = 0, 1
        
    print(f"Reading from Input column {input_col+1}, Output column {output_col+1}")
    
    valid_count = 0
    with open(output_jsonl, 'w', encoding='utf-8') as f:
        for row in sheet.iter_rows(min_row=2, values_only=True):
            if len(row) <= max(input_col, output_col): continue
            
            input_text = row[input_col]
            output_text = row[output_col]
            
            if not input_text or not output_text: continue
            
            input_text = str(input_text).strip()
            output_text = str(output_text).strip()
            
            # Chỉ lấy các dòng mà output thực sự nằm bên trong input
            if output_text not in input_text:
                continue
                
            # Tokenize input
            tokens = simple_tokenize(input_text)
            
            # Gán nhãn BIO
            tags = ["O"] * len(tokens)
            
            # Tokenize output để so khớp
            out_tokens = simple_tokenize(output_text)
            if not out_tokens: continue
            
            # Tìm chuỗi con out_tokens trong tokens
            match_found = False
            for i in range(len(tokens) - len(out_tokens) + 1):
                if tokens[i:i+len(out_tokens)] == out_tokens:
                    tags[i] = "B-PROD"
                    for j in range(1, len(out_tokens)):
                        tags[i+j] = "I-PROD"
                    match_found = True
                    break
            
            if match_found:
                data_obj = {
                    "tokens": tokens,
                    "ner_tags": tags
                }
                f.write(json.dumps(data_obj, ensure_ascii=False) + "\n")
                valid_count += 1
                
    print(f"Xử lý thành công! Đã tạo ra {valid_count} mẫu dữ liệu NER (BIO format) tại: {output_jsonl}")
    print("Bạn có thể upload file JSONL này lên Google Colab để train model.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chuẩn bị dữ liệu NER từ file Excel")
    parser.add_argument("input_excel", help="Đường dẫn file Excel chứa data (VD: adding_rules.xlsx hoặc file kết quả đã làm sạch)")
    parser.add_argument("--output", default="training_data.jsonl", help="Tên file output JSONL")
    args = parser.parse_args()
    
    prepare_data(args.input_excel, args.output)
