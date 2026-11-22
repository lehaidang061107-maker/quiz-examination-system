"""S3-14: Đóng đề, lưu trữ và công bố điểm (FR-07, FR-13, BR-17, BR-19).

Chạy riêng: cd src && python manage.py test exams.tests.test_views_close
"""
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role
from attempts.models import Submission, SubmissionStatus
from config.tests.factories import correct_option, make_open_exam, make_question, make_user
from exams.models import ExamStatus


class CloseBase(TestCase):
    def setUp(self):
        self.teacher = make_user(Role.TEACHER)
        self.an = make_user(name="An Nguyễn")
        self.binh = make_user(name="Bình Trần")
        self.question = make_question(self.teacher)
        self.exam = make_open_exam(self.teacher, [self.an, self.binh], [self.question])
        self.client.force_login(self.teacher)
        self.detail = reverse("exams:detail", args=[self.exam.pk])
        self.close_url = reverse("exams:close", args=[self.exam.pk])
        self.publish_url = reverse("exams:publish_results", args=[self.exam.pk])
        self.archive_url = reverse("exams:archive", args=[self.exam.pk])

    def submit(self, student):
        submission = student.start_exam(self.exam.pk)
        submission.save_answer(self.question.pk, correct_option(self.question).pk, submission.version)
        submission.submit()
        submission.refresh_from_db()
        return submission

    def reload(self):
        self.exam.refresh_from_db()
        return self.exam


class CloseTests(CloseBase):
    def test_hien_so_bai_dang_lam_cho_cham_da_cham(self):
        self.submit(self.an)
        self.binh.start_exam(self.exam.pk)
        response = self.client.get(self.detail)
        self.assertEqual(response.context["counts"], {"in_progress": 1, "submitted": 0, "graded": 1})
        self.assertContains(response, "Đóng đề")

    def test_dong_de_tu_nop_bai_dang_lam(self):
        submission = self.binh.start_exam(self.exam.pk)
        with self.assertLogs("exams.audit", "INFO") as logs:
            response = self.client.post(self.close_url, follow=True)
        self.assertContains(response, "Đã đóng đề thi. 1 bài đang làm đã được nộp bằng đáp án đã lưu.")
        self.assertEqual(self.reload().status, ExamStatus.CLOSED)
        submission.refresh_from_db()
        self.assertNotEqual(submission.status, SubmissionStatus.IN_PROGRESS)
        # Truy vết: ghi người thực hiện và đề.
        self.assertIn("đóng đề", logs.output[0])
        self.assertIn(f"user_id={self.teacher.pk}", logs.output[0])
        self.assertIn(f"exam_id={self.exam.pk}", logs.output[0])

    def test_de_dong_khong_mo_lai_va_khong_sua(self):
        self.client.post(self.close_url)
        response = self.client.post(self.close_url, follow=True)
        self.assertContains(response, "Chỉ đóng được đề đang phát hành.")
        response = self.client.post(reverse("exams:publish", args=[self.exam.pk]), follow=True)
        self.assertContains(response, "Đề đã phát hành, không thể sửa nội dung.")
        self.assertEqual(self.reload().status, ExamStatus.CLOSED)
        # Sinh viên không bắt đầu được đề đã đóng.
        self.assertEqual(self.exam.cannot_start_reason(self.an), "Đề thi chưa mở hoặc đã đóng.")

    def test_de_nhap_khong_dong_duoc(self):
        draft = self.teacher.create_exam({"title": "Nháp", "duration_minutes": 10})
        response = self.client.post(reverse("exams:close", args=[draft.pk]), follow=True)
        self.assertContains(response, "Chỉ đóng được đề đang phát hành.")

    def test_chi_nhan_post_va_dung_chu_de(self):
        self.assertEqual(self.client.get(self.close_url).status_code, 405)
        for user in (make_user(Role.TEACHER), self.an):
            with self.subTest(role=user.role):
                self.client.force_login(user)
                self.assertEqual(self.client.post(self.close_url).status_code, 403)
                self.assertEqual(self.client.post(self.publish_url).status_code, 403)
                self.assertEqual(self.client.post(self.archive_url).status_code, 403)
        self.assertEqual(self.reload().status, ExamStatus.PUBLISHED)


