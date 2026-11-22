"""S3-32: nhập câu hỏi từ file Excel.

Chạy riêng: cd src && python manage.py test questions.tests.test_import
"""
from decimal import Decimal
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from openpyxl import Workbook, load_workbook

from accounts.models import Role
from config.tests.factories import make_open_exam, make_question, make_user
from questions import importer
from questions.models import Question, QuestionStatus

GOOD = ["Thủ đô Việt Nam?", "Hà Nội", "Huế", "Đà Nẵng", "", "", "", "A"]


def make_xlsx(rows, header=importer.HEADERS, name="cau-hoi.xlsx"):
    workbook = Workbook()
    sheet = workbook.active
    if header is not None:
        sheet.append(header)
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return SimpleUploadedFile(name, buffer.getvalue())


class ReadWorkbookTests(TestCase):
    def test_dong_hop_le(self):
        [row] = importer.read_workbook(make_xlsx([GOOD]))
        self.assertTrue(row.valid)
        self.assertEqual(row.options, ["Hà Nội", "Huế", "Đà Nẵng"])
        self.assertEqual(row.correct, 0)

    def test_dap_an_chu_thuong_va_o_so(self):
        [row] = importer.read_workbook(make_xlsx([["1 + 1 = ?", 1, 2, 3, None, None, None, "b"]]))
        self.assertTrue(row.valid)
        self.assertEqual(row.options, ["1", "2", "3"])
        self.assertEqual(row.correct_letter, "B")

    def test_cac_loi_tung_dong(self):
        cases = {
            "Thiếu nội dung câu hỏi.": ["", "A", "B", "", "", "", "", "A"],
            "Cần ít nhất 2 phương án.": ["Câu?", "Chỉ một", "", "", "", "", "", "A"],
            "Thiếu đáp án đúng.": ["Câu?", "X", "Y", "", "", "", "", ""],
            "Đáp án đúng phải là một chữ từ A đến F.": ["Câu?", "X", "Y", "", "", "", "", "G"],
            "Đáp án đúng C trỏ tới phương án trống.": ["Câu?", "X", "Y", "", "", "", "", "C"],
            "Các phương án phải điền liên tục từ A, không bỏ trống ở giữa.": ["Câu?", "X", "", "Z", "", "", "", "A"],
            "Có hai phương án trùng nhau.": ["Câu?", "Có", "có", "", "", "", "", "A"],
        }
        for message, values in cases.items():
            with self.subTest(message=message):
                [row] = importer.read_workbook(make_xlsx([values]))
                self.assertIn(message, row.errors)

    def test_bo_qua_dong_trong(self):
        rows = importer.read_workbook(make_xlsx([GOOD, [None] * 8, GOOD]))
        self.assertEqual([r.row for r in rows], [2, 4])

    def test_sai_cot_tieu_de(self):
        with self.assertRaisesMessage(ValidationError, "Dòng 1 phải đúng các cột của file mẫu"):
            importer.read_workbook(make_xlsx([GOOD], header=["Câu hỏi", "A", "B"]))

    def test_khong_phai_xlsx(self):
        with self.assertRaisesMessage(ValidationError, "Chỉ nhận file Excel .xlsx"):
            importer.read_workbook(SimpleUploadedFile("cau-hoi.csv", b"a,b"))

    def test_file_hong(self):
        with self.assertRaisesMessage(ValidationError, "Không đọc được file"):
            importer.read_workbook(SimpleUploadedFile("cau-hoi.xlsx", b"khong phai excel"))

    def test_file_trong(self):
        with self.assertRaisesMessage(ValidationError, "File chưa có câu hỏi nào"):
            importer.read_workbook(make_xlsx([]))

    def test_qua_so_dong(self):
        with self.assertRaisesMessage(ValidationError, "quá 500 câu hỏi"):
            importer.read_workbook(make_xlsx([GOOD] * 501))

    def test_file_qua_lon(self):
        upload = make_xlsx([GOOD])
        upload.size = importer.MAX_FILE_BYTES + 1
        with self.assertRaisesMessage(ValidationError, "File quá lớn"):
            importer.read_workbook(upload)

    def test_file_mau_doc_lai_duoc(self):
        rows = importer.read_workbook(SimpleUploadedFile("mau.xlsx", importer.build_template()))
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r.valid for r in rows))


