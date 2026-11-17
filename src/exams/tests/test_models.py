"""Test lớp Exam, ExamQuestion, ExamParticipant (UC Create Exam, Manage Exams, FR-06, FR-07).

Chạy riêng: cd src && python manage.py test exams
"""
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.models import Role
from config.tests.factories import correct_option, make_open_exam, make_question, make_user
from exams.models import ExamParticipant, ExamStatus


class CreateExamTests(TestCase):
    def setUp(self):
        self.teacher = make_user(Role.TEACHER)

    def test_tao_de_moi_o_trang_thai_nhap(self):
        exam = self.teacher.create_exam({"title": "  Giữa kỳ  "})
        exam.refresh_from_db()
        self.assertEqual(exam.title, "Giữa kỳ")
        self.assertEqual(exam.status, ExamStatus.DRAFT)

    def test_lich_thi_sai_thi_khong_tao(self):
        now = timezone.now()
        with self.assertRaises(ValidationError) as ctx:
            self.teacher.create_exam({
                "title": "", "duration_minutes": 0, "opens_at": now, "closes_at": now - timedelta(hours=1),
            })
        self.assertEqual(set(ctx.exception.message_dict), {"title", "duration_minutes", "closes_at"})

    def test_them_cau_hoi_danh_vi_tri_lien_tiep(self):
        exam = self.teacher.create_exam({"title": "Đề"})
        first = exam.add_question(make_question(self.teacher).pk, 2)
        second = exam.add_question(make_question(self.teacher).pk, "1.5")
        self.assertEqual((first.position, second.position), (1, 2))

    def test_khong_them_cau_trung_hoac_diem_khong_hop_le(self):
        exam = self.teacher.create_exam({"title": "Đề"})
        question = make_question(self.teacher)
        exam.add_question(question.pk, 2)
        with self.assertRaisesMessage(ValidationError, "đã có trong đề"):
            exam.add_question(question.pk, 2)
        for bad in (0, -1, "abc", "NaN"):
            with self.subTest(points=bad), self.assertRaises(ValidationError):
                exam.add_question(make_question(self.teacher).pk, bad)

    def test_khong_dung_cau_hoi_cua_giang_vien_khac(self):
        exam = self.teacher.create_exam({"title": "Đề"})
        other_question = make_question(make_user(Role.TEACHER))
        with self.assertRaisesMessage(ValidationError, "không thuộc ngân hàng của bạn"):
            exam.add_question(other_question.pk, 2)

    def test_doi_vi_tri_hai_cau(self):
        exam = self.teacher.create_exam({"title": "Đề"})
        first = exam.add_question(make_question(self.teacher).pk, 2)
        second = exam.add_question(make_question(self.teacher).pk, 2)
        second.set_position(1)
        first.refresh_from_db()
        self.assertEqual((first.position, second.position), (2, 1))


class PublishExamTests(TestCase):
    """BR-17: điều kiện phát hành; BR-14: đề đã phát hành không sửa được."""

    def setUp(self):
        self.teacher = make_user(Role.TEACHER)

    def test_de_rong_khong_phat_hanh_duoc(self):
        exam = self.teacher.create_exam({"title": "Đề rỗng"})
        with self.assertRaisesMessage(ValidationError, "ít nhất 1 câu hỏi"):
            exam.publish()

    def test_cau_nhap_khong_phat_hanh_duoc(self):
        exam = self.teacher.create_exam({"title": "Đề"})
        exam.add_question(make_question(self.teacher, activate=False).pk, 2)
        with self.assertRaisesMessage(ValidationError, "Câu 1 chưa sẵn sàng"):
            exam.publish()

    def test_de_da_phat_hanh_khong_sua_duoc(self):
        exam = make_open_exam(self.teacher, [], [make_question(self.teacher)])
        self.assertEqual(exam.status, ExamStatus.PUBLISHED)
        with self.assertRaisesMessage(ValidationError, "Đề đã phát hành"):
            exam.add_question(make_question(self.teacher).pk, 2)
        with self.assertRaisesMessage(ValidationError, "Đề đã phát hành"):
            exam.exam_questions.first().set_points(5)


class ParticipantTests(TestCase):
    """BR-18: cấp và thu hồi quyền dự thi."""

    def setUp(self):
        self.teacher = make_user(Role.TEACHER)
        self.student = make_user()
        self.exam = make_open_exam(self.teacher, [self.student], [make_question(self.teacher)])

    def test_sinh_vien_duoc_giao_thi_lam_duoc(self):
        self.assertTrue(self.exam.can_start(self.student))
        self.assertFalse(self.exam.can_start(make_user()))  # không được giao

    def test_thu_hoi_quyen_giu_lich_su_va_nop_bai_dang_lam(self):
        submission = self.student.start_exam(self.exam.pk)
        participant = ExamParticipant.objects.get(exam=self.exam, student=self.student)
        participant.revoke_access()
        participant.refresh_from_db()
        submission.refresh_from_db()
        self.assertFalse(participant.is_active)  # bản ghi vẫn còn
        self.assertNotEqual(submission.status, "IN_PROGRESS")

    def test_cap_lai_quyen_sau_khi_thu_hoi(self):
        participant = ExamParticipant.objects.get(exam=self.exam, student=self.student)
        participant.revoke_access()
        self.teacher.assign_students(self.exam.pk, [self.student.pk])
        self.assertTrue(ExamParticipant.objects.get(exam=self.exam, student=self.student).can_participate())


class PublishResultsTests(TestCase):
    """BR-19: chỉ công bố khi đề đã đóng và mọi bài đã chấm."""

    def setUp(self):
        self.teacher = make_user(Role.TEACHER)
        self.student = make_user()
        self.question = make_question(self.teacher)
        self.exam = make_open_exam(self.teacher, [self.student], [self.question])

    def test_chua_dong_de_thi_chua_cong_bo(self):
        with self.assertRaisesMessage(ValidationError, "sau khi đã đóng đề"):
            self.exam.publish_results()

    def test_dong_de_thi_nop_bai_dang_lam_roi_cong_bo_duoc(self):
        submission = self.student.start_exam(self.exam.pk)
        submission.save_answer(self.question.pk, correct_option(self.question).pk, submission.version)
        self.exam.close()
        submission.refresh_from_db()
        self.assertEqual(submission.status, "GRADED")
        self.exam.publish_results()
        self.exam.refresh_from_db()
        self.assertTrue(self.exam.results_published)
