import pandas as pd

excel_path = r"C:\Users\duy.nguyenhk\Downloads\flavour-cleaner_improve\ml_trainer\test_model\pretrain_data_output.xlsx"
df = pd.read_excel(excel_path)

# Cột 0: Input, Cột 1: Output (expected), Cột 2: model_output
df['Output'] = df.iloc[:, 1].fillna('').astype(str).str.strip()
df['model_output'] = df.iloc[:, 2].fillna('').astype(str).str.strip()

# Loại bỏ trường hợp "nan" do pandas điền
df['Output'] = df['Output'].replace('nan', '')
df['model_output'] = df['model_output'].replace('nan', '')

total = len(df)
exact_match = (df['Output'] == df['model_output']).sum()
diff_count = total - exact_match

with open("diff_results.txt", "w", encoding="utf-8") as f:
    f.write(f"Total rows: {total}\n")
    f.write(f"Exact match: {exact_match} ({(exact_match/total)*100:.2f}%)\n")
    f.write(f"Differences: {diff_count} ({(diff_count/total)*100:.2f}%)\n")
    
    f.write("\n--- DIFFERENCES (Top 20) ---\n")
    differences = df[df['Output'] != df['model_output']]
    for i, row in differences.head(20).iterrows():
        f.write(f"Row {i+2}:\n")
        f.write(f"  Input:    {row.iloc[0]}\n")
        f.write(f"  Expected: {row['Output']}\n")
        f.write(f"  Model:    {row['model_output']}\n")
        f.write("-" * 50 + "\n")

