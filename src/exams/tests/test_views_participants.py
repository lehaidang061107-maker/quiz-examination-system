"""S3-13: Cấp và thu hồi quyền dự thi (FR-06, FR-07, BR-18).

Chạy riêng: cd src && python manage.py test exams.tests.test_views_participants
"""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role, User, UserStatus
from attempts.models import SubmissionStatus
from config.tests.factories import make_open_exam, make_question, make_user
from exams.models import Exam, ExamParticipant


class ParticipantBase(TestCase):
    def setUp(self):
        self.teacher = make_user(Role.TEACHER)
        self.an = make_user(name="An Nguyễn")
        self.binh = make_user(name="Bình Trần")
        self.exam = self.teacher.create_exam({"title": "Đề nháp", "duration_minutes": 30})
        self.client.force_login(self.teacher)
        self.url = reverse("exams:participants", args=[self.exam.pk])

    def active_ids(self, exam=None):
        exam = exam or self.exam
        return set(ExamParticipant.objects.filter(exam=exam, is_active=True).values_list("student_id", flat=True))


class GrantTests(ParticipantBase):
    def test_hien_sinh_vien_active_va_trang_thai(self):
        locked = make_user(name="Cường Khóa")
        User.objects.filter(pk=locked.pk).update(status=UserStatus.LOCKED)
        self.teacher.assign_students(self.exam.pk, [self.an.pk])
        response = self.client.get(self.url)
        names = [row["student"].full_name for row in response.context["rows"]]
        self.assertEqual(names, ["An Nguyễn", "Bình Trần"])  # sinh viên bị khóa chưa từng giao thì không hiện
        self.assertContains(response, "Đã cấp quyền")
        self.assertContains(response, "Chưa cấp")

    def test_tim_sinh_vien(self):
        response = self.client.get(self.url, {"q": "bình"})
        self.assertEqual([row["student"].pk for row in response.context["rows"]], [self.binh.pk])

    def test_cap_quyen_nhieu_sinh_vien(self):
        response = self.client.post(self.url, {"action": "grant", "student_ids": [self.an.pk, self.binh.pk]}, follow=True)
        self.assertContains(response, "Đã cấp quyền dự thi cho 2 sinh viên.")
        self.assertEqual(self.active_ids(), {self.an.pk, self.binh.pk})

    def test_khong_tao_phan_cong_trung(self):
        self.teacher.assign_students(self.exam.pk, [self.an.pk])
        response = self.client.post(self.url, {"action": "grant", "student_ids": [self.an.pk, self.binh.pk]}, follow=True)
        self.assertContains(response, "Đã cấp quyền dự thi cho 1 sinh viên.")
        self.assertEqual(ExamParticipant.objects.filter(exam=self.exam).count(), 2)
        response = self.client.post(self.url, {"action": "grant", "student_ids": [self.an.pk]}, follow=True)
        self.assertContains(response, "Các sinh viên đã chọn đều đã được cấp quyền.")

    def test_khong_chon_ai(self):
        response = self.client.post(self.url, {"action": "grant"}, follow=True)
        self.assertContains(response, "Vui lòng chọn ít nhất 1 sinh viên.")

    def test_khong_cap_cho_giang_vien_hoac_id_la(self):
        for bad in (self.teacher.pk, 999999, "abc"):
            with self.subTest(bad=bad):
                response = self.client.post(self.url, {"action": "grant", "student_ids": [self.an.pk, bad]}, follow=True)
                self.assertContains(response, "Có sinh viên không hợp lệ trong danh sách đã chọn.")
        self.assertEqual(self.active_ids(), set())

    def test_khong_cap_cho_sinh_vien_bi_khoa(self):
        User.objects.filter(pk=self.binh.pk).update(status=UserStatus.LOCKED)
        response = self.client.post(self.url, {"action": "grant", "student_ids": [self.an.pk, self.binh.pk]}, follow=True)
        self.assertContains(response, "Bình Trần không phải sinh viên đang hoạt động.")
        self.assertEqual(self.active_ids(), set())  # lỗi thì không cấp cho ai

    def test_sinh_vien_duoc_cap_quyen_thay_de_sau_khi_phat_hanh(self):
        self.client.post(self.url, {"action": "grant", "student_ids": [self.an.pk]})
        self.exam.add_question(make_question(self.teacher).pk, 1)
        self.exam.publish()
        self.assertIn(self.exam, self.an.view_available_exams())
        self.assertNotIn(self.exam, self.binh.view_available_exams())
        self.assertIsNone(self.exam.cannot_start_reason(self.an))
        self.assertEqual(self.exam.cannot_start_reason(self.binh), "Bạn không được giao đề thi này.")

    def test_de_het_lich_khong_cap_them(self):
        Exam.objects.filter(pk=self.exam.pk).update(closes_at=timezone.now() - timedelta(minutes=1))
        response = self.client.get(self.url)
        self.assertContains(response, "Đề đã đóng hoặc đã hết lịch thi")
        self.assertNotContains(response, 'value="grant"')
        response = self.client.post(self.url, {"action": "grant", "student_ids": [self.an.pk]}, follow=True)
        self.assertContains(response, "Đề đã hết lịch thi, không thể cấp quyền mới.")
        self.assertEqual(self.active_ids(), set())

    def test_sai_quyen(self):
        for user in (make_user(Role.TEACHER), make_user(Role.STUDENT), make_user(Role.ADMIN)):
            with self.subTest(role=user.role):
                self.client.force_login(user)
                self.assertEqual(self.client.get(self.url).status_code, 403)
                response = self.client.post(self.url, {"action": "grant", "student_ids": [self.an.pk]})
                self.assertEqual(response.status_code, 403)
        self.assertEqual(self.active_ids(), set())


