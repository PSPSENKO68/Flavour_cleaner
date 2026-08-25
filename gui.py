import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import sys
import os
import openpyxl

# Import existing modules
import run_clean

class FlavourCleanerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Flavour Cleaner")
        self.geometry("700x600")
        self.configure(padx=20, pady=20)

        # Style
        style = ttk.Style()
        style.theme_use('clam')

        self.input_file = tk.StringVar()
        self.rules_file = tk.StringVar()
        self.sheet_name = tk.StringVar()
        self.col_name = tk.StringVar()
        
        self.sheets = []
        self.columns = []

        self.create_widgets()

    def create_widgets(self):
        # Frame 1: Input File
        frame1 = ttk.LabelFrame(self, text="1. Chọn file Declaration (.xlsx)", padding=10)
        frame1.pack(fill=tk.X, pady=5)
        
        ttk.Entry(frame1, textvariable=self.input_file, state='readonly').pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(frame1, text="Browse...", command=self.browse_input).pack(side=tk.LEFT)

        # Frame 2: Options (Sheet, Column)
        self.frame2 = ttk.LabelFrame(self, text="2. Tùy chọn Sheet / Column", padding=10)
        self.frame2.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.frame2, text="Sheet:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.sheet_cb = ttk.Combobox(self.frame2, textvariable=self.sheet_name, state="readonly", width=30)
        self.sheet_cb.grid(row=0, column=1, sticky=tk.W, pady=5)
        self.sheet_cb.bind('<<ComboboxSelected>>', self.on_sheet_selected)

        ttk.Label(self.frame2, text="Column:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        self.col_cb = ttk.Combobox(self.frame2, textvariable=self.col_name, state="readonly", width=30)
        self.col_cb.grid(row=1, column=1, sticky=tk.W, pady=5)

        # Frame 3: Custom Rules File
        frame3 = ttk.LabelFrame(self, text="3. (Tùy chọn) Chọn file Custom Rules (adding_rules.xlsx)", padding=10)
        frame3.pack(fill=tk.X, pady=5)
        
        ttk.Entry(frame3, textvariable=self.rules_file, state='readonly').pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(frame3, text="Browse...", command=self.browse_rules).pack(side=tk.LEFT)
        ttk.Button(frame3, text="Xóa", command=lambda: self.rules_file.set("")).pack(side=tk.LEFT, padx=5)

        # Frame 4: Action
        frame4 = ttk.Frame(self)
        frame4.pack(fill=tk.X, pady=10)
        self.run_btn = ttk.Button(frame4, text="Run Flavour Cleaner (Không dùng AI)", command=self.start_processing, width=40)
        self.run_btn.pack(pady=5)

        # Frame 5: Logs
        frame5 = ttk.LabelFrame(self, text="Tiến trình chạy", padding=10)
        frame5.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_text = tk.Text(frame5, state='disabled', wrap='word', height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def log(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.update_idletasks()

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
        self.log(f"Đang đọc dữ liệu từ {os.path.basename(filename)}...")
        try:
            self.book = openpyxl.load_workbook(filename, read_only=True, data_only=True)
            self.sheets = self.book.sheetnames
            self.sheet_cb['values'] = self.sheets
            if self.sheets:
                self.sheet_cb.current(0)
                self.on_sheet_selected(None)
            self.log("Đã đọc danh sách sheet thành công.")
        except Exception as e:
            self.log(f"Lỗi đọc file: {e}")
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
                self.col_cb['values'] = ["Auto Detect"] + self.columns
                self.col_cb.current(0)
            else:
                self.col_cb['values'] = ["Auto Detect"]
                self.col_cb.current(0)
        except Exception as e:
            self.log(f"Lỗi đọc sheet: {e}")

    def start_processing(self):
        if not self.input_file.get():
            messagebox.showwarning("Warning", "Vui lòng chọn file Declaration đầu vào.")
            return

        self.run_btn.config(state='disabled')
        self.log("\n" + "="*40)
        self.log("Bắt đầu xử lý...")
        
        thread = threading.Thread(target=self.process)
        thread.start()

    def process(self):
        try:
            input_path = self.input_file.get()
            rules_path = self.rules_file.get()
            sheet = self.sheet_name.get()
            col = self.col_name.get()

            args = [input_path]
            
            if sheet:
                args.extend(["--sheet", sheet])
            if col and col != "Auto Detect":
                col_letter = col.split(" - ")[0]
                args.extend(["--col", col_letter])
            
            if rules_path:
                args.extend(["--custom-rules", rules_path])
            
            import io
            class StdoutRedirector(io.StringIO):
                def __init__(self, logger):
                    super().__init__()
                    self.logger = logger
                def write(self, s):
                    if s.strip():
                        self.logger(s.rstrip())
            
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = StdoutRedirector(self.log)
            sys.stderr = StdoutRedirector(self.log)

            try:
                run_clean.main(args)
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr

            self.log("Hoàn thành xử lý.")
        except Exception as e:
            import traceback
            self.log(f"Lỗi trong quá trình xử lý: {e}")
            self.log(traceback.format_exc())
            messagebox.showerror("Error", f"Đã xảy ra lỗi:\n{e}")
        finally:
            self.run_btn.config(state='normal')

if __name__ == "__main__":
    app = FlavourCleanerGUI()
    app.mainloop()
