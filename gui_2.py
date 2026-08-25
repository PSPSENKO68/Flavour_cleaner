import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import sys
import os
import re
import openpyxl

# Determine the base directory for resources
if getattr(sys, 'frozen', False):
    # Running as PyInstaller bundle
    parent_dir = os.path.dirname(sys.executable)
else:
    # Running in normal Python environment
    parent_dir = os.path.dirname(os.path.abspath(__file__))

if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    import run_clean
    from clean_flavour import Vocabulary, clean_description, CleanResult
except ImportError as e:
    messagebox.showerror("Lỗi Import", f"Không tìm thấy module cũ: {e}")

class FlavourAI_GUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Flavour Cleaner - AI Integration")
        self.geometry("1000x700")
        self.configure(padx=10, pady=10)

        # Set Window Icon
        icon_path = os.path.join(parent_dir, "logo", "logo.png")
        if os.path.exists(icon_path):
            try:
                img = tk.PhotoImage(file=icon_path)
                self.iconphoto(False, img)
            except Exception:
                pass

        # Style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview", rowheight=25)
        # Highlight màu vàng cho các dòng cần xem lại
        style.map('Treeview', background=[('selected', '#0078D7')])

        self.input_file = tk.StringVar()
        self.rules_file = tk.StringVar()
        
        # Auto-load adding_rules.xlsx from root folder if it exists
        default_rules_path = os.path.join(parent_dir, "adding_rules.xlsx")
        if os.path.exists(default_rules_path):
            self.rules_file.set(default_rules_path)
            
        self.sheet_name = tk.StringVar()
        self.col_name = tk.StringVar()
        
        self.book = None
        self.sheets = []
        self.columns = []
        self.custom_patterns = []
        self.vocab = Vocabulary.load()

        # Variables for AI Model
        self.ai_model_loaded = False
        self.ner_pipeline = None

        self.create_widgets()

    def create_widgets(self):
        # --- Frame 1: Inputs ---
        frame1 = ttk.LabelFrame(self, text="Cấu hình File Đầu Vào", padding=10)
        frame1.pack(fill=tk.X, pady=5)
        
        # Row 1: Data File
        ttk.Label(frame1, text="1. File Data (.xlsx):").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(frame1, textvariable=self.input_file, state='readonly', width=50).grid(row=0, column=1, padx=5, sticky=tk.W)
        ttk.Button(frame1, text="Browse...", command=self.browse_input).grid(row=0, column=2, padx=5)

        # Row 2: Custom Rules
        ttk.Label(frame1, text="2. Custom Rules (adding_rules.xlsx):").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(frame1, textvariable=self.rules_file, state='readonly', width=50).grid(row=1, column=1, padx=5, sticky=tk.W)
        ttk.Button(frame1, text="Browse...", command=self.browse_rules).grid(row=1, column=2, padx=5)
        ttk.Button(frame1, text="Xóa", command=lambda: self.rules_file.set("")).grid(row=1, column=3, padx=5)

        # Row 3: Sheet & Column
        ttk.Label(frame1, text="3. Sheet:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.sheet_cb = ttk.Combobox(frame1, textvariable=self.sheet_name, state="readonly", width=20)
        self.sheet_cb.grid(row=2, column=1, sticky=tk.W, padx=5)
        self.sheet_cb.bind('<<ComboboxSelected>>', self.on_sheet_selected)

        ttk.Label(frame1, text="Column:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.col_cb = ttk.Combobox(frame1, textvariable=self.col_name, state="readonly", width=20)
        self.col_cb.grid(row=3, column=1, sticky=tk.W, padx=5)

        ttk.Button(frame1, text="Load Data Preview", command=self.load_preview).grid(row=2, column=2, rowspan=2, sticky=tk.NSEW, padx=5, pady=5)

        # --- Frame 2: Action Buttons ---
        frame2 = ttk.Frame(self)
        frame2.pack(fill=tk.X, pady=5)
        
        self.btn_pipeline = ttk.Button(frame2, text="1. Run Full Auto Clean (AI + Regex)", command=self.run_pipeline)
        self.btn_pipeline.pack(side=tk.LEFT, padx=5)
        
        self.btn_save = ttk.Button(frame2, text="3. Save As...", command=self.save_as)
        self.btn_save.pack(side=tk.RIGHT, padx=5)

        # --- Frame 3: Data Preview (Treeview) ---
        frame3 = ttk.LabelFrame(self, text="Preview Data (Các dòng vàng là chưa cắt được hoặc độ tin cậy thấp)", padding=10)
        frame3.pack(fill=tk.BOTH, expand=True, pady=5)
        
        columns = ("row_idx", "input", "output", "status")
        self.tree = ttk.Treeview(frame3, columns=columns, show="headings", selectmode="browse")
        
        self.tree.heading("row_idx", text="Row")
        self.tree.column("row_idx", width=50, anchor=tk.CENTER)
        
        self.tree.heading("input", text="Original Text (Input)")
        self.tree.column("input", width=400, anchor=tk.W)
        
        self.tree.heading("output", text="Cleaned Text (Output)")
        self.tree.column("output", width=250, anchor=tk.W)
        
        self.tree.heading("status", text="Status")
        self.tree.column("status", width=150, anchor=tk.CENTER)
        
        # Scrollbars
        y_scroll = ttk.Scrollbar(frame3, orient=tk.VERTICAL, command=self.tree.yview)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        x_scroll = ttk.Scrollbar(frame3, orient=tk.HORIZONTAL, command=self.tree.xview)
        x_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Define tags for colors
        self.tree.tag_configure("amber", background="#FFF2CC")
        self.tree.tag_configure("success", background="#E2EFDA")
        
        # Status Label
        self.status_var = tk.StringVar()
        self.status_var.set("Sẵn sàng.")
        ttk.Label(self, textvariable=self.status_var, font=("Arial", 10, "italic")).pack(side=tk.BOTTOM, anchor=tk.W)

    def browse_input(self):
        filename = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
        if filename:
            self.input_file.set(filename)
            self.load_excel_info(filename)

    def browse_rules(self):
        filename = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
        if filename:
            self.rules_file.set(filename)

    def load_excel_info(self, filename):
        self.status_var.set(f"Đang đọc dữ liệu từ {os.path.basename(filename)}...")
        self.update_idletasks()
        try:
            self.book = openpyxl.load_workbook(filename, read_only=True, data_only=True)
            self.sheets = self.book.sheetnames
            self.sheet_cb['values'] = self.sheets
            if self.sheets:
                self.sheet_cb.current(0)
                self.on_sheet_selected(None)
            self.status_var.set("Đã đọc danh sách sheet thành công.")
        except Exception as e:
            self.status_var.set(f"Lỗi: {e}")
            messagebox.showerror("Error", f"Không thể đọc file Excel:\n{e}")

    def on_sheet_selected(self, event):
        sheet_name = self.sheet_name.get()
        if not sheet_name: return
        try:
            sheet = self.book[sheet_name]
            headers = []
            for row in sheet.iter_rows(min_row=1, max_row=10, values_only=True):
                if any(row):
                    headers = [str(cell) if cell else f"Col {i+1}" for i, cell in enumerate(row)]
                    break
            
            if headers:
                from openpyxl.utils import get_column_letter
                self.columns = [f"{get_column_letter(i+1)} - {h}" for i, h in enumerate(headers)]
                self.col_cb['values'] = self.columns
                self.col_cb.current(0)
        except Exception as e:
            self.status_var.set(f"Lỗi đọc sheet: {e}")

    def load_preview(self):
        if not self.book or not self.sheet_name.get() or not self.col_name.get():
            messagebox.showwarning("Warning", "Vui lòng chọn File, Sheet và Column.")
            return

        # Clear treeview
        for item in self.tree.get_children():
            self.tree.delete(item)

        sheet = self.book[self.sheet_name.get()]
        col_letter = self.col_name.get().split(" - ")[0]
        from openpyxl.utils import column_index_from_string
        col_idx = column_index_from_string(col_letter)

        self.status_var.set("Đang tải dữ liệu lên bảng preview...")
        self.update_idletasks()

        # Giả định dòng 1 là header, data từ dòng 2
        for row_idx, row in enumerate(sheet.iter_rows(min_row=2, max_row=sheet.max_row, values_only=True), start=2):
            val = row[col_idx - 1]
            if val is not None and str(val).strip():
                # tag mặc định là amber (màu vàng) vì chưa xử lý
                self.tree.insert("", tk.END, iid=str(row_idx), values=(row_idx, str(val).strip(), "", "Pending"), tags=("amber",))
        
        self.status_var.set(f"Đã tải {len(self.tree.get_children())} dòng.")

    def run_pipeline(self):
        if not self.tree.get_children():
            messagebox.showinfo("Info", "Bảng dữ liệu trống. Hãy nhấn 'Load Data Preview' trước.")
            return

        # Chạy pipeline trong luồng phụ để không đơ màn hình
        threading.Thread(target=self._run_pipeline_thread, daemon=True).start()

    def _run_pipeline_thread(self):
        self.status_var.set("Đang khởi tạo Pipeline...")
        self.update_idletasks()

        # Load Custom Rules if provided
        if self.rules_file.get():
            from pathlib import Path
            self.custom_patterns = run_clean.load_custom_rules(Path(self.rules_file.get()))
        else:
            self.custom_patterns = []

        # Helper function for post-processing AI and Custom Rules output
        def regex_post_processing(text):
            text = text.strip()
            # Cắt các số thứ tự ở đầu
            text = re.sub(r'^([0-9]+,\s*)+', '', text)
            
            # Cắt lỗi chẻ số hoặc chẻ chữ SÔCÔLA ở đầu chuỗi (ví dụ: "2010, CHOCOLATE" hoặc "S, CÔLA")
            text = re.sub(r'^(S,\s*Ô?,\s*CÔLA\s+PFE-\d+\s*,?|S,\s*CÔLA\s+PFE-\d+\s*,?)', '', text, flags=re.IGNORECASE)
            text = re.sub(r'^(\d{2,5},\s*)', '', text)
            
            # Cắt sau dấu phẩy các cụm từ mô tả bao bì / nhãn mác
            text = re.split(r',\s*(dạng|quy cách|hiệu|nhãn hiệu|hàng mẫu|dùng cho|mới\s*\d*|\d+\s*(túi|chai|kg|g|ml|kgs|drum|carton|bottle))', text, flags=re.IGNORECASE)[0]
            
            # Cắt "MỚI 100%" hoặc "MỚI" hoặc "KGS COATEDDRUM" nằm lọt lại ở cuối
            text = re.sub(r'\s*MỚI(\s*100%)?$', '', text, flags=re.IGNORECASE)
            text = re.sub(r',\s*\d*\s*KGS?\s+(COATEDDRUM|POLYBOTTLE).*$', '', text, flags=re.IGNORECASE)
            
            text = re.sub(r'^[\:\;\-\,]+', '', text)
            text = re.sub(r'[\:\;\-\,]+$', '', text)
            text = re.sub(r'[\:\;\-\,]+$', '', text)
            text = text.strip()
            
            # Cắt mã lặp lại ở đầu chuỗi (vd: PFE-18610-SEAWEED... PFE-18610 -> SEAWEED... PFE-18610)
            match = re.match(r'^([A-Z0-9]+[\-\s]*\d+)[\-\s]+(.*)$', text, re.IGNORECASE)
            if match:
                code = match.group(1).strip()
                rest = match.group(2).strip()
                if code and len(code) >= 4 and code.lower() in rest.lower():
                    text = rest
                    
            # Cân bằng ngoặc
            if '(' in text and ')' not in text:
                text += ')'
            elif ')' in text and '(' not in text:
                text = text.replace(')', '')
            text = re.sub(r'\)\)+$', ')', text)
            
            # --- CẮT TIẾNG VIỆT, CHỈ GIỮ TIẾNG ANH ---
            # Đọc danh sách từ tiếng Việt không dấu từ patterns.txt [viet-no-diacrit]
            viet_no_diacrit = set()
            patterns_path = os.path.join(parent_dir, "patterns.txt")
            if os.path.exists(patterns_path):
                in_section = False
                with open(patterns_path, encoding='utf-8') as pf:
                    for line in pf:
                        line = line.strip()
                        if line == '[viet-no-diacrit]':
                            in_section = True
                            continue
                        if line.startswith('[') and in_section:
                            break
                        if in_section and line and not line.startswith('#'):
                            viet_no_diacrit.add(line.upper())
            # Tìm FLAVOUR/FLAVOR làm mỏ neo, quét ngược giữ từ ASCII (tiếng Anh), bỏ từ có dấu (tiếng Việt)
            flavor_match = re.search(r'\b(FLAVOU?R)\b', text, re.IGNORECASE)
            if flavor_match:
                before = text[:flavor_match.start()]
                after = text[flavor_match.start():]
                words = before.split()
                english_start = len(words)  # mặc định: bắt đầu từ FLAVOUR
                for i in range(len(words) - 1, -1, -1):
                    word = words[i]
                    # Nếu từ nằm trong danh sách tiếng Việt không dấu -> dừng
                    if word.upper() in viet_no_diacrit:
                        break
                    # Kiểm tra từ có phải thuần ASCII không (A-Z, a-z, 0-9, dấu gạch)
                    if all(ord(c) < 128 for c in word):
                        english_start = i
                    else:
                        break  # Gặp từ tiếng Việt có dấu -> dừng
                if english_start < len(words):
                    text = ' '.join(words[english_start:]) + ' ' + after
                else:
                    text = after
                text = text.strip()
                
            return text.strip()

        items = self.tree.get_children()
        total_items = len(items)
        success_rules = 0
        success_ai = 0

        for i, item in enumerate(items):
            values = self.tree.item(item, 'values')
            input_text = values[1]
            
            # --- BƯỚC 1: LOAD AI MODEL ---
            if not self.ai_model_loaded:
                self.status_var.set("Lần đầu gọi AI: Đang load mô hình (mất vài giây)...")
                self.update_idletasks()
                from transformers import AutoTokenizer, pipeline
                from optimum.onnxruntime import ORTModelForTokenClassification
                
                model_path = os.path.join(parent_dir, "ml_trainer", "model_version4", "flavour_ner_onnx")
                if not os.path.exists(model_path):
                    messagebox.showerror("Error", f"Không tìm thấy model AI tại {model_path}")
                    self.status_var.set("Lỗi: Không thấy model.")
                    return
                
                try:
                    tokenizer = AutoTokenizer.from_pretrained(model_path)
                    model = ORTModelForTokenClassification.from_pretrained(model_path)
                    self.ner_pipeline = pipeline("token-classification", model=model, tokenizer=tokenizer, aggregation_strategy="simple")
                    self.ai_model_loaded = True
                except Exception as e:
                    messagebox.showerror("Lỗi load AI", str(e))
                    self.status_var.set("Lỗi load AI model.")
                    return

            # --- BƯỚC 2: CHẠY SONG SONG AI & CUSTOM RULES ĐỂ TÌM GIÁ TRỊ TỐT NHẤT ---
            try:
                # 1. Custom Rules
                res_custom = None
                if self.custom_patterns:
                    res_custom = run_clean.apply_custom_rules(input_text, self.custom_patterns)
                cleaned_custom = regex_post_processing(res_custom.name) if res_custom else ""
                
                # 2. AI
                results = self.ner_pipeline(input_text)
                extracted_ai = [ent['word'] for ent in results if ent['entity_group'] == 'PROD']
                
                # --- LỌC RÁC THÔNG MINH TRÊN TỪNG MẢNH AI BỐC ĐƯỢC ---
                filtered_ai = []
                for part in extracted_ai:
                    part = part.strip()
                    # Bỏ qua nếu chỉ là số (như "20106" hoặc "-20106") hoặc quá ngắn (< 3 ký tự, trừ phi chứa chữ H)
                    if re.fullmatch(r'[\-\+]?\d+', part) or (len(part) <= 2 and not any(c.isalpha() for c in part)):
                        continue
                    # Bỏ qua nếu chứa mã bao bì bị chẻ vụn (KGS, COATE, CAS, N, NSX)
                    if re.search(r'(KGS?|COATE|RUM X|POLYBOTTLE|CAS\s*\d|\bN\b|\bNSX\b)', part, re.IGNORECASE):
                        continue
                    filtered_ai.append(part)
                    
                raw_ai_text = " ".join(filtered_ai) if filtered_ai else ""
                cleaned_ai = regex_post_processing(raw_ai_text)

                # --- CHỌN KẾT QUẢ TỐT NHẤT ---
                best_text = ""
                source = ""
                
                # Lấy Custom Rules làm ưu tiên nếu có, vì nó giữ tiếng Việt tốt hơn
                # Nếu Custom Rules trống thì xài AI
                if cleaned_custom:
                    # Kiểm tra xem AI có giúp cắt gọn rác của Custom Rules không (Hybrid)
                    if cleaned_ai and cleaned_ai in cleaned_custom:
                        prefix = cleaned_custom.split(cleaned_ai)[0]
                        # Nếu tiền tố hợp lệ, ta ghép lại (Hybrid)
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
                    
                # Cập nhật UI
                if best_text:
                    self.tree.item(item, values=(values[0], input_text, best_text, source), tags=("success",))
                    if "AI" in source:
                        success_ai += 1
                    else:
                        success_rules += 1
                else:
                    # Fallback cuối cùng
                    res_old = clean_description(input_text, self.vocab)
                    if res_old and res_old.confidence >= 0.95:
                        self.tree.item(item, values=(values[0], input_text, res_old.name, "Cleaned (Old Rules)"), tags=("success",))
                        success_rules += 1
                    else:
                        self.tree.item(item, values=(values[0], input_text, "", "Failed (AI & Rules)"), tags=("amber",))
                        
            except Exception as e:
                print(f"Lỗi khi xử lý ở dòng {values[0]}: {e}")
                self.tree.item(item, values=(values[0], input_text, "", "Error"), tags=("amber",))

            # Cập nhật UI (nằm trong vòng lặp)
            if i % 10 == 0 or i == total_items - 1:
                self.status_var.set(f"Đang xử lý bằng AI... ({i+1}/{total_items})")
                self.update_idletasks()

        self.status_var.set(f"Hoàn tất! AI xử lý: {success_ai}. Rules (chữa cháy): {success_rules}.")

    def save_as(self):
        if not self.tree.get_children():
            messagebox.showinfo("Info", "Không có dữ liệu để lưu.")
            return
            
        save_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            title="Lưu file kết quả"
        )
        if not save_path:
            return

        self.status_var.set("Đang lưu file...")
        self.update_idletasks()

        try:
            # Load the original workbook (not read_only) so we can preserve structure
            input_file_path = self.input_file.get()
            wb = openpyxl.load_workbook(input_file_path)
            sheet = wb[self.sheet_name.get()]
            
            from openpyxl.utils import column_index_from_string
            col_letter = self.col_name.get().split(" - ")[0]
            col_idx = column_index_from_string(col_letter)
            
            for item in self.tree.get_children():
                values = self.tree.item(item, "values")
                row_idx = int(values[0])
                cleaned_text = str(values[2]).strip()
                
                # Nếu có kết quả sau khi cắt, thì ghi đè vào cột gốc
                if cleaned_text:
                    sheet.cell(row=row_idx, column=col_idx, value=cleaned_text)
                    
            wb.save(save_path)
            self.status_var.set(f"Đã lưu thành công tại {save_path}")
            messagebox.showinfo("Thành công", f"Đã lưu file giữ nguyên cấu trúc tại:\n{save_path}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lưu file: {e}")
            self.status_var.set("Lỗi lưu file.")

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    app = FlavourAI_GUI()
    app.mainloop()
