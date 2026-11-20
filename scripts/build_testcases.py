"""Gộp các file test case CSV vào file Excel theo đúng template của môn học.

Mỗi task viết test case vào docs/testcases/S3-xx.csv (5 cột như template). Script này:
  - kiểm tra từng file: đủ 5 cột đúng tên, không bỏ trống ô nào;
  - chép vào "Testing Document Template.xlsx" của cô (giữ nguyên sheet, cột, định dạng tiêu đề);
  - đánh lại mã TC01, TC02, ... liên tục theo thứ tự task.

Chạy ở thư mục gốc dự án:
  python scripts/build_testcases.py --check   # chỉ kiểm tra CSV, dùng trước khi tạo PR
  python scripts/build_testcases.py           # tạo docs/Testing Document - Group04.xlsx
"""
import argparse
import csv
import re
import sys
from copy import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASE_DIR = ROOT / "docs" / "testcases"
TEMPLATE = CASE_DIR / "Testing Document Template.xlsx"
OUTPUT = ROOT / "docs" / "Testing Document - Group04.xlsx"
HEADERS = ["Test Case ID", "Function", "Test Steps", "Input Data", "Expected Result"]
LINE_HEIGHT = 14.5  # chiều cao một dòng chữ Calibri 11 trong Excel


def task_files(folder):
    """Các file S3-xx.csv, sắp theo số task (S3-02 trước S3-10). File bắt đầu bằng _ là mẫu, bỏ qua."""
    files = [p for p in folder.glob("S3-*.csv")]
    return sorted(files, key=lambda p: [int(n) if n.isdigit() else n for n in re.split(r"(\d+)", p.name)])


def read_cases(path):
    """Đọc một file CSV, trả về (danh sách dòng, danh sách lỗi)."""
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return [], [f"{path.name}: không đọc được tiếng Việt. Hãy lưu lại dạng 'CSV UTF-8' (xem docs/huong-dan/4-kiem-thu.md)."]
    delimiter = ";" if text.split("\n", 1)[0].count(";") > text.split("\n", 1)[0].count(",") else ","
    reader = csv.reader(text.splitlines(keepends=True), delimiter=delimiter)
    rows = [[cell.strip() for cell in row] for row in reader if any(cell.strip() for cell in row)]
    if not rows:
        return [], [f"{path.name}: file trống."]
    if rows[0] != HEADERS:
        return [], [f"{path.name}: dòng tiêu đề phải đúng là: {','.join(HEADERS)}"]
    cases, errors = [], []
    for line, row in enumerate(rows[1:], start=2):
        if len(row) != len(HEADERS):
            errors.append(f"{path.name} dòng {line}: cần đúng 5 cột, đang có {len(row)} (ô có dấu phẩy/xuống dòng phải nằm trong ngoặc kép).")
            continue
        missing = [h for h, cell in zip(HEADERS, row) if not cell]
        if missing:
            errors.append(f"{path.name} dòng {line} ({row[0] or 'chưa có mã'}): còn trống {', '.join(missing)}.")
            continue
        cases.append(row)
    if not cases and not errors:
        errors.append(f"{path.name}: chưa có test case nào.")
    return cases, errors


def wrapped_lines(text, column_width):
    """Số dòng hiển thị của ô sau khi Excel tự xuống dòng (ước lượng 1 ký tự ~ 1 đơn vị độ rộng cột)."""
    per_line = max(int(column_width or 10) - 1, 1)
    return sum(max(1, -(-len(line) // per_line)) for line in text.split("\n"))


def build(cases, output):
    from openpyxl import load_workbook

    workbook = load_workbook(TEMPLATE)
    sheet = workbook.active
    if [c.value for c in sheet[1]][: len(HEADERS)] != HEADERS:
        sys.exit("Template đã bị sửa dòng tiêu đề; lấy lại file gốc từ Elearning.")
    style = [copy(c._style) for c in sheet[2][: len(HEADERS)]]  # định dạng dòng dữ liệu mẫu của cô
    sheet.delete_rows(2, sheet.max_row)  # bỏ 3 dòng ví dụ TC01-TC03 của template
    for i, (_, function, steps, data, expected) in enumerate(cases, start=1):
        row = i + 1
        values = [f"TC{i:02d}", function, steps, data, expected]
        for col, (value, cell_style) in enumerate(zip(values, style), start=1):
            cell = sheet.cell(row=row, column=col, value=value)
            cell._style = copy(cell_style)
        sheet.row_dimensions[row].height = max(2, max(
            wrapped_lines(value, sheet.column_dimensions[letter].width) for value, letter in zip(values, "ABCDE")
        )) * LINE_HEIGHT
    workbook.save(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="chỉ kiểm tra file CSV, không tạo Excel")
    parser.add_argument("--dir", type=Path, default=CASE_DIR, help="thư mục chứa S3-xx.csv")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    files = task_files(args.dir)
    if not files:
        sys.exit(f"Chưa có file S3-xx.csv nào trong {args.dir}")
    all_cases, all_errors = [], []
    for path in files:
        cases, errors = read_cases(path)
        print(f"  {path.name}: {len(cases)} test case" + (f", {len(errors)} lỗi" if errors else ""))
        all_cases += cases
        all_errors += errors
    if all_errors:
        print("\nCần sửa:", *all_errors, sep="\n  - ")
        sys.exit(1)
    print(f"Tổng: {len(all_cases)} test case, hợp lệ.")
    if not args.check:
        build(all_cases, args.output)
        print(f"Đã tạo {args.output.relative_to(ROOT) if args.output.is_relative_to(ROOT) else args.output}")


if __name__ == "__main__":
    main()
