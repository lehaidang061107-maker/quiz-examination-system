"""Hàm tạo dữ liệu nhanh cho test, để mỗi test chỉ viết phần cần kiểm tra."""
from datetime import timedelta

from django.utils import timezone

from accounts.models import Role, User
from questions.models import AnswerOption, Question

PASSWORD = "matkhau123"


def make_user(role=Role.STUDENT, email=None, name=None):
    """Tạo tài khoản và trả về đúng lớp con: Admin, Teacher hoặc Student."""
    make_user.count = getattr(make_user, "count", 0) + 1
    email = email or f"{role.lower()}{make_user.count}@test.example"
    user = User.objects.create_user(email, PASSWORD, full_name=name or f"{role} {make_user.count}", role=role)
    user.refresh_from_db()
    return user.as_role()


def make_question(teacher, content="1 + 1 bằng mấy?", options=("2", "3", "4"), correct=0, activate=True):
    """Tạo câu hỏi có các phương án; phương án thứ `correct` là đáp án đúng."""
    question = Question.objects.create(teacher=teacher, content=content)
    for i, text in enumerate(options):
        AnswerOption.objects.create(question=question, content=text, display_order=i + 1, is_correct=(i == correct))
    if activate:
        question.activate()
    question.refresh_from_db()
    return question


def make_open_exam(teacher, students, questions, points=2, duration=30):
    """Tạo đề đã phát hành, đang trong giờ thi, đã giao cho các sinh viên."""
    now = timezone.now()
    exam = teacher.create_exam({
        "title": "Đề kiểm tra",
        "duration_minutes": duration,
        "opens_at": now - timedelta(hours=1),
        "closes_at": now + timedelta(days=1),
    })
    for question in questions:
        exam.add_question(question.pk, points)
    teacher.assign_students(exam.pk, [s.pk for s in students])
    exam.publish()
    exam.refresh_from_db()
    return exam


def correct_option(question):
    return question.options.get(is_correct=True)


def wrong_option(question):
    return question.options.filter(is_correct=False).first()
