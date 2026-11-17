"""Tạo dữ liệu demo: python manage.py seed_demo

Chỉ chạy trên database phát triển hoặc demo. Chạy lại bao nhiêu lần cũng được: phần nào đã có
thì giữ nguyên (không thêm trùng, không đổi mật khẩu), phần nào còn thiếu thì tạo thêm.
Bộ đề thi demo dở dang (thiếu đề) thì dừng để tránh ghi đè.
"""
import os
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from accounts.models import Role, User
from attempts.models import Submission, SubmissionAnswer, SubmissionStatus
from exams.models import Exam, ExamParticipant, ExamQuestion, ExamStatus
from questions.models import AnswerOption, Question, QuestionStatus
from results.models import Result

ACCOUNTS = (
    ("admin@demo.example", "Quản trị demo", Role.ADMIN),
    ("teacher@demo.example", "Giảng viên demo", Role.TEACHER),
    ("teacher2@demo.example", "Giảng viên hai", Role.TEACHER),
    ("student1@demo.example", "Sinh viên một", Role.STUDENT),
    ("student2@demo.example", "Sinh viên hai", Role.STUDENT),
    ("student3@demo.example", "Sinh viên ba", Role.STUDENT),
)
EMAILS = tuple(a[0] for a in ACCOUNTS)
MARKER = "S3-21 demo v1"
EXAM_TITLES = (
    "[Demo S3-21] Đề nháp",
    "[Demo S3-21] Đề đang mở",
    "[Demo S3-21] Đề chờ chấm",
    "[Demo S3-21] Đề đã công bố",
)
# Ngân hàng câu hỏi: (email giảng viên, nội dung, các lựa chọn; lựa chọn đầu tiên là đáp án đúng).
QUESTIONS = (
    ("teacher@demo.example", "Khóa chính dùng để làm gì?",
     ("Định danh duy nhất bản ghi", "Lưu mật khẩu", "Sắp xếp giao diện")),
    ("teacher@demo.example", "PostgreSQL là hệ quản trị nào?",
     ("Cơ sở dữ liệu quan hệ", "Trình soạn thảo", "Trình duyệt")),
    ("teacher@demo.example", "Khóa ngoại dùng để làm gì?",
     ("Tham chiếu dữ liệu ở bảng liên quan", "Mã hóa mật khẩu", "Tạo giao diện")),
    ("teacher2@demo.example", "Mô hình MVC gồm những thành phần nào?",
     ("Model, View, Controller", "Module, Version, Client", "Main, Value, Config")),
    ("teacher2@demo.example", "Sơ đồ Use Case mô tả điều gì?",
     ("Chức năng hệ thống theo góc nhìn người dùng", "Cấu trúc bảng dữ liệu", "Thứ tự gói tin mạng")),
)
EXAM_QUESTION_COUNT = 3  # 3 câu đầu (của teacher@) được đưa vào các đề demo
POINTS = Decimal("2.00")
ADVISORY_LOCK_ID = 3212026  # tuần tự hóa hai lần chạy đồng thời


