import os
import json
import re
from pathlib import Path
from transformers import AutoTokenizer, pipeline
from optimum.onnxruntime import ORTModelForTokenClassification
from openpyxl import load_workbook
import sys

# Thêm đường dẫn để import
BASE_DIR = r"C:\Users\duy.nguyenhk\Downloads\flavour-cleaner_improve"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from clean_flavour import clean_description, Vocabulary
import run_clean

# Đường dẫn
MODEL_PATH = os.path.join(BASE_DIR, "ml_trainer", "model_version4", "flavour_ner_onnx")
EXCEL_PATH = os.path.join(BASE_DIR, "ml_trainer", "pretrain_data.xlsx")
OUTPUT_EXCEL_PATH = os.path.join(BASE_DIR, "ml_trainer", "test_model", "pretrain_data_output.xlsx")
RULES_PATH = os.path.join(BASE_DIR, "adding_rules.xlsx")

def regex_post_processing(text):
    text = text.strip()
    text = re.sub(r'^([0-9]+,\s*)+', '', text)
    
    text = re.sub(r'^(S,\s*Ô?,\s*CÔLA\s+PFE-\d+\s*,?|S,\s*CÔLA\s+PFE-\d+\s*,?)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^(\d{2,5},\s*)', '', text)
    
    text = re.split(r',\s*(dạng|quy cách|hiệu|nhãn hiệu|hàng mẫu|dùng cho|mới\s*\d*|\d+\s*(túi|chai|kg|g|ml|kgs|drum|carton|bottle))', text, flags=re.IGNORECASE)[0]
    
    text = re.sub(r'\s*MỚI(\s*100%)?$', '', text, flags=re.IGNORECASE)
    text = re.sub(r',\s*\d*\s*KGS?\s+(COATEDDRUM|POLYBOTTLE).*$', '', text, flags=re.IGNORECASE)
    
    text = re.sub(r'^[\:\;\-\,]+', '', text)
    text = re.sub(r'[\:\;\-\,]+$', '', text)
    text = text.strip()
    
    # Cắt mã lặp lại ở đầu chuỗi (vd: PFE-18610-SEAWEED... PFE-18610 -> SEAWEED... PFE-18610)
    match = re.match(r'^([A-Z0-9]+[\-\s]*\d+)[\-\s]+(.*)$', text, re.IGNORECASE)
    if match:
        code = match.group(1).strip()
        rest = match.group(2).strip()
        if code and len(code) >= 4 and code.lower() in rest.lower():
            text = rest
    
    if '(' in text and ')' not in text:
        text += ')'
    elif ')' in text and '(' not in text:
        text = text.replace(')', '')
        
    return text.strip()

def main():
    print("Loading ONNX model and tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    model = ORTModelForTokenClassification.from_pretrained(MODEL_PATH)

    ner_pipeline = pipeline("token-classification", model=model, tokenizer=tokenizer, aggregation_strategy="simple")
    
    print("Loading vocab and rules...")
    vocab = Vocabulary.load()
    custom_patterns = []
    if os.path.exists(RULES_PATH):
        custom_patterns = run_clean.load_custom_rules(Path(RULES_PATH))

    print(f"Reading excel file: {EXCEL_PATH}")
    wb = load_workbook(EXCEL_PATH)
    ws = wb.active

    ws["C1"] = "model_output"
    ws["D1"] = "source"

    print("Running model for prediction. Please wait...")
    
    for row in range(2, ws.max_row + 1):
        input_text = ws[f"A{row}"].value
        
        if input_text and isinstance(input_text, str):
            # Engine 1: Custom Rules
            res_custom = None
            if custom_patterns:
                res_custom = run_clean.apply_custom_rules(input_text, custom_patterns)
            cleaned_custom = regex_post_processing(res_custom.name) if res_custom else ""
            
            # Engine 2: AI
            results = ner_pipeline(input_text)
            extracted_ai = [ent['word'] for ent in results if ent['entity_group'] == 'PROD']
            
            # --- LỌC RÁC THÔNG MINH TRÊN TỪNG MẢNH AI BỐC ĐƯỢC ---
            filtered_ai = []
            for part in extracted_ai:
                part = part.strip()
                if re.fullmatch(r'[\-\+]?\d+', part) or (len(part) <= 2 and not any(c.isalpha() for c in part)):
                    continue
                if re.search(r'(KGS?|COATE|RUM X|POLYBOTTLE|CAS\s*\d|\bN\b|\bNSX\b)', part, re.IGNORECASE):
                    continue
                filtered_ai.append(part)
                
            raw_ai_text = " ".join(filtered_ai) if filtered_ai else ""
            cleaned_ai = regex_post_processing(raw_ai_text)
            
            # Engine 3: Old Rules
            res_old = clean_description(input_text, vocab)
            
            best_text = ""
            source = ""
            
            if cleaned_custom:
                if cleaned_ai and cleaned_ai in cleaned_custom:
                    prefix = cleaned_custom.split(cleaned_ai)[0]
                    if prefix and not re.search(r'[^a-zA-ZáàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđĐ\s\(\)\[\]]', prefix):
                        best_text = prefix + cleaned_ai
                        source = "Cleaned (AI + Rules Hybrid)"
                    else:
                        best_text = cleaned_custom
                        source = "Cleaned (Custom Rules)"
                else:
                    best_text = cleaned_custom
                    source = "Cleaned (Custom Rules)"
            elif cleaned_ai:
                best_text = cleaned_ai
                source = "Cleaned (AI Core)"
                
            if not best_text:
                if res_old and res_old.confidence >= 0.95:
                    best_text = res_old.name
                    source = "Cleaned (Old Rules)"
                
            ws[f"C{row}"] = best_text
            ws[f"D{row}"] = source
            
        if row % 100 == 0:
            print(f"Processed {row}/{ws.max_row} rows")

    print(f"Saving output file to: {OUTPUT_EXCEL_PATH}")
    wb.save(OUTPUT_EXCEL_PATH)
    print("Done! You can open the output file to view the results.")

if __name__ == "__main__":
    main()
