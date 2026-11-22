"""S3-24: Xem kết quả thi theo quyền và điều kiện công bố (FR-13, BR-10, BR-19)."""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role
from attempts.models import Submission, SubmissionStatus
from config.tests.factories import correct_option, make_open_exam, make_question, make_user, wrong_option
from results.templatetags.results_extras import duration


class ResultViewsBase(TestCase):
    """Đề 3 câu x 2 điểm. Sinh viên A: đúng 1, sai 1, bỏ trống 1 -> 2,00/6,00 (định dạng số tiếng Việt)."""

    def setUp(self):
        self.teacher = make_user(Role.TEACHER, name="Giảng viên chính")
        self.other_teacher = make_user(Role.TEACHER)
        self.student = make_user(name="An Nguyễn")
        self.classmate = make_user(name="Bình Trần")
        self.questions = [
            make_question(self.teacher, content=f"Câu {i}", options=("DapAnDungXYZ", "Sai 1", "Sai 2"))
            for i in range(3)
        ]
        self.exam = make_open_exam(self.teacher, [self.student, self.classmate], self.questions)
        self.submission = self.answer_and_submit(self.student, right=[0], wrong=[1])

    def answer_and_submit(self, student, right=(), wrong=()):
        submission = student.start_exam(self.exam.pk)
        version = submission.version
        for index in right:
            question = self.questions[index]
            version = submission.save_answer(question.pk, correct_option(question).pk, version)
        for index in wrong:
            question = self.questions[index]
            version = submission.save_answer(question.pk, wrong_option(question).pk, version)
        submission.submit()
        submission.refresh_from_db()
        return submission

    def close_and_publish(self):
        self.exam.close()
        self.exam.publish_results()
        self.exam.refresh_from_db()

    def mark_submitted_not_graded(self, student):
        """Bài đã nộp nhưng chưa chấm xong (ví dụ chấm lỗi, worker sẽ chấm lại)."""
        submission = student.start_exam(self.exam.pk)
        Submission.objects.filter(pk=submission.pk).update(
            status=SubmissionStatus.SUBMITTED, submitted_at=timezone.now()
        )
        return submission


