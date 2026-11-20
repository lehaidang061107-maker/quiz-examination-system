
from django.test import TestCase
from django.urls import reverse

from accounts.models import Role
from config.tests.factories import make_question, make_user
from questions.models import QuestionStatus


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
        make_question(
            self.teacher,
            content="Câu hỏi nháp",
            activate=False,
        )
        make_question(
            self.teacher,
            content="Câu hỏi đang dùng",
            activate=True,
        )

        self.client.force_login(self.teacher)
        response = self.client.get(
            self.url,
            {"status": QuestionStatus.DRAFT},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Câu hỏi nháp")
        self.assertNotContains(response, "Câu hỏi đang dùng")

    def test_filter_active_questions(self):
        make_question(
            self.teacher,
            content="Câu hỏi nháp",
            activate=False,
        )
        make_question(
            self.teacher,
            content="Câu hỏi đang dùng",
            activate=True,
        )

        self.client.force_login(self.teacher)
        response = self.client.get(
            self.url,
            {"status": QuestionStatus.ACTIVE},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Câu hỏi đang dùng")
        self.assertNotContains(response, "Câu hỏi nháp")

    def test_archived_questions_are_not_displayed(self):
        question = make_question(
            self.teacher,
            content="Câu hỏi đã lưu trữ",
        )
        question.archive()

        self.client.force_login(self.teacher)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Câu hỏi đã lưu trữ")

    def test_question_list_is_paginated(self):
        for number in range(11):
            make_question(
                self.teacher,
                content=f"Câu hỏi số {number}",
            )

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
