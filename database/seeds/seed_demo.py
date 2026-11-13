"""Tạo dữ liệu demo S3-21: python database/seeds/seed_demo.py.

Chỉ chạy trên database phát triển. Không xóa/ghi đè dữ liệu đã có.
"""
import os
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import MetaData, create_engine, func, select, text
from sqlalchemy.engine import URL
from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parents[2]
EMAILS = (
    "admin@demo.example",
    "teacher@demo.example",
    "student1@demo.example",
    "student2@demo.example",
)
MARKER = "S3-21 demo v1"
EXAM_TITLES = (
    "[Demo S3-21] Đề nháp",
    "[Demo S3-21] Đề đang mở",
    "[Demo S3-21] Đề chờ chấm",
    "[Demo S3-21] Đề đã công bố",
)
TABLE_NAMES = (
    "users", "questions", "answer_options", "exams", "exam_questions",
    "exam_participants", "submissions", "submission_answers", "results",
)


def get_engine():
    load_dotenv(ROOT / ".env")
    return create_engine(URL.create(
        "postgresql+psycopg",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "55433")),
        database=os.environ["POSTGRES_DB"],
    ), pool_pre_ping=True)


def seed_demo(engine, password):
    if len(password) < 6:
        raise ValueError("Đặt DEMO_PASSWORD tối thiểu 6 ký tự trong .env")

    with engine.begin() as conn:
        # Giữ toàn bộ seed trong một giao dịch; tuần tự hóa hai lần chạy đồng thời.
        conn.execute(text("SELECT pg_advisory_xact_lock(3212026)"))
        if conn.scalar(text("SELECT version_num FROM alembic_version")) != "0001":
            raise RuntimeError("Seed v1 yêu cầu schema 0001; kiểm tra migration trước")
        metadata = MetaData()
        metadata.reflect(bind=conn, only=TABLE_NAMES)
        tables = metadata.tables
        users, exams = tables["users"], tables["exams"]
        existing = conn.execute(select(users.c.email, users.c.user_id).where(
            users.c.email.in_(EMAILS)
        )).all()
        if existing:
            ids = dict(existing)
            complete = len(ids) == len(EMAILS)
            if complete:
                count = conn.scalar(select(func.count()).select_from(exams).where(
                    exams.c.teacher_id == ids[EMAILS[1]],
                    exams.c.description == MARKER,
                    exams.c.title.in_(EXAM_TITLES),
                ))
                complete = count == len(EXAM_TITLES)
            if complete:
                return False
            raise RuntimeError("Email demo đã tồn tại hoặc dữ liệu demo chưa đủ; không ghi đè")

        def insert(name, **values):
            table = tables[name]
            result = conn.execute(table.insert().values(**values))
            return result.inserted_primary_key[0]

        user_ids = []
        for email, name, role in zip(EMAILS,
                ("Quản trị demo", "Giảng viên demo", "Sinh viên một", "Sinh viên hai"),
                ("ADMIN", "TEACHER", "STUDENT", "STUDENT")):
            user_ids.append(insert("users", full_name=name, email=email,
                                   password_hash=generate_password_hash(password, method="scrypt"),
                                   role=role))
        teacher, student1, student2 = user_ids[1:]

        questions, options = [], []
        for content, choices in (
            ("Khóa chính dùng để làm gì?", ("Định danh duy nhất bản ghi", "Lưu mật khẩu", "Sắp xếp giao diện")),
            ("PostgreSQL là hệ quản trị nào?", ("Cơ sở dữ liệu quan hệ", "Trình soạn thảo", "Trình duyệt")),
            ("Khóa ngoại dùng để làm gì?", ("Tham chiếu dữ liệu ở bảng liên quan", "Mã hóa mật khẩu", "Tạo giao diện")),
        ):
            qid = insert("questions", teacher_id=teacher, content=content)
            questions.append(qid)
            options.append([
                insert("answer_options", question_id=qid, content=choice,
                       display_order=i + 1, is_correct=(i == 0))
                for i, choice in enumerate(choices)
            ])
            # Kích hoạt sau khi đã có đủ phương án và đúng một đáp án đúng.
            conn.execute(tables["questions"].update().where(
                tables["questions"].c.question_id == qid
            ).values(status="ACTIVE"))
        insert("questions", teacher_id=teacher, content=None)  # DRAFT chưa hoàn chỉnh

        now = conn.scalar(select(func.now()))
        exam_ids = []
        for title in EXAM_TITLES:
            exam = insert("exams", teacher_id=teacher, title=title,
                          description=MARKER, duration_minutes=30)
            exam_ids.append(exam)
            for i, qid in enumerate(questions):
                insert("exam_questions", exam_id=exam, question_id=qid,
                       position=i + 1, points=Decimal("2.00"))
            for student in (student1, student2):
                insert("exam_participants", exam_id=exam, student_id=student)
            if title != EXAM_TITLES[0]:
                conn.execute(exams.update().where(exams.c.exam_id == exam).values(
                    status="PUBLISHED", opens_at=now - timedelta(days=1),
                    closes_at=now + timedelta(days=30),
                ))

        scenarios = (
            (exam_ids[1], student1, "IN_PROGRESS", (0,)),
            (exam_ids[2], student1, "SUBMITTED", (0, 0, 0)),
            (exam_ids[3], student1, "GRADED", (0, 0, 0)),
            (exam_ids[3], student2, "GRADED", (0, 1, None)),
        )
        for exam, student, status, answers in scenarios:
            started = now if status == "IN_PROGRESS" else now - timedelta(minutes=20)
            submitted = None if status == "IN_PROGRESS" else now - timedelta(minutes=5)
            submission = insert(
                "submissions", exam_id=exam, student_id=student,
                started_at=started, deadline_at=started + timedelta(minutes=30),
                last_saved_at=started + timedelta(minutes=1) if submitted else started,
                version=1,
            )
            for i, answer in enumerate(answers):
                insert("submission_answers", submission_id=submission, exam_id=exam,
                       question_id=questions[i],
                       selected_option_id=None if answer is None else options[i][answer],
                       saved_at=started + timedelta(minutes=1) if submitted else started)
            if status != "IN_PROGRESS":
                conn.execute(tables["submissions"].update().where(
                    tables["submissions"].c.submission_id == submission
                ).values(status="SUBMITTED", submitted_at=submitted))
            if status == "GRADED":
                correct = sum(answer == 0 for answer in answers)
                insert("results", submission_id=submission,
                       score=Decimal("2.00") * correct, max_score=Decimal("6.00"),
                       correct_count=correct, total_questions=3, graded_at=now)
                conn.execute(tables["submissions"].update().where(
                    tables["submissions"].c.submission_id == submission
                ).values(status="GRADED"))

        conn.execute(exams.update().where(exams.c.exam_id.in_(exam_ids[2:])).values(
            status="CLOSED", closes_at=now,
        ))
        conn.execute(exams.update().where(exams.c.exam_id == exam_ids[3]).values(
            results_published=True,
        ))
        return True


def main():
    engine = get_engine()
    try:
        changed = seed_demo(engine, os.getenv("DEMO_PASSWORD", ""))
        print("Đã tạo dữ liệu demo S3-21." if changed else "Demo đã tồn tại; giữ nguyên dữ liệu và mật khẩu.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