class PublishResultTests(CloseBase):
    def test_chua_dong_thi_khong_cong_bo(self):
        self.submit(self.an)
        response = self.client.post(self.publish_url, follow=True)
        self.assertContains(response, "Chỉ công bố điểm sau khi đã đóng đề.")
        self.assertFalse(self.reload().results_published)

    def test_con_bai_chua_cham_thi_khong_cong_bo(self):
        submission = self.an.start_exam(self.exam.pk)
        self.client.post(self.close_url)
        # Giả lập chấm lỗi: bài vẫn ở SUBMITTED chờ worker chấm lại.
        Submission.objects.filter(pk=submission.pk).update(status=SubmissionStatus.SUBMITTED, submitted_at=timezone.now())
        submission.results.all().delete()
        response = self.client.post(self.publish_url, follow=True)
        self.assertContains(response, "Còn 1 bài chưa chấm xong, chưa thể công bố.")
        self.assertContains(response, "Còn 1 bài chưa chấm xong.")
        self.assertFalse(self.reload().results_published)

    def test_cong_bo_thanh_cong_sinh_vien_xem_duoc_diem(self):
        self.submit(self.an)
        self.client.post(self.close_url)
        # Trước khi công bố: sinh viên chưa xem được điểm.
        self.assertIsNone(self.an.view_result(self.exam.pk))
        with self.assertLogs("exams.audit", "INFO") as logs:
            response = self.client.post(self.publish_url, follow=True)
        self.assertContains(response, "Đã công bố điểm. Sinh viên đã xem được kết quả của mình.")
        self.assertIn("công bố điểm", logs.output[0])
        self.assertTrue(self.reload().results_published)
        self.assertIsNotNone(self.an.view_result(self.exam.pk))
        # Đã công bố thì không còn nút công bố.
        self.assertNotContains(response, self.publish_url)

    def test_cong_bo_lan_hai(self):
        self.client.post(self.close_url)
        self.client.post(self.publish_url)
        response = self.client.post(self.publish_url, follow=True)
        self.assertContains(response, "Điểm của đề này đã được công bố trước đó.")


class ArchiveTests(CloseBase):
    def test_luu_tru_sau_khi_dong_va_giu_diem_da_cong_bo(self):
        self.submit(self.an)
        self.client.post(self.close_url)
        self.client.post(self.publish_url)
        with self.assertLogs("exams.audit", "INFO"):
            response = self.client.post(self.archive_url, follow=True)
        self.assertContains(response, "Đã lưu trữ đề thi.")
        self.assertEqual(self.reload().status, ExamStatus.ARCHIVED)
        self.assertIsNotNone(self.an.view_result(self.exam.pk))  # BR-19: lưu trữ không mất quyền xem
        self.assertNotContains(response, self.close_url)

    def test_chua_dong_khong_luu_tru(self):
        response = self.client.post(self.archive_url, follow=True)
        self.assertContains(response, "Chỉ lưu trữ được đề đã đóng.")
        self.assertEqual(self.reload().status, ExamStatus.PUBLISHED)

    def test_con_bai_cho_cham_khong_luu_tru(self):
        submission = self.an.start_exam(self.exam.pk)
        self.client.post(self.close_url)
        Submission.objects.filter(pk=submission.pk).update(status=SubmissionStatus.SUBMITTED, submitted_at=timezone.now())
        submission.results.all().delete()
        response = self.client.post(self.archive_url, follow=True)
        self.assertContains(response, "Còn 1 bài chưa chấm xong, chưa thể lưu trữ.")
        self.assertEqual(self.reload().status, ExamStatus.CLOSED)