class ImportViewTests(TestCase):
    def setUp(self):
        self.teacher = make_user(Role.TEACHER)
        self.client.force_login(self.teacher)
        self.url = reverse("questions:import")

    def preview(self, rows, url=None):
        return self.client.post(url or self.url, {"step": "preview", "file": make_xlsx(rows)})

    def test_tai_file_mau(self):
        response = self.client.get(reverse("questions:import_template"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
        sheet = load_workbook(BytesIO(response.content)).active
        self.assertEqual([c.value for c in sheet[1]], importer.HEADERS)

    def test_xem_truoc_chua_tao_cau_nao(self):
        bad = ["", "A", "B", "", "", "", "", "A"]
        response = self.preview([GOOD, bad])
        self.assertContains(response, "1 câu hợp lệ")
        self.assertContains(response, "1 dòng lỗi")
        self.assertContains(response, "Thiếu nội dung câu hỏi.")
        self.assertEqual(Question.objects.count(), 0)

    def test_xac_nhan_tao_cau_active_cua_minh(self):
        self.preview([GOOD, ["", "A", "B", "", "", "", "", "A"]])
        response = self.client.post(self.url, {"step": "confirm"}, follow=True)
        self.assertRedirects(response, reverse("questions:list"))
        self.assertContains(response, "Đã nhập 1 câu hỏi vào ngân hàng.")
        question = Question.objects.get()
        self.assertEqual((question.teacher_id, question.status), (self.teacher.pk, QuestionStatus.ACTIVE))
        self.assertEqual(list(question.options.order_by("display_order").values_list("content", "is_correct")),
                         [("Hà Nội", True), ("Huế", False), ("Đà Nẵng", False)])

    def test_xac_nhan_hai_lan_khong_tao_trung(self):
        self.preview([GOOD])
        self.client.post(self.url, {"step": "confirm"})
        response = self.client.post(self.url, {"step": "confirm"}, follow=True)
        self.assertContains(response, "Phiên nhập đã hết")
        self.assertEqual(Question.objects.count(), 1)

    def test_nhap_va_them_vao_de_nhap(self):
        exam = self.teacher.create_exam({"title": "Đề nháp"})
        url = f"{self.url}?exam={exam.pk}"
        self.preview([GOOD, GOOD], url=url)
        response = self.client.post(url, {"step": "confirm", "exam": exam.pk, "add_to_exam": "1", "points": "2,5"})
        self.assertRedirects(response, reverse("exams:questions", args=[exam.pk]))
        self.assertEqual(exam.exam_questions.count(), 2)
        self.assertEqual({i.points for i in exam.exam_questions.all()}, {Decimal("2.5")})

    def test_diem_sai_thi_khong_tao_gi(self):
        exam = self.teacher.create_exam({"title": "Đề nháp"})
        url = f"{self.url}?exam={exam.pk}"
        self.preview([GOOD], url=url)
        response = self.client.post(url, {"step": "confirm", "exam": exam.pk, "add_to_exam": "1", "points": "0"})
        self.assertContains(response, "alert-danger")
        self.assertEqual(Question.objects.count(), 0)
        self.assertEqual(exam.exam_questions.count(), 0)

    def test_de_da_phat_hanh_khong_nhan_cau_moi(self):
        exam = make_open_exam(self.teacher, [], [make_question(self.teacher)])
        url = f"{self.url}?exam={exam.pk}"
        self.preview([GOOD], url=url)
        self.client.post(url, {"step": "confirm", "exam": exam.pk, "add_to_exam": "1", "points": "1"})
        self.assertEqual(exam.exam_questions.count(), 1)
        self.assertEqual(Question.objects.filter(content=GOOD[0]).count(), 1)  # vẫn vào ngân hàng

    def test_de_cua_giang_vien_khac_bi_chan(self):
        exam = make_user(Role.TEACHER).create_exam({"title": "Đề người khác"})
        self.assertEqual(self.client.get(f"{self.url}?exam={exam.pk}").status_code, 403)

    def test_file_loi_hien_thong_bao(self):
        response = self.client.post(self.url, {"step": "preview", "file": SimpleUploadedFile("a.csv", b"x")})
        self.assertContains(response, "Chỉ nhận file Excel .xlsx")

    def test_sai_vai_tro_bi_chan(self):
        for role in (Role.STUDENT, Role.ADMIN):
            with self.subTest(role=role):
                self.client.force_login(make_user(role))
                self.assertEqual(self.client.get(self.url).status_code, 403)
                self.assertEqual(self.client.get(reverse("questions:import_template")).status_code, 403)
