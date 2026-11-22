"""Form thông tin đề thi (S3-11, UC Create Exam bước 2).

Form chỉ đổi chữ người dùng gõ thành dữ liệu (số, ngày giờ). Quy tắc nghiệp vụ (tên bắt buộc,
thời lượng > 0, giờ đóng sau giờ mở) nằm ở Exam.apply_settings, view gọi Model rồi gắn lỗi về đúng ô.
"""
from django import forms

DATETIME_INPUT = "%Y-%m-%dT%H:%M"  # định dạng của ô <input type="datetime-local">
MAX_DURATION = 1440  # 24 giờ; chặn số quá lớn làm tràn cột integer


class ExamForm(forms.Form):
    title = forms.CharField(
        label="Tên đề thi",
        max_length=200,
        required=False,  # bỏ trống thì Model báo "Vui lòng nhập tên đề thi."
        widget=forms.TextInput(attrs={"maxlength": 200}),
        error_messages={"max_length": "Tên đề thi tối đa 200 ký tự."},
    )
    description = forms.CharField(label="Mô tả", required=False, widget=forms.Textarea(attrs={"rows": 3}))
    duration_minutes = forms.IntegerField(
        label="Thời lượng (phút)",
        max_value=MAX_DURATION,
        widget=forms.NumberInput(attrs={"min": 1, "step": 1}),
        error_messages={
            "required": "Vui lòng nhập thời lượng làm bài.",
            "invalid": "Thời lượng phải là số nguyên.",
            "max_value": f"Thời lượng tối đa {MAX_DURATION} phút (24 giờ).",
        },
    )
    opens_at = forms.DateTimeField(
        label="Thời gian mở",
        required=False,
        input_formats=[DATETIME_INPUT],
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format=DATETIME_INPUT),
        error_messages={"invalid": "Thời gian mở không đúng định dạng."},
    )
    closes_at = forms.DateTimeField(
        label="Thời gian đóng",
        required=False,
        input_formats=[DATETIME_INPUT],
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format=DATETIME_INPUT),
        error_messages={"invalid": "Thời gian đóng không đúng định dạng."},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_description(self):
        return self.cleaned_data["description"].strip() or None

    @classmethod
    def initial_from(cls, exam):
        """Giá trị ban đầu khi sửa đề. Giờ lưu UTC, ô nhập hiện giờ Việt Nam (TIME_ZONE)."""
        return {
            "title": exam.title,
            "description": exam.description or "",
            "duration_minutes": exam.duration_minutes,
            "opens_at": exam.opens_at,
            "closes_at": exam.closes_at,
        }
