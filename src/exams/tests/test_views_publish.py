"""S3-12: Chọn câu hỏi và phát hành đề (FR-06, FR-07, BR-14, BR-17).

Chạy riêng: cd src && python manage.py test exams.tests.test_views_publish
"""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role
from config.tests.factories import make_question, make_user
from exams.models import Exam, ExamStatus


class ExamQuestionsBase(TestCase):
    def setUp(self):
        self.teacher = make_user(Role.TEACHER)
        self.exam = self.teacher.create_exam({"title": "Đề giữa kỳ", "duration_minutes": 30})
        self.q1 = make_question(self.teacher, content="Câu một")
        self.q2 = make_question(self.teacher, content="Câu hai")
        self.q3 = make_question(self.teacher, content="Câu ba")
        self.client.force_login(self.teacher)
        self.url = reverse("exams:questions", args=[self.exam.pk])

    def positions(self):
        return list(self.exam.exam_questions.order_by("position").values_list("question__content", flat=True))


class ChooseQuestionTests(ExamQuestionsBase):
    def test_ngan_hang_chi_hien_cau_active_cua_minh_chua_co_trong_de(self):
        make_question(self.teacher, content="Câu nháp", activate=False)
        make_question(make_user(Role.TEACHER), content="Câu người khác")
        self.exam.add_question(self.q1.pk, 1)
        response = self.client.get(self.url)
        bank = [q.content for q in response.context["bank"]]
        self.assertEqual(sorted(bank), ["Câu ba", "Câu hai"])

    def test_tim_cau_hoi_trong_ngan_hang(self):
        response = self.client.get(self.url, {"q": "hai"})
        self.assertEqual([q.content for q in response.context["bank"]], ["Câu hai"])

    def test_them_nhieu_cau_cung_diem(self):
        response = self.client.post(
            self.url, {"action": "add", "question_ids": [self.q1.pk, self.q2.pk], "points": "2,5"}, follow=True
        )
        self.assertContains(response, "Đã thêm 2 câu hỏi vào đề.")
        self.assertEqual(self.positions(), ["Câu một", "Câu hai"])
        self.assertEqual(set(self.exam.exam_questions.values_list("points", flat=True)), {Decimal("2.5")})
        self.assertContains(response, "tổng 5,00 điểm")

    def test_them_khong_chon_cau(self):
        response = self.client.post(self.url, {"action": "add", "points": "1"}, follow=True)
        self.assertContains(response, "Vui lòng chọn ít nhất 1 câu hỏi.")

    def test_diem_khong_hop_le_khong_them_cau_nao(self):
        for points, text in (("0", "Điểm phải lớn hơn 0."), ("abc", "Điểm phải là số."),
                             ("", "Vui lòng nhập điểm."), ("5000", "Điểm mỗi câu tối đa 1000.")):
            with self.subTest(points=points):
                response = self.client.post(
                    self.url, {"action": "add", "question_ids": [self.q1.pk, self.q2.pk], "points": points}, follow=True
                )
                self.assertContains(response, text)
                self.assertFalse(self.exam.exam_questions.exists())

    def test_khong_them_cau_cua_giang_vien_khac(self):
        foreign = make_question(make_user(Role.TEACHER))
        response = self.client.post(self.url, {"action": "add", "question_ids": [foreign.pk], "points": "1"}, follow=True)
        self.assertContains(response, "Câu hỏi không thuộc ngân hàng của bạn.")
        self.assertFalse(self.exam.exam_questions.exists())

    def test_them_cau_trung(self):
        self.exam.add_question(self.q1.pk, 1)
        response = self.client.post(self.url, {"action": "add", "question_ids": [self.q1.pk], "points": "1"}, follow=True)
        self.assertContains(response, "Câu hỏi đã có trong đề.")
        self.assertEqual(self.exam.exam_questions.count(), 1)

    def test_sap_xep_bo_cau_va_luu_diem(self):
        for q in (self.q1, self.q2, self.q3):
            self.exam.add_question(q.pk, 1)
        self.client.post(self.url, {"action": f"up:{self.q3.pk}"})
        self.assertEqual(self.positions(), ["Câu một", "Câu ba", "Câu hai"])
        self.client.post(self.url, {"action": f"down:{self.q1.pk}"})
        self.assertEqual(self.positions(), ["Câu ba", "Câu một", "Câu hai"])
        # Câu đầu không lên được nữa, giữ nguyên.
        self.client.post(self.url, {"action": f"up:{self.q3.pk}"})
        self.assertEqual(self.positions(), ["Câu ba", "Câu một", "Câu hai"])

        response = self.client.post(self.url, {"action": f"remove:{self.q1.pk}"}, follow=True)
        self.assertContains(response, "Đã bỏ câu hỏi khỏi đề.")
        self.assertEqual(self.positions(), ["Câu ba", "Câu hai"])
        self.assertEqual(list(self.exam.exam_questions.order_by("position").values_list("position", flat=True)), [1, 2])

        response = self.client.post(
            self.url,
            {"action": "save_points", f"points_{self.q3.pk}": "3", f"points_{self.q2.pk}": "0,5"},
            follow=True,
        )
        self.assertContains(response, "Đã lưu điểm các câu hỏi.")
        points = dict(self.exam.exam_questions.values_list("question__content", "points"))
        self.assertEqual(points, {"Câu ba": Decimal("3"), "Câu hai": Decimal("0.5")})

    def test_enter_trong_o_diem_la_luu_diem(self):
        # Trình duyệt bấm nút submit đầu tiên khi nhấn Enter; nút đó phải là "Lưu điểm",
        # kể cả khi đề chỉ có 1 câu (↑ ↓ đều tắt, nút bật đầu tiên trước đây là "Bỏ").
        self.exam.add_question(self.q1.pk, 1)
        html = self.client.get(self.url).content.decode()
        form = html[html.index('<form method="post" class="mb-4">'):]
        first_button = form[form.index("<button"):]
        self.assertTrue(first_button.startswith('<button type="submit" name="action" value="save_points"'))

    def test_luu_diem_sai_bao_dung_cau_va_khong_luu(self):
        self.exam.add_question(self.q1.pk, 1)
        self.exam.add_question(self.q2.pk, 1)
        response = self.client.post(
            self.url, {"action": "save_points", f"points_{self.q1.pk}": "4", f"points_{self.q2.pk}": "-1"}, follow=True
        )
        self.assertContains(response, "Câu 2: Điểm phải lớn hơn 0.")
        self.assertEqual(set(self.exam.exam_questions.values_list("points", flat=True)), {Decimal("1")})

    def test_thao_tac_la_bi_tu_choi(self):
        response = self.client.post(self.url, {"action": "xoa_het"}, follow=True)
        self.assertContains(response, "Thao tác không hợp lệ.")

    def test_de_da_phat_hanh_khong_vao_trang_chon_cau(self):
        self.exam.add_question(self.q1.pk, 1)
        self.exam.publish()
        response = self.client.post(self.url, {"action": "add", "question_ids": [self.q2.pk], "points": "1"}, follow=True)
        self.assertContains(response, "Đề đã phát hành, không thể sửa nội dung.")
        self.assertEqual(self.exam.exam_questions.count(), 1)

    def test_giang_vien_khac_va_sinh_vien_bi_chan(self):
        for user in (make_user(Role.TEACHER), make_user(Role.STUDENT)):
            with self.subTest(role=user.role):
                self.client.force_login(user)
                self.assertEqual(self.client.get(self.url).status_code, 403)
                self.assertEqual(
                    self.client.post(self.url, {"action": "add", "question_ids": [self.q1.pk], "points": "1"}).status_code,
                    403,
                )
        self.assertFalse(self.exam.exam_questions.exists())


