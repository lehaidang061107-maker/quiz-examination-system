"""Kiểm thử database: ràng buộc, dữ liệu mẫu, trigger, chỉ mục, quay lui migration.

Chạy: cd src && python manage.py test
Django tự tạo database test riêng (test_quiz_examination) rồi xóa sau khi chạy.
"""
from django.contrib.auth.hashers import check_password
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, connection, transaction
from django.test import TestCase, TransactionTestCase

from accounts.management.commands.seed_demo import seed_demo
from accounts.models import Role, User, UserStatus

PASSWORD = "integration-test-only-123"
TABLES = (
    "users", "questions", "answer_options", "exams", "exam_questions",
    "exam_participants", "submissions", "submission_answers", "results",
)

# 37 câu lệnh dữ liệu sai; database phải từ chối tất cả.
INVALID_SQL = (
    "UPDATE users SET email='teacher@demo.example' WHERE email='student1@demo.example'",
    "UPDATE users SET email=' Student1@demo.example ' WHERE email='student1@demo.example'",
    "UPDATE users SET role='GUEST' WHERE role='STUDENT'",
    "UPDATE users SET status='UNKNOWN' WHERE role='STUDENT'",
    "UPDATE users SET full_name=' '",
    "UPDATE questions SET status='UNKNOWN'",
    "UPDATE questions SET content=NULL WHERE status='ACTIVE'",
    "UPDATE questions SET teacher_id=9223372036854775807",
    "UPDATE answer_options SET display_order=0",
    "UPDATE answer_options SET content=' '",
    "UPDATE answer_options SET display_order=1 WHERE display_order=2",
    "UPDATE exam_questions SET points=0",
    "UPDATE exam_questions SET points='NaN'::numeric",
    "UPDATE exam_questions SET position=1 WHERE position=2",
    "UPDATE exams SET duration_minutes=0",
    "UPDATE exams SET opens_at=now(), closes_at=now()-interval '1 hour'",
    "UPDATE exams SET results_published=true WHERE status='DRAFT'",
    "UPDATE submissions SET attempt_no=2",
    "UPDATE submissions SET version=-1",
    "UPDATE submissions SET status='INVALID'",
    "UPDATE submissions SET submitted_at=NULL WHERE status='GRADED'",
    "UPDATE results SET score=max_score+1",
    "UPDATE results SET max_score=0",
    "UPDATE results SET score=-1",
    "UPDATE results SET score='NaN'::numeric",
    "UPDATE results SET correct_count=total_questions+1",
    "UPDATE results SET total_questions=0",
    "INSERT INTO results(submission_id,score,max_score,correct_count,total_questions) "
    "SELECT submission_id,score,max_score,correct_count,total_questions FROM results LIMIT 1",
    "INSERT INTO submissions(exam_id,student_id) SELECT exam_id,student_id FROM submissions LIMIT 1",
    "INSERT INTO submissions(exam_id,student_id) "
    "SELECT exam_id,(SELECT user_id FROM users WHERE role='ADMIN') FROM exams LIMIT 1",
    "INSERT INTO submission_answers SELECT * FROM submission_answers LIMIT 1",
    "DELETE FROM users WHERE role='TEACHER'",
    "DELETE FROM exam_participants WHERE (exam_id,student_id) IN (SELECT exam_id,student_id FROM submissions)",
    "DELETE FROM answer_options WHERE option_id IN (SELECT selected_option_id FROM submission_answers)",
    # Phương án có thật nhưng thuộc câu hỏi khác.
    "UPDATE submission_answers a SET selected_option_id="
    "(SELECT min(option_id) FROM answer_options WHERE question_id<>a.question_id)",
    # Câu hỏi có thật nhưng không nằm trong đề.
    "UPDATE submission_answers SET question_id=(SELECT question_id FROM questions WHERE status='DRAFT'), "
    "selected_option_id=NULL WHERE (submission_id, question_id) = "
    "(SELECT submission_id, question_id FROM submission_answers LIMIT 1)",
    # Đề có thật nhưng không phải đề của lượt làm bài.
    "UPDATE submission_answers SET exam_id=(SELECT min(exam_id) FROM exams WHERE status='DRAFT')",
)


def scalar(sql):
    with connection.cursor() as cursor:
        cursor.execute(sql)
        return cursor.fetchone()[0]


def rows(sql):
    with connection.cursor() as cursor:
        cursor.execute(sql)
        return cursor.fetchall()


class DatabaseRulesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        if not seed_demo(PASSWORD):
            raise AssertionError("Lần seed đầu tiên trên database mới phải tạo dữ liệu")

    def test_rejects_invalid_data(self):
        self.assertEqual(len(INVALID_SQL), 37)
        for sql in INVALID_SQL:
            with self.subTest(sql=sql):
                with self.assertRaises(IntegrityError):
                    with transaction.atomic():
                        with connection.cursor() as cursor:
                            # Khóa ngoại của Django được kiểm tra cuối giao dịch; kiểm tra ngay để bắt lỗi.
                            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
                            cursor.execute(sql)

    def test_seed_counts(self):
        expected = {
            "users": 4, "questions": 4, "answer_options": 9, "exams": 4, "exam_questions": 12,
            "exam_participants": 8, "submissions": 4, "submission_answers": 10, "results": 2,
        }
        self.assertEqual({t: scalar(f"SELECT count(*) FROM {t}") for t in TABLES}, expected)

    def test_seed_repeat_keeps_data_and_hashes_passwords(self):
        def snapshot():
            return {t: rows(f"SELECT * FROM {t} ORDER BY 1, 2") for t in TABLES}

        before = snapshot()
        self.assertFalse(seed_demo(PASSWORD))
        self.assertEqual(snapshot(), before)
        hashes = [h for (h,) in rows("SELECT password_hash FROM users")]
        self.assertEqual(len(set(hashes)), 4)
        self.assertTrue(all(h != PASSWORD and check_password(PASSWORD, h) for h in hashes))

    def test_seed_rejects_weak_password(self):
        for weak in ("short1", "onlyletters", "1234567890"):
            with self.subTest(password=weak), self.assertRaises(CommandError):
                seed_demo(weak)

    def test_demo_scores_match_answers(self):
        result_rows = rows("""
            SELECT r.score, r.max_score, r.correct_count, r.total_questions,
                sum(CASE WHEN o.is_correct THEN eq.points ELSE 0 END),
                sum(eq.points),
                count(*) FILTER (WHERE o.is_correct),
                count(*)
            FROM results r JOIN submissions s USING (submission_id)
            JOIN exam_questions eq ON eq.exam_id = s.exam_id
            LEFT JOIN submission_answers a ON a.submission_id = s.submission_id AND a.question_id = eq.question_id
            LEFT JOIN answer_options o ON o.option_id = a.selected_option_id
            GROUP BY r.result_id
        """)
        self.assertEqual(len(result_rows), 2)
        for row in result_rows:
            self.assertEqual(tuple(row[:4]), tuple(row[4:]))
        scores = sorted(str(s) for (s,) in rows("SELECT score FROM results"))
        self.assertEqual(scores, ["2.00", "6.00"])  # sinh viên hai 2/6, sinh viên một 6/6

    def test_allows_blank_answers_and_incomplete_drafts(self):
        with connection.cursor() as cursor:
            cursor.execute("UPDATE submission_answers SET selected_option_id=NULL")
            cursor.execute("UPDATE questions SET content=NULL WHERE status='DRAFT'")
            cursor.execute(
                "UPDATE exams SET duration_minutes=NULL, opens_at=NULL, closes_at=NULL WHERE status='DRAFT'"
            )

    def test_updated_at_triggers(self):
        for table, pk, column in (
            ("users", "user_id", "full_name"), ("questions", "question_id", "content"), ("exams", "exam_id", "title"),
        ):
            with self.subTest(table=table):
                before = dict(rows(f"SELECT {pk}, updated_at FROM {table}"))
                after = rows(f"UPDATE {table} SET {column}={column} RETURNING {pk}, updated_at")
                self.assertTrue(all(updated > before[key] for key, updated in after))

    def test_query_indexes_exist(self):
        with connection.cursor() as cursor:
            names = {
                name
                for table in TABLES
                for name, info in connection.introspection.get_constraints(cursor, table).items()
                if info["index"]
            }
        self.assertLessEqual(
            {"ix_exams_teacher_status", "ix_part_student_active_exam", "ix_sub_student_exam_status",
             "ix_sub_pending_deadline", "ix_submissions_grading_queue"},
            names,
        )


class UserModelTests(TestCase):
    def test_email_is_normalized_and_used_for_login(self):
        user = User.objects.create_user("  Mixed.Case@Example.COM ", "abc12345xyz", full_name="An")
        self.assertEqual(user.email, "mixed.case@example.com")
        self.assertEqual(User.objects.get_by_natural_key("MIXED.case@example.com "), user)
        self.assertEqual(user.role, Role.STUDENT)

    def test_only_active_accounts_are_active(self):
        user = User.objects.create_user("a@example.com", "abc12345xyz", full_name="An")
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        for status in (UserStatus.LOCKED, UserStatus.DELETED):
            user.status = status
            self.assertFalse(user.is_active)

    def test_only_admin_is_staff(self):
        admin = User.objects.create_user("ad@example.com", "abc12345xyz", full_name="Ad", role=Role.ADMIN)
        teacher = User.objects.create_user("t@example.com", "abc12345xyz", full_name="T", role=Role.TEACHER)
        admin.status = teacher.status = UserStatus.ACTIVE
        self.assertTrue(admin.is_staff)
        self.assertFalse(teacher.is_staff)


class MigrationReversibleTests(TransactionTestCase):
    """Quay lui toàn bộ migration rồi tạo lại được (thay cho alembic downgrade/upgrade)."""

    def test_migrate_zero_then_forward(self):
        call_command("migrate", "accounts", "zero", verbosity=0)
        existing = set(connection.introspection.table_names())
        self.assertFalse(existing & set(TABLES))
        self.assertIsNone(scalar("SELECT to_regprocedure('quiz_set_updated_at()')"))

        call_command("migrate", verbosity=0)
        self.assertLessEqual(set(TABLES), set(connection.introspection.table_names()))
        self.assertIsNotNone(scalar("SELECT to_regprocedure('quiz_set_updated_at()')"))
