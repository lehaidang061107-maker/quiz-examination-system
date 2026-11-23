"""S3-10: tạo dữ liệu đo tải (đề 50 câu x 4 lựa chọn, N sinh viên được giao đề).

Chạy trong container: docker compose -f compose.yaml -f compose.loadtest.yaml exec -T web-load \
    env LOAD_STUDENTS=500 python manage.py shell < scripts/loadtest/seed.py
"""
import os
from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.utils import timezone

from accounts.models import Role, User
from exams.models import ExamParticipant
from questions.models import AnswerOption, Question

N = int(os.environ.get("LOAD_STUDENTS", "500"))
PASSWORD = "LoadTest2026"
QUESTIONS = 50

teacher = User.objects.create_user("teacher@load.example", PASSWORD, full_name="Load Teacher", role=Role.TEACHER).as_role()
User.objects.create_user("admin@load.example", PASSWORD, full_name="Load Admin", role=Role.ADMIN)

hashed = make_password(PASSWORD)
User.objects.bulk_create(
    [User(full_name=f"Load Student {i}", email=f"load{i}@load.example", password=hashed, role=Role.STUDENT) for i in range(1, N + 1)]
)
students = list(User.objects.filter(role=Role.STUDENT).order_by("user_id"))

questions = []
for q in range(QUESTIONS):
    question = Question.objects.create(teacher=teacher, content=f"Câu {q + 1}: chọn đáp án đúng")
    AnswerOption.objects.bulk_create(
        [AnswerOption(question=question, content=f"Phương án {k + 1}", display_order=k + 1, is_correct=(k == 0)) for k in range(4)]
    )
    question.activate()
    questions.append(question)

now = timezone.now()
exam = teacher.create_exam(
    {"title": "Đề đo tải 50 câu", "duration_minutes": 60, "opens_at": now - timedelta(hours=1), "closes_at": now + timedelta(days=1)}
)
for question in questions:
    exam.add_question(question.pk, 0.2)
exam.publish()
teacher.assign_students(exam.pk, [s.pk for s in students])
print(f"OK exam_id={exam.pk} students={len(students)} questions={QUESTIONS} participants={ExamParticipant.objects.filter(exam=exam).count()}")