class PublishTests(ExamQuestionsBase):
    def setUp(self):
        super().setUp()
        self.publish_url = reverse("exams:publish", args=[self.exam.pk])

    def test_phat_hanh_thanh_cong(self):
        self.exam.add_question(self.q1.pk, 2)
        response = self.client.post(self.publish_url, follow=True)
        self.assertContains(response, "Đã phát hành đề thi.")
        self.exam.refresh_from_db()
        self.assertEqual(self.exam.status, ExamStatus.PUBLISHED)
        # Đã phát hành: không còn nút sửa / chọn câu hỏi / phát hành.
        self.assertNotContains(response, reverse("exams:questions", args=[self.exam.pk]))
        self.assertNotContains(response, self.publish_url)

    def test_de_rong_khong_phat_hanh(self):
        response = self.client.post(self.publish_url, follow=True)
        self.assertContains(response, "Chưa thể phát hành đề:")
        self.assertContains(response, "Đề cần ít nhất 1 câu hỏi.")
        self.exam.refresh_from_db()
        self.assertEqual(self.exam.status, ExamStatus.DRAFT)

    def test_lich_da_qua_khong_phat_hanh(self):
        self.exam.add_question(self.q1.pk, 2)
        Exam.objects.filter(pk=self.exam.pk).update(closes_at=timezone.now() - timedelta(hours=1))
        response = self.client.post(self.publish_url, follow=True)
        self.assertContains(response, "Thời gian đóng đã qua.")
        self.exam.refresh_from_db()
        self.assertEqual(self.exam.status, ExamStatus.DRAFT)

    def test_cau_hoi_bi_luu_tru_sau_khi_chon_thi_khong_phat_hanh(self):
        self.exam.add_question(self.q1.pk, 2)
        self.q1.archive()
        response = self.client.post(self.publish_url, follow=True)
        self.assertContains(response, "Câu 1 chưa sẵn sàng (cần ACTIVE, đủ phương án và 1 đáp án đúng).")

    def test_phat_hanh_lai_bi_tu_choi(self):
        self.exam.add_question(self.q1.pk, 2)
        self.exam.publish()
        response = self.client.post(self.publish_url, follow=True)
        self.assertContains(response, "Đề đã phát hành, không thể sửa nội dung.")

    def test_noi_dung_de_da_phat_hanh_duoc_bao_toan(self):
        # BR-14: sửa câu hỏi gốc sau khi phát hành tạo bản mới, đề vẫn trỏ câu cũ.
        self.exam.add_question(self.q1.pk, 2)
        self.client.post(self.publish_url)
        self.assertTrue(self.q1.is_locked())
        revision = self.q1.create_revision()
        self.assertNotEqual(revision.pk, self.q1.pk)
        self.assertEqual(list(self.exam.exam_questions.values_list("question_id", flat=True)), [self.q1.pk])

    def test_chi_nhan_post_va_dung_chu_de(self):
        self.exam.add_question(self.q1.pk, 2)
        self.assertEqual(self.client.get(self.publish_url).status_code, 405)
        self.client.force_login(make_user(Role.TEACHER))
        self.assertEqual(self.client.post(self.publish_url).status_code, 403)
        self.exam.refresh_from_db()
        self.assertEqual(self.exam.status, ExamStatus.DRAFT)