class TeacherResultTests(ResultViewsBase):
    def test_teacher_xem_danh_sach_de_minh_phu_trach(self):
        self.client.force_login(self.teacher)
        response = self.client.get(reverse("results:teacher_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.exam.title)
        exam = response.context["exams"][0]
        self.assertEqual((exam.participant_total, exam.graded_total, exam.grading_total), (2, 1, 0))

    def test_teacher_khac_khong_thay_de_khong_phu_trach(self):
        self.client.force_login(self.other_teacher)
        response = self.client.get(reverse("results:teacher_list"))

        self.assertEqual(len(response.context["exams"]), 0)
        self.assertContains(response, "Bạn chưa có đề thi nào đã phát hành.")

    def test_teacher_xem_chi_tiet_truoc_khi_cong_bo(self):
        self.client.force_login(self.teacher)
        response = self.client.get(reverse("results:teacher_exam", args=[self.exam.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2,00 / 6,00")
        self.assertContains(response, "Sinh viên chưa xem được điểm (chưa công bố)")
        row = next(r for r in response.context["rows"] if r["student"].pk == self.student.pk)
        self.assertEqual((row["result"].correct_count, row["result"].wrong_count, row["result"].blank_count),
                         (1, 1, 1))

    def test_teacher_thay_sinh_vien_chua_lam_bai(self):
        self.client.force_login(self.teacher)
        response = self.client.get(reverse("results:teacher_exam", args=[self.exam.pk]))

        row = next(r for r in response.context["rows"] if r["student"].pk == self.classmate.pk)
        self.assertEqual(row["state"], "not_started")
        self.assertContains(response, "Chưa làm bài")

    def test_bai_chua_cham_hien_dang_cham_khong_hien_diem_0(self):
        self.mark_submitted_not_graded(self.classmate)
        self.client.force_login(self.teacher)
        response = self.client.get(reverse("results:teacher_exam", args=[self.exam.pk]))

        row = next(r for r in response.context["rows"] if r["student"].pk == self.classmate.pk)
        self.assertEqual(row["state"], "grading")
        self.assertIsNone(row["result"])
        self.assertContains(response, "Đang chấm")
        self.assertNotContains(response, "0,00 / 6,00")

    def test_teacher_doi_id_sang_de_nguoi_khac_bi_403(self):
        self.client.force_login(self.other_teacher)
        response = self.client.get(reverse("results:teacher_exam", args=[self.exam.pk]))

        self.assertEqual(response.status_code, 403)

    def test_student_vao_trang_teacher_bi_403(self):
        self.client.force_login(self.student)

        self.assertEqual(self.client.get(reverse("results:teacher_list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("results:teacher_exam", args=[self.exam.pk])).status_code, 403)


class StudentResultTests(ResultViewsBase):
    def test_chua_cong_bo_khong_hien_diem(self):
        self.client.force_login(self.student)
        detail = self.client.get(reverse("results:student_detail", args=[self.exam.pk]))
        history = self.client.get(reverse("results:student_list"))

        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Kết quả chưa được công bố.")
        self.assertIsNone(detail.context["result"])
        self.assertNotContains(detail, "2,00")
        self.assertContains(history, "Kết quả chưa được công bố")
        self.assertNotContains(history, "2,00")

    def test_sau_cong_bo_xem_duoc_diem_va_so_cau(self):
        self.close_and_publish()
        self.client.force_login(self.student)
        response = self.client.get(reverse("results:student_detail", args=[self.exam.pk]))

        self.assertContains(response, "2,00 / 6,00")
        self.assertContains(response, "Đúng: <strong>1</strong> / 3", html=False)
        self.assertContains(response, "Sai: <strong>1</strong>", html=False)
        self.assertContains(response, "Bỏ trống: <strong>1</strong>", html=False)
        self.assertContains(self.client.get(reverse("results:student_list")), "2,00 / 6,00")

    def test_khong_lo_dap_an_dung(self):
        self.close_and_publish()
        self.client.force_login(self.student)
        response = self.client.get(reverse("results:student_detail", args=[self.exam.pk]))

        self.assertNotContains(response, "DapAnDungXYZ")

    def test_student_doi_id_sang_de_khong_co_bai_bi_403(self):
        other_exam = make_open_exam(self.teacher, [self.classmate], [make_question(self.teacher)])
        self.client.force_login(self.student)
        response = self.client.get(reverse("results:student_detail", args=[other_exam.pk]))

        self.assertEqual(response.status_code, 403)

    def test_chi_thay_bai_cua_minh(self):
        self.answer_and_submit(self.classmate, right=[0, 1, 2])
        self.close_and_publish()
        self.client.force_login(self.student)
        response = self.client.get(reverse("results:student_list"))

        self.assertEqual(len(response.context["rows"]), 1)
        self.assertContains(response, "2,00 / 6,00")
        self.assertNotContains(response, "6,00 / 6,00")

    def test_bai_da_nop_chua_cham_hien_dang_cham(self):
        self.mark_submitted_not_graded(self.classmate)
        self.client.force_login(self.classmate)
        response = self.client.get(reverse("results:student_detail", args=[self.exam.pk]))

        self.assertEqual(response.context["state"], "grading")
        self.assertContains(response, "Bài thi đang được chấm.")

    def test_bai_dang_lam_chuyen_ve_danh_sach_bai_thi(self):
        self.classmate.start_exam(self.exam.pk)
        self.client.force_login(self.classmate)
        response = self.client.get(reverse("results:student_detail", args=[self.exam.pk]))

        self.assertRedirects(response, reverse("attempts:exam_list"))

    def test_teacher_vao_trang_student_bi_403(self):
        self.client.force_login(self.teacher)

        self.assertEqual(self.client.get(reverse("results:student_list")).status_code, 403)

    def test_chua_dang_nhap_chuyen_ve_trang_dang_nhap(self):
        response = self.client.get(reverse("results:student_list"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])


class DurationFilterTests(TestCase):
    def test_dinh_dang_thoi_gian(self):
        self.assertEqual(duration(timedelta(minutes=12, seconds=5)), "12 phút 05 giây")
        self.assertEqual(duration(timedelta(hours=1, minutes=2, seconds=3)), "1 giờ 02 phút 03 giây")


class ResultPaginationTests(TestCase):
    """Bổ sung S3-24 (NFR-PER-05): các danh sách kết quả phân trang 20 dòng."""

    def setUp(self):
        self.teacher = make_user(Role.TEACHER)
        self.question = make_question(self.teacher)

    def test_teacher_danh_sach_de_phan_trang(self):
        for _ in range(22):
            make_open_exam(self.teacher, [], [self.question])
        self.client.force_login(self.teacher)
        first = self.client.get(reverse("results:teacher_list"))
        self.assertEqual(len(first.context["exams"]), 20)
        self.assertContains(first, "1/2")
        second = self.client.get(reverse("results:teacher_list"), {"page": 2})
        self.assertEqual(len(second.context["exams"]), 2)

    def test_ket_qua_mot_de_phan_trang_theo_ten_va_dung_trang_thai(self):
        students = [make_user(name=f"Sinh viên {i:02d}") for i in range(25)]
        exam = make_open_exam(self.teacher, students, [self.question])
        # Sinh viên 24 (trang 2) đã nộp bài; các bạn còn lại chưa làm.
        submission = students[24].start_exam(exam.pk)
        submission.submit()
        self.client.force_login(self.teacher)
        url = reverse("results:teacher_exam", args=[exam.pk])
        first = self.client.get(url)
        self.assertEqual([row["student"].full_name for row in first.context["rows"]][:2], ["Sinh viên 00", "Sinh viên 01"])
        self.assertEqual(len(first.context["rows"]), 20)
        second = self.client.get(url, {"page": 2})
        rows = second.context["rows"]
        self.assertEqual(len(rows), 5)
        last = rows[-1]
        self.assertEqual(last["student"], students[24])
        self.assertIsNotNone(last["result"])  # kết quả của trang 2 vẫn lấy đúng
        self.assertEqual(rows[0]["state"], "not_started")

    def test_sinh_vien_lich_su_phan_trang(self):
        student = make_user()
        for _ in range(21):
            exam = make_open_exam(self.teacher, [student], [self.question])
            student.start_exam(exam.pk).submit()
        self.client.force_login(student)
        first = self.client.get(reverse("results:student_list"))
        self.assertEqual(len(first.context["rows"]), 20)
        second = self.client.get(reverse("results:student_list"), {"page": 2})
        self.assertEqual(len(second.context["rows"]), 1)


class ScoreOnTenTests(ResultViewsBase):
    """Hiện thêm điểm quy đổi thang 10; điểm gốc trong database giữ nguyên."""

    def test_quy_doi_va_lam_tron(self):
        from decimal import Decimal

        from results.models import Result

        cases = [("2", "6", "3.33"), ("4", "6", "6.67"), ("6", "6", "10.00"), ("0", "6", "0.00"), ("7.5", "10", "7.50")]
        for score, max_score, expected in cases:
            with self.subTest(score=score, max_score=max_score):
                result = Result(score=Decimal(score), max_score=Decimal(max_score))
                self.assertEqual(result.score_on_10, Decimal(expected))
        self.assertEqual(Result(score=Decimal("0"), max_score=Decimal("0")).score_on_10, Decimal("0.00"))

    def test_teacher_va_student_thay_diem_thang_10_kem_diem_goc(self):
        self.client.force_login(self.teacher)
        response = self.client.get(reverse("results:teacher_exam", args=[self.exam.pk]))
        self.assertContains(response, "3,33 / 10")
        self.assertContains(response, "2,00 / 6,00")
        self.exam.close()
        self.exam.publish_results()
        self.client.force_login(self.student)
        detail = self.client.get(reverse("results:student_detail", args=[self.exam.pk]))
        self.assertContains(detail, "3,33 / 10")
        self.assertContains(detail, "Điểm gốc: 2,00 / 6,00")
        self.assertContains(self.client.get(reverse("results:student_list")), "3,33 / 10")

    def test_chua_cong_bo_khong_lo_diem_thang_10(self):
        self.client.force_login(self.student)
        self.assertNotContains(self.client.get(reverse("results:student_detail", args=[self.exam.pk])), "3,33")
        self.assertNotContains(self.client.get(reverse("results:student_list")), "3,33")