class _Seeder:
    def __init__(self, password):
        self.password = password
        self.created = 0

    def users(self):
        users = {}
        for email, name, role in ACCOUNTS:
            user = User.objects.filter(email=email).first()
            if user is None:
                user = User.objects.create_user(email, self.password, full_name=name, role=role)
                self.created += 1
            elif user.role != role:
                raise CommandError(f"Email demo {email} đã có với vai trò {user.role}; không ghi đè.")
            users[email] = user
        return users

    def questions(self, users):
        """Trả về [(câu hỏi, [phương án theo thứ tự])] theo thứ tự QUESTIONS."""
        bank = []
        for email, content, choices in QUESTIONS:
            teacher = users[email]
            question = Question.objects.filter(teacher=teacher, content=content).order_by("pk").first()
            if question is None:
                question = Question.objects.create(teacher=teacher, content=content)
                for i, choice in enumerate(choices):
                    AnswerOption.objects.create(
                        question=question, content=choice, display_order=i + 1, is_correct=(i == 0)
                    )
                # Kích hoạt sau khi đã có đủ phương án và đúng một đáp án đúng.
                Question.objects.filter(pk=question.pk).update(status=QuestionStatus.ACTIVE)
                self.created += 1
            bank.append((question, list(question.options.order_by("display_order"))))
        # Mỗi giảng viên có một câu nháp chưa hoàn chỉnh.
        for teacher in {users[email] for email, _, _ in QUESTIONS}:
            if not Question.objects.filter(teacher=teacher, content__isnull=True).exists():
                Question.objects.create(teacher=teacher, content=None)
                self.created += 1
        return bank

    def exams(self, users, bank):
        teacher = users["teacher@demo.example"]
        existing = Exam.objects.filter(teacher=teacher, description=MARKER, title__in=EXAM_TITLES).count()
        if existing == len(EXAM_TITLES):
            return
        if existing:
            raise CommandError("Bộ đề demo đang dở dang (thiếu đề); không ghi đè.")

        student1, student2, student3 = (users[f"student{i}@demo.example"] for i in (1, 2, 3))
        questions = [q for q, _ in bank[:EXAM_QUESTION_COUNT]]
        options = [o for _, o in bank[:EXAM_QUESTION_COUNT]]
        now = timezone.now()
        exams = []
        for index, title in enumerate(EXAM_TITLES):
            exam = Exam.objects.create(teacher=teacher, title=title, description=MARKER, duration_minutes=30)
            for i, question in enumerate(questions):
                ExamQuestion.objects.create(exam=exam, question=question, position=i + 1, points=POINTS)
            students = (student1, student2, student3) if index < 2 else (student1, student2)
            for student in students:
                ExamParticipant.objects.create(exam=exam, student=student)
            if index > 0:
                Exam.objects.filter(pk=exam.pk).update(
                    status=ExamStatus.PUBLISHED, opens_at=now - timedelta(days=1), closes_at=now + timedelta(days=30)
                )
            exams.append(exam)

        # (đề, sinh viên, trạng thái, chỉ số phương án đã chọn cho từng câu; None = bỏ chọn)
        scenarios = (
            (exams[1], student1, SubmissionStatus.IN_PROGRESS, (0,)),
            (exams[2], student1, SubmissionStatus.SUBMITTED, (0, 0, 0)),
            (exams[3], student1, SubmissionStatus.GRADED, (0, 0, 0)),
            (exams[3], student2, SubmissionStatus.GRADED, (0, 1, None)),
        )
        for exam, student, status, answers in scenarios:
            in_progress = status == SubmissionStatus.IN_PROGRESS
            started = now if in_progress else now - timedelta(minutes=20)
            saved = started if in_progress else started + timedelta(minutes=1)
            submission = Submission.objects.create(
                exam=exam, student=student, started_at=started,
                deadline_at=started + timedelta(minutes=30), last_saved_at=saved, version=1,
            )
            for i, answer in enumerate(answers):
                SubmissionAnswer.objects.create(
                    submission=submission, exam=exam, question=questions[i],
                    selected_option=None if answer is None else options[i][answer], saved_at=saved,
                )
            if not in_progress:
                Submission.objects.filter(pk=submission.pk).update(
                    status=SubmissionStatus.SUBMITTED, submitted_at=now - timedelta(minutes=5)
                )
            if status == SubmissionStatus.GRADED:
                correct = sum(a == 0 for a in answers)
                Result.objects.create(
                    submission=submission, score=POINTS * correct, max_score=POINTS * len(questions),
                    correct_count=correct, total_questions=len(questions), graded_at=now,
                )
                Submission.objects.filter(pk=submission.pk).update(status=SubmissionStatus.GRADED)

        Exam.objects.filter(pk__in=[e.pk for e in exams[2:]]).update(status=ExamStatus.CLOSED, closes_at=now)
        Exam.objects.filter(pk=exams[3].pk).update(results_published=True)
        self.created += len(exams)


def seed_demo(password):
    """Tạo phần demo còn thiếu. Trả về True nếu có tạo thêm gì, False nếu bộ demo đã đủ."""
    try:
        validate_password(password)
    except ValidationError as exc:
        raise CommandError("DEMO_PASSWORD chưa hợp lệ: " + " ".join(exc.messages)) from exc
    seeder = _Seeder(password)
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [ADVISORY_LOCK_ID])
        users = seeder.users()
        bank = seeder.questions(users)
        seeder.exams(users, bank)
    return seeder.created > 0


class Command(BaseCommand):
    help = ("Tạo dữ liệu demo (1 admin, 2 giảng viên, 3 sinh viên, câu hỏi, đề thi, bài làm, kết quả). "
            "Mật khẩu lấy từ DEMO_PASSWORD trong .env. Chạy lại không tạo trùng.")

    def handle(self, *args, **options):
        created = seed_demo(os.getenv("DEMO_PASSWORD", ""))
        if created:
            self.stdout.write(self.style.SUCCESS("Đã tạo dữ liệu demo."))
        else:
            self.stdout.write("Demo đã tồn tại; giữ nguyên dữ liệu và mật khẩu.")
