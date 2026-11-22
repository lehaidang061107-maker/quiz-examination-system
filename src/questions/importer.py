"""S3-32: đọc câu hỏi từ file Excel (.xlsx) theo file mẫu và tạo file mẫu.

Mỗi dòng (từ dòng 2) là một câu hỏi một lựa chọn: Nội dung, Phương án A–F, Đáp án đúng (A–F).
Kiểm tra theo BR-07/BR-13: có nội dung, ít nhất 2 phương án điền liên tục từ A, đúng một đáp án
đúng trỏ tới phương án có nội dung. Lỗi cả file (sai định dạng, quá lớn, sai cột) báo bằng
ValidationError; lỗi từng dòng nằm trong ImportRow.errors để giao diện hiện lại cho giảng viên.
"""
from dataclasses import dataclass, field
from io import BytesIO
from zipfile import BadZipFile

from django.core.exceptions import ValidationError
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils.exceptions import InvalidFileException

MAX_FILE_BYTES = 2 * 1024 * 1024  # 2 MB
MAX_ROWS = 500
MAX_CONTENT_LENGTH = 2000
MAX_OPTION_LENGTH = 500
LETTERS = "ABCDEF"
HEADERS = ["Nội dung câu hỏi", *[f"Phương án {letter}" for letter in LETTERS], "Đáp án đúng"]
SAMPLE_ROWS = [
    ["Mô hình MVC gồm những thành phần nào?", "Model, View, Controller", "Module, Version, Client",
     "Main, Value, Config", "", "", "", "A"],
    ["Câu lệnh nào dùng để xóa bảng trong SQL?", "DELETE TABLE", "REMOVE TABLE", "DROP TABLE", "CLEAR TABLE",
     "", "", "C"],
]
GUIDE = [
    "Mỗi dòng ở sheet 'Cau hoi' (từ dòng 2) là một câu hỏi một lựa chọn.",
    "Điền ít nhất 2 phương án, liên tục từ Phương án A; các cột không dùng để trống.",
    "Cột 'Đáp án đúng' ghi đúng một chữ A–F, trỏ tới phương án có nội dung.",
    f"Nội dung câu hỏi tối đa {MAX_CONTENT_LENGTH} ký tự, mỗi phương án tối đa {MAX_OPTION_LENGTH} ký tự.",
    f"Tối đa {MAX_ROWS} câu mỗi file, file không quá 2 MB. Không đổi tên hay thứ tự các cột ở dòng 1.",
    "Câu hợp lệ được thêm vào ngân hàng ở trạng thái Đang dùng; dòng lỗi được báo lại và không nhập.",
]


@dataclass
class ImportRow:
    row: int
    content: str
    options: list = field(default_factory=list)
    correct: int | None = None  # vị trí đáp án đúng trong options (0 = A)
    errors: list = field(default_factory=list)

    @property
    def valid(self):
        return not self.errors

    @property
    def correct_letter(self):
        return LETTERS[self.correct] if self.correct is not None else ""

    def as_dict(self):
        """Dạng gọn để giữ trong session giữa bước xem trước và bước xác nhận."""
        return {"row": self.row, "content": self.content, "options": self.options, "correct": self.correct}


def _text(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)  # ô số 2.0 -> "2"
    return str(value).strip()


def read_workbook(upload):
    """Đọc file tải lên, trả về danh sách ImportRow (cả dòng hợp lệ và dòng lỗi)."""
    if not upload.name.lower().endswith(".xlsx"):
        raise ValidationError("Chỉ nhận file Excel .xlsx (tải file mẫu để soạn).")
    if upload.size > MAX_FILE_BYTES:
        raise ValidationError("File quá lớn, tối đa 2 MB.")
    try:
        workbook = load_workbook(upload, read_only=True, data_only=True)
    except (BadZipFile, InvalidFileException, KeyError, OSError, ValueError):
        raise ValidationError("Không đọc được file. Hãy lưu lại đúng định dạng Excel .xlsx.")

    try:
        sheet = workbook.worksheets[0]
        rows = sheet.iter_rows(values_only=True)
        header = [_text(cell) for cell in (next(rows, None) or [])][: len(HEADERS)]
        if header != HEADERS:
            raise ValidationError("Dòng 1 phải đúng các cột của file mẫu: " + ", ".join(HEADERS) + ".")
        result = []
        for number, values in enumerate(rows, start=2):
            cells = [_text(cell) for cell in (values or [])][: len(HEADERS)]
            cells += [""] * (len(HEADERS) - len(cells))
            if not any(cells):
                continue  # bỏ dòng trống
            if len(result) >= MAX_ROWS:
                raise ValidationError(f"File có quá {MAX_ROWS} câu hỏi, hãy chia thành nhiều file.")
            result.append(_check_row(number, cells))
    finally:
        workbook.close()
    if not result:
        raise ValidationError("File chưa có câu hỏi nào (dòng 2 trở đi đang trống).")
    return result


def _check_row(number, cells):
    content, answer = cells[0], cells[-1].upper()
    raw_options = cells[1:-1]
    item = ImportRow(row=number, content=content)
    if not content:
        item.errors.append("Thiếu nội dung câu hỏi.")
    elif len(content) > MAX_CONTENT_LENGTH:
        item.errors.append(f"Nội dung quá {MAX_CONTENT_LENGTH} ký tự.")

    last_filled = max((i for i, text in enumerate(raw_options) if text), default=-1)
    if any(not text for text in raw_options[: last_filled + 1]):
        item.errors.append("Các phương án phải điền liên tục từ A, không bỏ trống ở giữa.")
    item.options = [text for text in raw_options if text]
    if len(item.options) < 2:
        item.errors.append("Cần ít nhất 2 phương án.")
    if any(len(text) > MAX_OPTION_LENGTH for text in item.options):
        item.errors.append(f"Có phương án quá {MAX_OPTION_LENGTH} ký tự.")
    if len({text.casefold() for text in item.options}) != len(item.options):
        item.errors.append("Có hai phương án trùng nhau.")

    if not answer:
        item.errors.append("Thiếu đáp án đúng.")
    elif len(answer) != 1 or answer not in LETTERS:
        item.errors.append("Đáp án đúng phải là một chữ từ A đến F.")
    elif LETTERS.index(answer) >= len(item.options):
        item.errors.append(f"Đáp án đúng {answer} trỏ tới phương án trống.")
    else:
        item.correct = LETTERS.index(answer)
    return item


def build_template():
    """File mẫu .xlsx (bytes): sheet 'Cau hoi' có dòng tiêu đề + 2 câu ví dụ, sheet 'Huong dan'."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Cau hoi"
    sheet.append(HEADERS)
    for row in SAMPLE_ROWS:
        sheet.append(row)
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="2465B1")
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    for column, width in zip("ABCDEFGH", (48, 26, 26, 26, 26, 20, 20, 13)):
        sheet.column_dimensions[column].width = width
    sheet.freeze_panes = "A2"
    guide = workbook.create_sheet("Huong dan")
    for line in GUIDE:
        guide.append([line])
    guide.column_dimensions["A"].width = 100
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
