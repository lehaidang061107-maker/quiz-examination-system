"""create business tables

Revision ID: 0001
Revises:
Create Date: 2026-11-12 22:09:30.565540

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("user_id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("full_name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column(
            "status",
            sa.String(10),
            nullable=False,
            server_default=sa.text("'ACTIVE'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.CheckConstraint(
            "length(btrim(full_name)) > 0",
            name="ck_users_full_name",
        ),
        sa.CheckConstraint(
            "email = lower(btrim(email)) AND length(email) > 0",
            name="ck_users_email_normalized",
        ),
        sa.CheckConstraint(
            "length(btrim(password_hash)) > 0",
            name="ck_users_password_hash",
        ),
        sa.CheckConstraint(
            "role IN ('ADMIN', 'TEACHER', 'STUDENT')",
            name="ck_users_role",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'LOCKED', 'DELETED')",
            name="ck_users_status",
        ),
    )

    op.create_table(
        "questions",
        sa.Column(
            "question_id",
            sa.BigInteger(),
            sa.Identity(),
            primary_key=True,
        ),
        sa.Column("teacher_id", sa.BigInteger(), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column(
            "question_type",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'SINGLE_CHOICE'"),
        ),
        sa.Column(
            "status",
            sa.String(10),
            nullable=False,
            server_default=sa.text("'DRAFT'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["teacher_id"],
            ["users.user_id"],
            name="fk_questions_teacher",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "question_type = 'SINGLE_CHOICE'",
            name="ck_questions_type",
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'ACTIVE', 'ARCHIVED')",
            name="ck_questions_status",
        ),
        sa.CheckConstraint(
            """
            status <> 'ACTIVE'
            OR (content IS NOT NULL AND length(btrim(content)) > 0)
            """,
            name="ck_questions_active_content",
        ),
    )

    op.create_index(
        "ix_questions_teacher_status",
        "questions",
        ["teacher_id", "status"],
    )

    op.create_table(
        "answer_options",
        sa.Column(
            "option_id",
            sa.BigInteger(),
            sa.Identity(),
            primary_key=True,
        ),
        sa.Column("question_id", sa.BigInteger(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column(
            "is_correct",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.question_id"],
            name="fk_options_question",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "question_id",
            "display_order",
            name="uq_options_display_order",
        ),
        sa.UniqueConstraint(
            "question_id",
            "option_id",
            name="uq_options_question_option",
        ),
        sa.CheckConstraint(
            "length(btrim(content)) > 0",
            name="ck_options_content",
        ),
        sa.CheckConstraint(
            "display_order > 0",
            name="ck_options_display_order",
        ),
    )
    op.create_table(
        "exams",
        sa.Column("exam_id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("teacher_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(10),
            nullable=False,
            server_default=sa.text("'DRAFT'"),
        ),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("opens_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closes_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "results_published",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["teacher_id"],
            ["users.user_id"],
            name="fk_exams_teacher",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "length(btrim(title)) > 0",
            name="ck_exams_title",
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'PUBLISHED', 'CLOSED', 'ARCHIVED')",
            name="ck_exams_status",
        ),
        sa.CheckConstraint(
            "duration_minutes IS NULL OR duration_minutes > 0",
            name="ck_exams_duration",
        ),
        sa.CheckConstraint(
            """
            opens_at IS NULL
            OR closes_at IS NULL
            OR closes_at > opens_at
            """,
            name="ck_exams_schedule",
        ),
        sa.CheckConstraint(
            "NOT results_published OR status IN ('CLOSED', 'ARCHIVED')",
            name="ck_exams_publication_status",
        ),
    )

    op.create_index(
        "ix_exams_teacher_status",
        "exams",
        ["teacher_id", "status"],
    )

    op.create_table(
        "exam_questions",
        sa.Column("exam_id", sa.BigInteger(), nullable=False),
        sa.Column("question_id", sa.BigInteger(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("points", sa.Numeric(12, 2), nullable=False),
        sa.PrimaryKeyConstraint(
            "exam_id",
            "question_id",
            name="pk_exam_questions",
        ),
        sa.ForeignKeyConstraint(
            ["exam_id"],
            ["exams.exam_id"],
            name="fk_exam_questions_exam",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.question_id"],
            name="fk_exam_questions_question",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "exam_id",
            "position",
            name="uq_exam_questions_position",
        ),
        sa.CheckConstraint(
            "position > 0",
            name="ck_exam_questions_position",
        ),
        sa.CheckConstraint(
            "points > 0 AND points <> 'NaN'::numeric",
            name="ck_exam_questions_points",
        ),
    )

    op.create_index(
        "ix_exam_questions_question",
        "exam_questions",
        ["question_id"],
    )

    op.create_table(
        "exam_participants",
        sa.Column("exam_id", sa.BigInteger(), nullable=False),
        sa.Column("student_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.PrimaryKeyConstraint(
            "exam_id",
            "student_id",
            name="pk_exam_participants",
        ),
        sa.ForeignKeyConstraint(
            ["exam_id"],
            ["exams.exam_id"],
            name="fk_exam_participants_exam",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.user_id"],
            name="fk_exam_participants_student",
            ondelete="RESTRICT",
        ),
    )

    op.create_index(
        "ix_participants_student_active_exam",
        "exam_participants",
        ["student_id", "is_active", "exam_id"],
    )

    op.create_table(
        "submissions",
        sa.Column("submission_id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("exam_id", sa.BigInteger(), nullable=False),
        sa.Column("student_id", sa.BigInteger(), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("status", sa.String(15), nullable=False, server_default=sa.text("'IN_PROGRESS'")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_saved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.ForeignKeyConstraint(
            ["exam_id", "student_id"],
            ["exam_participants.exam_id", "exam_participants.student_id"],
            name="fk_submissions_participant", ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("exam_id", "student_id", name="uq_submissions_participant"),
        sa.UniqueConstraint("submission_id", "exam_id", name="uq_submissions_exam"),
        sa.CheckConstraint("attempt_no = 1", name="ck_submissions_attempt"),
        sa.CheckConstraint("version >= 0", name="ck_submissions_version"),
        sa.CheckConstraint(
            "status IN ('IN_PROGRESS', 'SUBMITTED', 'GRADED')",
            name="ck_submissions_status",
        ),
        sa.CheckConstraint(
            """
            (status = 'IN_PROGRESS' AND submitted_at IS NULL)
            OR (status IN ('SUBMITTED', 'GRADED') AND submitted_at IS NOT NULL)
            """,
            name="ck_submissions_status_time",
        ),
        sa.CheckConstraint(
            """
            (deadline_at IS NULL OR deadline_at >= started_at)
            AND (last_saved_at IS NULL OR last_saved_at >= started_at)
            AND (submitted_at IS NULL OR submitted_at >= started_at)
            """,
            name="ck_submissions_time",
        ),
    )

    op.create_index(
        "ix_submissions_student_exam_status", "submissions",
        ["student_id", "exam_id", "status"],
    )
    op.create_index(
        "ix_submissions_pending_deadline", "submissions", ["deadline_at"],
        postgresql_where=sa.text("status = 'IN_PROGRESS'"),
    )
    op.create_index(
        "ix_submissions_grading_queue", "submissions", ["submitted_at"],
        postgresql_where=sa.text("status = 'SUBMITTED'"),
    )

    op.create_table(
        "submission_answers",
        sa.Column("submission_id", sa.BigInteger(), nullable=False),
        sa.Column("exam_id", sa.BigInteger(), nullable=False),
        sa.Column("question_id", sa.BigInteger(), nullable=False),
        sa.Column("selected_option_id", sa.BigInteger(), nullable=True),
        sa.Column("saved_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("submission_id", "question_id", name="pk_submission_answers"),
        sa.ForeignKeyConstraint(
            ["submission_id", "exam_id"],
            ["submissions.submission_id", "submissions.exam_id"],
            name="fk_answers_submission", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["exam_id", "question_id"],
            ["exam_questions.exam_id", "exam_questions.question_id"],
            name="fk_answers_exam_question", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["question_id", "selected_option_id"],
            ["answer_options.question_id", "answer_options.option_id"],
            name="fk_answers_option", ondelete="RESTRICT",
        ),
    )

    op.create_index(
        "ix_answers_exam_question", "submission_answers", ["exam_id", "question_id"],
    )
    op.create_index(
        "ix_answers_question_option", "submission_answers", ["question_id", "selected_option_id"],
    )

    op.create_table(
        "results",
        sa.Column("result_id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("submission_id", sa.BigInteger(), nullable=False),
        sa.Column("score", sa.Numeric(12, 2), nullable=False),
        sa.Column("max_score", sa.Numeric(12, 2), nullable=False),
        sa.Column("correct_count", sa.Integer(), nullable=False),
        sa.Column("total_questions", sa.Integer(), nullable=False),
        sa.Column("graded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["submission_id"], ["submissions.submission_id"],
            name="fk_results_submission", ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("submission_id", name="uq_results_submission"),
        sa.CheckConstraint(
            """
            max_score > 0 AND score >= 0 AND score <= max_score
            AND score <> 'NaN'::numeric AND max_score <> 'NaN'::numeric
            """,
            name="ck_results_score",
        ),
        sa.CheckConstraint(
            "total_questions > 0 AND correct_count >= 0 AND correct_count <= total_questions",
            name="ck_results_counts",
        ),
    )
    op.execute("""
        CREATE FUNCTION quiz_set_updated_at()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            NEW.updated_at = clock_timestamp();
            RETURN NEW;
        END;
        $$;
    """)

    for table in ("users", "questions", "exams"):
        op.execute(f"""
            CREATE TRIGGER {table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW
            EXECUTE FUNCTION quiz_set_updated_at();
        """)


def downgrade() -> None:
    op.drop_table("results")

    op.drop_index(
        "ix_answers_question_option",
        table_name="submission_answers",
    )
    op.drop_index(
        "ix_answers_exam_question",
        table_name="submission_answers",
    )
    op.drop_table("submission_answers")

    op.drop_index(
        "ix_submissions_grading_queue",
        table_name="submissions",
    )
    op.drop_index(
        "ix_submissions_pending_deadline",
        table_name="submissions",
    )
    op.drop_index(
        "ix_submissions_student_exam_status",
        table_name="submissions",
    )
    op.drop_table("submissions")

    op.drop_index(
        "ix_participants_student_active_exam",
        table_name="exam_participants",
    )
    op.drop_table("exam_participants")

    op.drop_index(
        "ix_exam_questions_question",
        table_name="exam_questions",
    )
    op.drop_table("exam_questions")

    op.drop_index("ix_exams_teacher_status", table_name="exams")
    op.drop_table("exams")

    op.drop_table("answer_options")

    op.drop_index("ix_questions_teacher_status", table_name="questions")
    op.drop_table("questions")

    op.drop_table("users")

    op.execute("DROP FUNCTION quiz_set_updated_at()")
