from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role
from attempts.models import Submission, SubmissionAnswer
from config.tests.factories import (
    make_open_exam,
    make_question,
    make_user,
)
from questions.models import Question, QuestionStatus


class QuestionListViewTests(TestCase):
    def setUp(self):
        self.teacher = make_user(Role.TEACHER)
        self.url = reverse("questions:list")

    def test_teacher_can_view_question_list(self):
        make_question(self.teacher, content="Câu hỏi của tôi")

        self.client.force_login(self.teacher)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Câu hỏi của tôi")

    def test_teacher_only_sees_own_questions(self):
        other_teacher = make_user(Role.TEACHER)

        make_question(self.teacher, content="Câu hỏi của giảng viên hiện tại")
        make_question(other_teacher, content="Câu hỏi của giảng viên khác")

        self.client.force_login(self.teacher)
        response = self.client.get(self.url)

        self.assertContains(response, "Câu hỏi của giảng viên hiện tại")
        self.assertNotContains(response, "Câu hỏi của giảng viên khác")

    def test_search_questions_by_content(self):
        make_question(self.teacher, content="Câu hỏi về Python")
        make_question(self.teacher, content="Câu hỏi về Django")

        self.client.force_login(self.teacher)
        response = self.client.get(self.url, {"q": "Python"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Câu hỏi về Python")
        self.assertNotContains(response, "Câu hỏi về Django")

    def test_filter_draft_questions(self):
        make_question(self.teacher, content="Câu hỏi nháp", activate=False)
        make_question(self.teacher, content="Câu hỏi đang dùng", activate=True)

        self.client.force_login(self.teacher)
        response = self.client.get(
            self.url,
            {"status": QuestionStatus.DRAFT},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Câu hỏi nháp")
        self.assertNotContains(response, "Câu hỏi đang dùng")

    def test_filter_active_questions(self):
        make_question(self.teacher, content="Câu hỏi nháp", activate=False)
        make_question(self.teacher, content="Câu hỏi đang dùng", activate=True)

        self.client.force_login(self.teacher)
        response = self.client.get(
            self.url,
            {"status": QuestionStatus.ACTIVE},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Câu hỏi đang dùng")
        self.assertNotContains(response, "Câu hỏi nháp")

    def test_archived_questions_are_not_displayed(self):
        question = make_question(self.teacher, content="Câu hỏi đã lưu trữ")
        question.archive()

        self.client.force_login(self.teacher)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Câu hỏi đã lưu trữ")

    def test_question_list_is_paginated(self):
        for number in range(11):
            make_question(self.teacher, content=f"Câu hỏi số {number}")

        self.client.force_login(self.teacher)
        response = self.client.get(self.url, {"page": 2})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertEqual(len(response.context["questions"]), 1)

    def test_question_option_count_is_displayed_in_context(self):
        make_question(self.teacher, content="Câu hỏi có ba phương án")

        self.client.force_login(self.teacher)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        question = response.context["questions"][0]
        self.assertEqual(question.option_count, 3)

    def test_empty_question_list(self):
        self.client.force_login(self.teacher)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Không tìm thấy câu hỏi nào")

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_student_cannot_view_question_list(self):
        student = make_user(Role.STUDENT)
        self.client.force_login(student)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)


class QuestionEditorViewTests(TestCase):
    def setUp(self):
        self.teacher = make_user(Role.TEACHER)
        self.student = make_user(Role.STUDENT)
        self.create_url = reverse("questions:create")

        self.client.force_login(self.teacher)

    def test_teacher_can_view_create_page(self):
        response = self.client.get(self.create_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nội dung câu hỏi")

    def test_teacher_can_update_question(self):
        question = make_question(
            self.teacher,
            content="Câu hỏi ban đầu",
        )
        options = list(question.options.order_by("display_order"))

        edit_url = reverse(
            "questions:edit",
            args=[question.question_id],
        )

        response = self.client.post(
            edit_url,
            {
                "content": "Câu hỏi đã cập nhật",
                "option_id": [
                    str(options[0].option_id),
                    str(options[1].option_id),
                    str(options[2].option_id),
                ],
                "option_content": [
                    "Phương án A mới",
                    "Phương án B mới",
                    "Phương án C mới",
                ],
                "correct_option": "1",
                "action": "activate",
            },
        )

        self.assertRedirects(response, reverse("questions:list"))

        question.refresh_from_db()

        self.assertEqual(question.content, "Câu hỏi đã cập nhật")
        self.assertEqual(question.status, QuestionStatus.ACTIVE)
        self.assertEqual(question.options.count(), 3)
        self.assertEqual(
            question.options.filter(is_correct=True).count(),
            1,
        )
        self.assertEqual(
            question.options.get(is_correct=True).content,
            "Phương án B mới",
        )

    def test_cannot_remove_option_used_in_submission(self):
        question = make_question(self.teacher)
        options = list(question.options.order_by("display_order"))
        now = timezone.now()
        exam = self.teacher.create_exam({
            "title": "Đề kiểm tra nháp",
            "duration_minutes": 30,
            "opens_at": now - timedelta(hours=1),
            "closes_at": now + timedelta(days=1),
        })
        exam.add_question(question.pk, 2)
        self.teacher.assign_students(exam.pk, [self.student.pk])

        submission = Submission.start(exam, self.student)

        submission.save_answer(
            question.pk,
            options[0].option_id,
            version=0,
        )

        question.refresh_from_db()
        self.assertFalse(question.is_locked())

        edit_url = reverse(
            "questions:edit",
            args=[question.question_id],
        )

        response = self.client.post(
            edit_url,
            {
                "content": question.content,
                "option_id": [
                    str(options[1].option_id),
                    str(options[2].option_id),
                ],
                "option_content": [
                    options[1].content,
                    options[2].content,
                ],
                "correct_option": "0",
                "action": "draft",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            SubmissionAnswer.objects.filter(
                selected_option=options[0],
            ).count(),
            1,
        )
        self.assertEqual(question.options.count(), 3)
        self.assertContains(
            response,
            "Không thể xóa phương án đã được sử dụng",
        )

    def test_teacher_cannot_edit_other_teachers_question(self):
        other_teacher = make_user(Role.TEACHER)
        question = make_question(
            other_teacher,
            content="Câu hỏi của giảng viên khác",
        )

        edit_url = reverse(
            "questions:edit",
            args=[question.question_id],
        )

        response = self.client.get(edit_url)

        self.assertEqual(response.status_code, 404)

    def test_teacher_can_save_incomplete_draft(self):
        response = self.client.post(
            self.create_url,
            {
                "content": "",
                "option_content": ["Phương án 1", ""],
                "action": "draft",
            },
        )

        self.assertRedirects(response, reverse("questions:list"))

        question = Question.objects.get(teacher=self.teacher)

        self.assertEqual(question.content, "")
        self.assertEqual(question.status, QuestionStatus.DRAFT)
        self.assertEqual(question.options.count(), 1)

    def test_teacher_can_create_and_activate_valid_question(self):
        response = self.client.post(
            self.create_url,
            {
                "content": "Thủ đô Việt Nam là gì?",
                "option_content": ["Hà Nội", "Đà Nẵng", "Huế"],
                "correct_option": "0",
                "action": "activate",
            },
        )

        self.assertRedirects(response, reverse("questions:list"))

        question = Question.objects.get(teacher=self.teacher)

        self.assertEqual(question.status, QuestionStatus.ACTIVE)
        self.assertEqual(question.options.count(), 3)
        self.assertEqual(
            question.options.filter(is_correct=True).count(),
            1,
        )

    def test_cannot_activate_question_without_content(self):
        response = self.client.post(
            self.create_url,
            {
                "content": "",
                "option_content": ["Phương án A", "Phương án B"],
                "correct_option": "0",
                "action": "activate",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Question.objects.filter(
                teacher=self.teacher,
                status=QuestionStatus.ACTIVE,
            ).exists()
        )

    def test_cannot_activate_question_with_less_than_two_options(self):
        response = self.client.post(
            self.create_url,
            {
                "content": "Câu hỏi kiểm tra",
                "option_content": ["Phương án A", ""],
                "correct_option": "0",
                "action": "activate",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Question.objects.filter(
                teacher=self.teacher,
                status=QuestionStatus.ACTIVE,
            ).exists()
        )

    def test_cannot_activate_question_without_correct_option(self):
        response = self.client.post(
            self.create_url,
            {
                "content": "Câu hỏi kiểm tra",
                "option_content": ["Phương án A", "Phương án B"],
                "action": "activate",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Question.objects.filter(
                teacher=self.teacher,
                status=QuestionStatus.ACTIVE,
            ).exists()
        )

    def test_student_cannot_create_question(self):
        self.client.force_login(self.student)

        response = self.client.get(self.create_url)

        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_cannot_create_question(self):
        self.client.logout()

        response = self.client.get(self.create_url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_teacher_can_view_edit_page(self):
        question = make_question(
            self.teacher,
            content="Câu hỏi cần chỉnh sửa",
        )
        edit_url = reverse(
            "questions:edit",
            args=[question.question_id],
        )

        response = self.client.get(edit_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Câu hỏi cần chỉnh sửa")

    def test_cannot_create_revision_with_get_request(self):
        question = make_question(
            self.teacher,
            content="Câu hỏi gốc",
        )

        revision_url = reverse(
            "questions:revision",
            args=[question.question_id],
        )

        response = self.client.get(revision_url)

        self.assertEqual(response.status_code, 405)
        self.assertEqual(
            Question.objects.filter(teacher=self.teacher).count(),
            1,
        )

    def test_teacher_can_create_revision_of_locked_question(self):
        question = make_question(
            self.teacher,
            content="Câu hỏi phiên bản cũ",
        )
        original_options = list(
            question.options.order_by("display_order")
        )

        make_open_exam(
            self.teacher,
            [self.student],
            [question],
        )

        revision_url = reverse(
            "questions:revision",
            args=[question.question_id],
        )

        response = self.client.post(revision_url)

        revision = Question.objects.exclude(
            question_id=question.question_id,
        ).get(teacher=self.teacher)

        self.assertRedirects(
            response,
            reverse(
                "questions:edit",
                args=[revision.question_id],
            ),
        )

        self.assertNotEqual(
            revision.question_id,
            question.question_id,
        )
        self.assertEqual(revision.content, question.content)
        self.assertEqual(revision.status, QuestionStatus.DRAFT)
        self.assertEqual(revision.options.count(), len(original_options))

        self.assertEqual(
            list(
                revision.options.order_by("display_order").values_list(
                    "content",
                    "is_correct",
                )
            ),
            [
                (option.content, option.is_correct)
                for option in original_options
            ],
        )

        question.refresh_from_db()
        self.assertEqual(question.content, "Câu hỏi phiên bản cũ")

    def test_editing_revision_does_not_change_original_exam_question(self):
        original = make_question(
            self.teacher,
            content="Câu hỏi gốc",
        )
        original_options = list(
            original.options.order_by("display_order")
        )

        exam = make_open_exam(
            self.teacher,
            [self.student],
            [original],
        )

        revision_response = self.client.post(
            reverse(
                "questions:revision",
                args=[original.question_id],
            )
        )

        revision = Question.objects.exclude(
            question_id=original.question_id,
        ).get(teacher=self.teacher)

        self.assertEqual(revision_response.status_code, 302)

        revision_options = list(
            revision.options.order_by("display_order")
        )

        edit_response = self.client.post(
            reverse(
                "questions:edit",
                args=[revision.question_id],
            ),
            {
                "content": "Câu hỏi phiên bản mới",
                "option_id": [
                    str(option.option_id)
                    for option in revision_options
                ],
                "option_content": [
                    "Phương án mới A",
                    "Phương án mới B",
                    "Phương án mới C",
                ],
                "correct_option": "1",
                "action": "activate",
            },
        )

        self.assertRedirects(
            edit_response,
            reverse("questions:list"),
        )

        original.refresh_from_db()
        revision.refresh_from_db()

        self.assertEqual(original.content, "Câu hỏi gốc")
        self.assertEqual(
            list(
                original.options.order_by("display_order").values_list(
                    "content",
                    "is_correct",
                )
            ),
            [
                (option.content, option.is_correct)
                for option in original_options
            ],
        )

        self.assertEqual(revision.content, "Câu hỏi phiên bản mới")
        self.assertEqual(revision.status, QuestionStatus.ACTIVE)

        exam_question = exam.exam_questions.get()
        self.assertEqual(
            exam_question.question_id,
            original.question_id,
        )

    def test_teacher_cannot_view_edit_page_of_locked_question(self):
        question = make_question(
            self.teacher,
            content="Câu hỏi gốc đã phát hành",
        )
        make_open_exam(
            self.teacher,
            [self.student],
            [question],
        )

        edit_url = reverse(
            "questions:edit",
            args=[question.question_id],
        )

        response = self.client.get(edit_url, follow=True)

        self.assertRedirects(response, reverse("questions:list"))
        self.assertContains(
            response,
            "Câu hỏi đã dùng trong đề đã phát hành",
        )

    def test_teacher_cannot_update_locked_question_directly(self):
        question = make_question(
            self.teacher,
            content="Câu hỏi gốc đã phát hành",
        )
        original_options = list(
            question.options.order_by("display_order")
        )
        make_open_exam(
            self.teacher,
            [self.student],
            [question],
        )

        edit_url = reverse(
            "questions:edit",
            args=[question.question_id],
        )

        response = self.client.post(
            edit_url,
            {
                "content": "Nội dung bị sửa trái phép",
                "option_id": [
                    str(option.option_id)
                    for option in original_options
                ],
                "option_content": [
                    "Phương án bị sửa"
                    for option in original_options
                ],
                "correct_option": "0",
                "action": "activate",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("questions:list"))

        question.refresh_from_db()
        self.assertEqual(
            question.content,
            "Câu hỏi gốc đã phát hành",
        )
        self.assertEqual(
            list(
                question.options.order_by("display_order").values_list(
                    "content",
                    flat=True,
                )
            ),
            [option.content for option in original_options],
        )

    def test_cannot_create_revision_of_unlocked_question(self):
        question = make_question(
            self.teacher,
            content="Câu hỏi chưa được sử dụng",
        )

        revision_url = reverse(
            "questions:revision",
            args=[question.question_id],
        )

        response = self.client.post(revision_url, follow=True)
        self.assertRedirects(
            response,
            reverse("questions:list"),
        )

        self.assertEqual(
            Question.objects.filter(teacher=self.teacher).count(),
            1,
        )
        self.assertContains(
            response,
            "Chỉ có thể tạo phiên bản mới",
            status_code=200,
        )

    def test_cannot_create_revision_of_other_teachers_question(self):
        other_teacher = make_user(Role.TEACHER)
        question = make_question(
            other_teacher,
            content="Câu hỏi của giáo viên khác",
        )

        make_open_exam(
            other_teacher,
            [self.student],
            [question],
        )

        revision_url = reverse(
            "questions:revision",
            args=[question.question_id],
        )

        response = self.client.post(revision_url)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            Question.objects.filter(teacher=other_teacher).count(),
            1,
        )

    def test_can_edit_draft_saved_without_options(self):
        self.client.post(
            self.create_url,
            {
                "content": "Câu hỏi nháp",
                "option_content": ["", ""],
                "action": "draft",
            },
        )

        question = Question.objects.get(teacher=self.teacher)
        self.assertEqual(question.options.count(), 0)

        edit_url = reverse("questions:edit", args=[question.question_id])
        response = self.client.get(edit_url)

        # Hai dòng phương án mặc định phải có option_id để view ghép đúng.
        self.assertContains(response, 'name="option_id"', count=3)

        response = self.client.post(
            edit_url,
            {
                "content": "Câu hỏi nháp",
                "option_id": ["", ""],
                "option_content": ["Phương án A", "Phương án B"],
                "correct_option": "0",
                "action": "activate",
            },
        )

        self.assertRedirects(response, reverse("questions:list"))

        question.refresh_from_db()
        self.assertEqual(question.status, QuestionStatus.ACTIVE)
        self.assertEqual(question.options.count(), 2)
