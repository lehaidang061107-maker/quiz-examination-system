"""Tạo dữ liệu demo: python manage.py seed_demo

Chỉ chạy trên database phát triển hoặc demo. Không xóa hay ghi đè dữ liệu đã có:
chạy lại khi demo đã đủ thì giữ nguyên; demo dở dang thì dừng để tránh ghi đè.
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
    ("student1@demo.example", "Sinh viên một", Role.STUDENT),
    ("student2@demo.example", "Sinh viên hai", Role.STUDENT),
)
EMAILS = tuple(a[0] for a in ACCOUNTS)
MARKER = "S3-21 demo v1"
EXAM_TITLES = (
    "[Demo S3-21] Đề nháp",
    "[Demo S3-21] Đề đang mở",
    "[Demo S3-21] Đề chờ chấm",
    "[Demo S3-21] Đề đã công bố",
)
QUESTIONS = (
    ("Khóa chính dùng để làm gì?", ("Định danh duy nhất bản ghi", "Lưu mật khẩu", "Sắp xếp giao diện")),
    ("PostgreSQL là hệ quản trị nào?", ("Cơ sở dữ liệu quan hệ", "Trình soạn thảo", "Trình duyệt")),
    ("Khóa ngoại dùng để làm gì?", ("Tham chiếu dữ liệu ở bảng liên quan", "Mã hóa mật khẩu", "Tạo giao diện")),
)
POINTS = Decimal("2.00")
ADVISORY_LOCK_ID = 3212026  # tuần tự hóa hai lần chạy đồng thời


def seed_demo(password):
    """Tạo bộ demo. Trả về True nếu vừa tạo, False nếu bộ demo đã có đủ."""
    try:
        validate_password(password)
    except ValidationError as exc:
        raise CommandError("DEMO_PASSWORD chưa hợp lệ: " + " ".join(exc.messages)) from exc

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [ADVISORY_LOCK_ID])

        existing = dict(User.objects.filter(email__in=EMAILS).values_list("email", "user_id"))
        if existing:
            complete = len(existing) == len(EMAILS) and Exam.objects.filter(
                teacher_id=existing[EMAILS[1]], description=MARKER, title__in=EXAM_TITLES
            ).count() == len(EXAM_TITLES)
            if complete:
                return False
            raise CommandError("Email demo đã tồn tại hoặc dữ liệu demo chưa đủ; không ghi đè.")

        users = [User.objects.create_user(email, password, full_name=name, role=role) for email, name, role in ACCOUNTS]
        teacher, student1, student2 = users[1:]

        questions, options = [], []
        for content, choices in QUESTIONS:
            question = Question.objects.create(teacher=teacher, content=content)
            options.append([
                AnswerOption.objects.create(question=question, content=c, display_order=i + 1, is_correct=(i == 0))
                for i, c in enumerate(choices)
            ])
            # Kích hoạt sau khi đã có đủ phương án và đúng một đáp án đúng.
            Question.objects.filter(pk=question.pk).update(status=QuestionStatus.ACTIVE)
            questions.append(question)
        Question.objects.create(teacher=teacher, content=None)  # câu nháp chưa hoàn chỉnh

        now = timezone.now()
        exams = []
        for title in EXAM_TITLES:
            exam = Exam.objects.create(teacher=teacher, title=title, description=MARKER, duration_minutes=30)
            for i, question in enumerate(questions):
                ExamQuestion.objects.create(exam=exam, question=question, position=i + 1, points=POINTS)
            for student in (student1, student2):
                ExamParticipant.objects.create(exam=exam, student=student)
            if title != EXAM_TITLES[0]:
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
        return True


class Command(BaseCommand):
    help = "Tạo dữ liệu demo (4 tài khoản, câu hỏi, đề thi, bài làm, kết quả). Mật khẩu lấy từ DEMO_PASSWORD trong .env."

    def handle(self, *args, **options):
        created = seed_demo(os.getenv("DEMO_PASSWORD", ""))
        if created:
            self.stdout.write(self.style.SUCCESS("Đã tạo dữ liệu demo."))
        else:
            self.stdout.write("Demo đã tồn tại; giữ nguyên dữ liệu và mật khẩu.")
