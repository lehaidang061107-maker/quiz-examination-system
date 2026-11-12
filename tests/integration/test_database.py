"""Run: python -m unittest discover -s tests/integration -v.

Uses a UUID-named schema in the configured local PostgreSQL database.
No migration/downgrade is run against the application's public schema.
"""
import sys
import unittest
import uuid
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from database.seeds.seed_demo import TABLE_NAMES, get_engine, seed_demo

PASSWORD = "local-integration-test-only"
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
    "INSERT INTO results(submission_id,score,max_score,correct_count,total_questions) SELECT submission_id,score,max_score,correct_count,total_questions FROM results LIMIT 1",
    "INSERT INTO submissions(exam_id,student_id) SELECT exam_id,student_id FROM submissions LIMIT 1",
    "INSERT INTO submissions(exam_id,student_id) SELECT exam_id,(SELECT user_id FROM users WHERE role='ADMIN') FROM exams LIMIT 1",
    "INSERT INTO submission_answers SELECT * FROM submission_answers LIMIT 1",
    "DELETE FROM users WHERE role='TEACHER'",
    "DELETE FROM exam_participants WHERE (exam_id,student_id) IN (SELECT exam_id,student_id FROM submissions)",
    "DELETE FROM answer_options WHERE option_id IN (SELECT selected_option_id FROM submission_answers)",
    # Valid option ID, but from the wrong question.
    "UPDATE submission_answers a SET selected_option_id=(SELECT min(option_id) FROM answer_options WHERE question_id<>a.question_id)",
    # Valid question ID, but not included in this exam.
    "UPDATE submission_answers SET question_id=(SELECT question_id FROM questions WHERE status='DRAFT'), selected_option_id=NULL",
    # Valid exam ID, but not the exam of this submission.
    "UPDATE submission_answers SET exam_id=(SELECT min(exam_id) FROM exams WHERE status='DRAFT')",
)


class DatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = get_engine()
        cls.addClassCleanup(cls.admin.dispose)
        cls.schema = "s321_test_" + uuid.uuid4().hex
        with cls.admin.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA "{cls.schema}"'))
        cls.addClassCleanup(cls.drop_schema)
        url = cls.admin.url.update_query_dict({"options": f"-csearch_path={cls.schema}"})
        cls.engine = create_engine(url)
        cls.addClassCleanup(cls.engine.dispose)
        cls.config = Config(str(ROOT / "alembic.ini"))
        cls.migrate("head")
        cls.tables_after_upgrade = set(inspect(cls.engine).get_table_names())
        cls.migrate("base", downgrade=True)
        cls.tables_after_downgrade = set(inspect(cls.engine).get_table_names())
        with cls.engine.connect() as conn:
            cls.function_after_downgrade = conn.scalar(text(
                "SELECT to_regprocedure('quiz_set_updated_at()')"
            ))
        cls.migrate("head")
        if not seed_demo(cls.engine, PASSWORD):
            raise AssertionError("First seed in a new schema must create data")

    @classmethod
    def drop_schema(cls):
        # Only the schema whose random name was created above can be removed here.
        with cls.admin.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{cls.schema}" CASCADE'))

    @classmethod
    def migrate(cls, revision, downgrade=False):
        with cls.engine.begin() as conn:
            cls.config.attributes["connection"] = conn
            try:
                (command.downgrade if downgrade else command.upgrade)(cls.config, revision)
            finally:
                cls.config.attributes.pop("connection", None)

    def setUp(self):
        self.conn = self.engine.connect()
        self.addCleanup(self.conn.close)
        transaction = self.conn.begin()
        self.addCleanup(transaction.rollback)

    def test_migration_upgrade_downgrade_upgrade(self):
        self.assertEqual(self.tables_after_upgrade, set(TABLE_NAMES) | {"alembic_version"})
        self.assertEqual(self.tables_after_downgrade, {"alembic_version"})
        self.assertIsNone(self.function_after_downgrade)
        self.assertEqual(set(inspect(self.conn).get_table_names()), self.tables_after_upgrade)
        self.assertEqual(self.conn.scalar(text("SELECT version_num FROM alembic_version")), "0001")

    def test_constraints(self):
        for sql in INVALID_SQL:
            with self.subTest(sql=sql):
                with self.assertRaises(IntegrityError):
                    with self.conn.begin_nested():
                        self.conn.execute(text(sql))

    def test_seed_repeat_and_password_hashes(self):
        def snapshot():
            return {name: self.conn.execute(text(f'SELECT * FROM {name} ORDER BY 1,2')).all()
                    for name in TABLE_NAMES}
        before = snapshot()
        self.assertFalse(seed_demo(self.engine, PASSWORD))
        self.assertEqual(snapshot(), before)
        hashes = self.conn.execute(text("SELECT password_hash FROM users")).scalars().all()
        self.assertEqual(len(hashes), 4)
        self.assertEqual(len(set(hashes)), 4)
        self.assertTrue(all(h != PASSWORD and check_password_hash(h, PASSWORD) for h in hashes))

    def test_demo_scores_match_answers(self):
        rows = self.conn.execute(text('''
            SELECT r.score,r.max_score,r.correct_count,r.total_questions,
                sum(CASE WHEN o.is_correct THEN eq.points ELSE 0 END) AS expected_score,
                sum(eq.points) AS expected_max,
                count(*) FILTER (WHERE o.is_correct) AS expected_correct,
                count(*) AS expected_total
            FROM results r JOIN submissions s USING(submission_id)
            JOIN exam_questions eq ON eq.exam_id=s.exam_id
            LEFT JOIN submission_answers a ON a.submission_id=s.submission_id AND a.question_id=eq.question_id
            LEFT JOIN answer_options o ON o.option_id=a.selected_option_id
            GROUP BY r.result_id
        ''')).all()
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertEqual(tuple(row[:4]), tuple(row[4:]))

    def test_null_answers_and_incomplete_drafts(self):
        self.conn.execute(text("UPDATE submission_answers SET selected_option_id=NULL"))
        self.conn.execute(text("UPDATE questions SET content=NULL WHERE status='DRAFT'"))
        self.conn.execute(text("UPDATE exams SET duration_minutes=NULL,opens_at=NULL,closes_at=NULL WHERE status='DRAFT'"))

    def test_updated_at_triggers(self):
        for table, column in (("users", "full_name"), ("questions", "content"), ("exams", "title")):
            with self.subTest(table=table):
                before = dict(self.conn.execute(text(f'SELECT {inspect(self.conn).get_pk_constraint(table)["constrained_columns"][0]}, updated_at FROM {table}')).all())
                pk = inspect(self.conn).get_pk_constraint(table)["constrained_columns"][0]
                rows = self.conn.execute(text(f'UPDATE {table} SET {column}={column} RETURNING {pk},updated_at')).all()
                self.assertTrue(all(updated > before[record_id] for record_id, updated in rows))

    def test_query_indexes(self):
        indexes = {i["name"] for table in TABLE_NAMES for i in inspect(self.conn).get_indexes(table)}
        self.assertTrue({"ix_exams_teacher_status", "ix_participants_student_active_exam",
                         "ix_submissions_student_exam_status", "ix_submissions_pending_deadline",
                         "ix_submissions_grading_queue"} <= indexes)

    def test_seed_rejects_too_short_password(self):
        with self.assertRaises(ValueError):
            seed_demo(self.engine, "short")


if __name__ == "__main__":
    unittest.main()
