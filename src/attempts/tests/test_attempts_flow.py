import json
from datetime import timedelta

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role
from attempts.models import Submission, SubmissionAnswer, SubmissionStatus
from config.tests.factories import make_user
from exams.models import Exam, ExamParticipant, ExamQuestion, ExamStatus
from questions.models import AnswerOption, Question, QuestionStatus


class AttemptsFlowAndConcurrencyTests(TestCase):
    def setUp(self):
        self.teacher = make_user(Role.TEACHER)
        self.student = make_user(Role.STUDENT)

        self.question = Question.objects.create(
            teacher=self.teacher,
            content="1 + 1 bằng mấy?",
            status=QuestionStatus.ACTIVE,
        )
        self.opt_wrong = AnswerOption.objects.create(
            question=self.question, content="3", display_order=1, is_correct=False
        )
        self.opt_right = AnswerOption.objects.create(
            question=self.question, content="2", display_order=2, is_correct=True
        )

        now = timezone.now()
        self.exam = Exam.objects.create(
            teacher=self.teacher,
            title="Đề kiểm thử S3-20",
            duration_minutes=30,
            opens_at=now - timedelta(minutes=5),
            closes_at=now + timedelta(hours=1),
            status=ExamStatus.PUBLISHED,
        )
        ExamQuestion.objects.create(
            exam=self.exam, question=self.question, position=1, points=10
        )
        ExamParticipant.objects.create(
            exam=self.exam, student=self.student, is_active=True
        )

        self.client = Client()
        self.client.force_login(self.student)

    def test_start_exam_idempotent_on_double_click(self):
        """S3-16 & S3-20: Bấm Bắt đầu 2 lần liên tiếp chỉ tạo đúng 1 Submission."""
        url = reverse("attempts:start_exam", args=[self.exam.pk])
        res1 = self.client.post(url)
        res2 = self.client.post(url)

        self.assertEqual(Submission.objects.filter(exam=self.exam, student=self.student).count(), 1)
        sub = Submission.objects.get(exam=self.exam, student=self.student)
        self.assertRedirects(res1, reverse("attempts:take_exam", args=[sub.pk]))
        self.assertRedirects(res2, reverse("attempts:take_exam", args=[sub.pk]))

    def test_save_answer_version_conflict_and_network_retry(self):
        """S3-18 & S3-20: Chống ghi đè khi mở 2 tab (StaleVersionError) & retry khi rớt mạng."""
        sub = Submission.start(exam=self.exam, student=self.student)
        save_url = reverse("attempts:save_answer_api", args=[sub.pk])

        res_tab1 = self.client.post(
            save_url,
            data=json.dumps(
                {"question_id": self.question.pk, "option_id": self.opt_right.pk, "version": 0}
            ),
            content_type="application/json",
        )
        self.assertEqual(res_tab1.status_code, 200)
        self.assertEqual(res_tab1.json()["version"], 1)

        res_tab2 = self.client.post(
            save_url,
            data=json.dumps(
                {"question_id": self.question.pk, "option_id": self.opt_wrong.pk, "version": 0}
            ),
            content_type="application/json",
        )
        self.assertIn(res_tab2.status_code, [400, 409])
        self.assertFalse(res_tab2.json().get("ok"))

        ans = SubmissionAnswer.objects.get(submission=sub, question=self.question)
        self.assertEqual(ans.selected_option_id, self.opt_right.pk)

    def test_auto_finalize_when_deadline_expired(self):
        """S3-19 & S3-20: Quá hạn deadline_at thì lưu đáp án hoặc vào lại phòng thi đều tự nộp."""
        sub = Submission.start(exam=self.exam, student=self.student)
        sub.save_answer(question_id=self.question.pk, option_id=self.opt_right.pk, version=0)

        past_start = timezone.now() - timedelta(minutes=35)
        past_deadline = timezone.now() - timedelta(seconds=5)
        Submission.objects.filter(pk=sub.pk).update(
            started_at=past_start,
            last_saved_at=past_start + timedelta(seconds=10),
            deadline_at=past_deadline,
        )

        save_url = reverse("attempts:save_answer_api", args=[sub.pk])
        res = self.client.post(
            save_url,
            data=json.dumps(
                {"question_id": self.question.pk, "option_id": self.opt_wrong.pk, "version": 1}
            ),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 409)
        self.assertTrue(res.json().get("finalized"))
        self.assertEqual(res.json().get("reason"), "expired")

        sub.refresh_from_db()
        self.assertIn(sub.status, [SubmissionStatus.SUBMITTED, SubmissionStatus.GRADED])
        ans = SubmissionAnswer.objects.get(submission=sub, question=self.question)
        self.assertEqual(ans.selected_option_id, self.opt_right.pk)

    def test_concurrent_submit_is_idempotent(self):
        """S3-19 & S3-20: Gửi request Nộp bài đồng thời nhiều lần không tạo bản nộp trùng."""
        sub = Submission.start(exam=self.exam, student=self.student)
        sub.save_answer(question_id=self.question.pk, option_id=self.opt_right.pk, version=0)

        submit_url = reverse("attempts:submit_exam", args=[sub.pk])
        res1 = self.client.post(submit_url)
        res2 = self.client.post(submit_url)

        self.assertRedirects(res1, reverse("attempts:exam_list"))
        self.assertRedirects(res2, reverse("attempts:exam_list"))

        sub.refresh_from_db()
        self.assertIn(sub.status, [SubmissionStatus.SUBMITTED, SubmissionStatus.GRADED])
        self.assertIsNotNone(sub.submitted_at)

    def test_start_exam_rejects_draft_or_unassigned_exam(self):
        """Review fix #1: Sinh viên tự POST /start/ vào đề nháp hoặc đề chưa được giao bị chặn."""
        draft_exam = Exam.objects.create(
            teacher=self.teacher,
            title="Đề nháp chưa công bố",
            duration_minutes=30,
            status=ExamStatus.DRAFT,
        )
        res_draft = self.client.post(reverse("attempts:start_exam", args=[draft_exam.pk]))
        self.assertRedirects(res_draft, reverse("attempts:exam_list"))
        self.assertEqual(Submission.objects.filter(exam=draft_exam).count(), 0)

        unassigned_exam = Exam.objects.create(
            teacher=self.teacher,
            title="Đề không giao cho sinh viên này",
            duration_minutes=30,
            opens_at=timezone.now() - timedelta(minutes=5),
            closes_at=timezone.now() + timedelta(hours=1),
            status=ExamStatus.PUBLISHED,
        )
        res_unassigned = self.client.post(reverse("attempts:start_exam", args=[unassigned_exam.pk]))
        self.assertRedirects(res_unassigned, reverse("attempts:exam_list"))
        self.assertEqual(Submission.objects.filter(exam=unassigned_exam).count(), 0)

    def test_take_exam_without_deadline_hides_countdown(self):
        """Review fix #3: Đề không giới hạn thời gian (deadline_at=None) không tự nộp sau 1 giây."""
        unlimited_exam = Exam.objects.create(
            teacher=self.teacher,
            title="Đề không giới hạn thời gian",
            duration_minutes=None,
            opens_at=timezone.now() - timedelta(minutes=5),
            closes_at=None,
            status=ExamStatus.PUBLISHED,
        )
        ExamQuestion.objects.create(
            exam=unlimited_exam, question=self.question, position=1, points=10
        )
        ExamParticipant.objects.create(
            exam=unlimited_exam, student=self.student, is_active=True
        )

        sub = Submission.start(exam=unlimited_exam, student=self.student)
        self.assertIsNone(sub.deadline_at)

        res = self.client.get(reverse("attempts:take_exam", args=[sub.pk]))
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.context["has_deadline"])
        self.assertIsNone(res.context["remaining_seconds"])
        self.assertContains(res, "Không giới hạn thời gian")

    def test_save_answer_api_rejects_non_object_json_payload(self):
        """Review fix #4: Body JSON không phải dict (vd: []) trả về 400 thay vì lỗi 500."""
        sub = Submission.start(exam=self.exam, student=self.student)
        save_url = reverse("attempts:save_answer_api", args=[sub.pk])

        res = self.client.post(
            save_url,
            data=json.dumps([1, 2, 3]),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertFalse(res.json().get("ok"))

    def test_exam_list_shows_unlimited_duration(self):
        """Đề không giới hạn thời lượng hiển thị "Không giới hạn" thay vì "None phút"."""
        unlimited_exam = Exam.objects.create(
            teacher=self.teacher,
            title="Đề không giới hạn thời lượng",
            duration_minutes=None,
            opens_at=timezone.now() - timedelta(minutes=5),
            status=ExamStatus.PUBLISHED,
        )
        ExamParticipant.objects.create(
            exam=unlimited_exam, student=self.student, is_active=True
        )

        res = self.client.get(reverse("attempts:exam_list"))

        self.assertContains(res, "Đề không giới hạn thời lượng")
        self.assertNotContains(res, "None phút")

    def test_take_exam_uses_base_layout_header(self):
        """Phòng thi dùng tiêu đề và nút Nộp bài trong header chung của base.html."""
        sub = Submission.start(exam=self.exam, student=self.student)

        res = self.client.get(reverse("attempts:take_exam", args=[sub.pk]))

        self.assertContains(res, '<h1 class="h4 fw-bold mb-1">Đề kiểm thử S3-20</h1>', html=False)
        self.assertContains(res, 'id="btn-submit-exam"')

    def test_take_exam_does_not_expose_correct_answer_metadata(self):
        """S3-09: HTML phòng thi không tiết lộ metadata xác định đáp án đúng."""
        sub = Submission.start(exam=self.exam, student=self.student)

        res = self.client.get(reverse("attempts:take_exam", args=[sub.pk]))

        self.assertEqual(res.status_code, 200)
        self.assertContains(res, self.opt_wrong.content)
        self.assertContains(res, self.opt_right.content)
        self.assertNotContains(res, "is_correct")
        self.assertNotContains(res, "correct_option")
        self.assertNotContains(res, "Đáp án đúng")

    def test_save_answer_api_does_not_return_grading_data(self):
        """S3-09: API lưu đáp án chỉ trả trạng thái lưu và version."""
        sub = Submission.start(exam=self.exam, student=self.student)
        save_url = reverse("attempts:save_answer_api", args=[sub.pk])

        res = self.client.post(
            save_url,
            data=json.dumps(
                {
                    "question_id": self.question.pk,
                    "option_id": self.opt_right.pk,
                    "version": 0,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(res.status_code, 200)
        self.assertEqual(set(res.json().keys()), {"ok", "version"})
        self.assertTrue(res.json()["ok"])