class RevokeTests(ParticipantBase):
    def setUp(self):
        super().setUp()
        self.question = make_question(self.teacher)
        self.open_exam = make_open_exam(self.teacher, [self.an, self.binh], [self.question])
        self.open_url = reverse("exams:participants", args=[self.open_exam.pk])

    def test_thu_hoi_giu_lich_su(self):
        response = self.client.post(self.open_url, {"action": f"revoke:{self.an.pk}"}, follow=True)
        self.assertContains(response, "Đã thu hồi quyền của An Nguyễn.")
        self.assertContains(response, "Đã thu hồi")
        record = ExamParticipant.objects.get(exam=self.open_exam, student=self.an)
        self.assertFalse(record.is_active)  # vẫn còn bản ghi, chỉ tắt quyền
        self.assertEqual(self.open_exam.cannot_start_reason(self.an), "Bạn không được giao đề thi này.")

    def test_thu_hoi_khi_dang_lam_thi_chot_bai(self):
        submission = self.an.start_exam(self.open_exam.pk)
        response = self.client.post(self.open_url, {"action": f"revoke:{self.an.pk}"}, follow=True)
        self.assertContains(
            response, "Đã thu hồi quyền của An Nguyễn. Bài đang làm đã được chốt và nộp bằng đáp án đã lưu."
        )
        submission.refresh_from_db()
        self.assertNotEqual(submission.status, SubmissionStatus.IN_PROGRESS)
        self.assertIsNotNone(submission.submitted_at)

    def test_cap_lai_sau_khi_thu_hoi(self):
        self.client.post(self.open_url, {"action": f"revoke:{self.an.pk}"})
        response = self.client.post(self.open_url, {"action": "grant", "student_ids": [self.an.pk]}, follow=True)
        self.assertContains(response, "Đã cấp quyền dự thi cho 1 sinh viên.")
        self.assertIn(self.an.pk, self.active_ids(self.open_exam))

    def test_thu_hoi_hai_lan_hoac_chua_cap(self):
        self.client.post(self.open_url, {"action": f"revoke:{self.an.pk}"})
        response = self.client.post(self.open_url, {"action": f"revoke:{self.an.pk}"}, follow=True)
        self.assertContains(response, "Sinh viên đã bị thu hồi quyền trước đó.")
        other = make_user()
        response = self.client.post(self.open_url, {"action": f"revoke:{other.pk}"}, follow=True)
        self.assertContains(response, "Sinh viên chưa được cấp quyền cho đề này.")

    def test_de_da_dong_khong_thu_hoi(self):
        self.open_exam.close()
        response = self.client.post(self.open_url, {"action": f"revoke:{self.an.pk}"}, follow=True)
        self.assertContains(response, "Đề đã đóng, không thể thu hồi quyền.")
        self.assertIn(self.an.pk, self.active_ids(self.open_exam))
        self.assertContains(response, "chỉ để xem lịch sử")

    def test_giang_vien_khac_khong_thu_hoi_duoc(self):
        self.client.force_login(make_user(Role.TEACHER))
        self.assertEqual(self.client.post(self.open_url, {"action": f"revoke:{self.an.pk}"}).status_code, 403)
        self.assertIn(self.an.pk, self.active_ids(self.open_exam))

    def test_thao_tac_la(self):
        response = self.client.post(self.open_url, {"action": "xoa"}, follow=True)
        self.assertContains(response, "Thao tác không hợp lệ.")
