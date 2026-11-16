"""Khóa ngoại nhiều cột: Django chỉ hỗ trợ khóa ngoại một cột nên khai báo bằng SQL.

- submissions (exam_id, student_id) -> exam_participants: chỉ sinh viên được giao đề mới có lượt làm.
- submission_answers (submission_id, exam_id) -> submissions: đáp án đúng đề của lượt làm.
- submission_answers (exam_id, question_id) -> exam_questions: câu trả lời phải là câu có trong đề.
- submission_answers (question_id, selected_option_id) -> answer_options: đáp án phải thuộc đúng câu.
"""
from django.db import migrations

SQL = """
ALTER TABLE submissions
    ADD CONSTRAINT fk_submissions_participant FOREIGN KEY (exam_id, student_id)
        REFERENCES exam_participants (exam_id, student_id) ON DELETE RESTRICT;
ALTER TABLE submission_answers
    ADD CONSTRAINT fk_answers_submission FOREIGN KEY (submission_id, exam_id)
        REFERENCES submissions (submission_id, exam_id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_answers_exam_question FOREIGN KEY (exam_id, question_id)
        REFERENCES exam_questions (exam_id, question_id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_answers_option FOREIGN KEY (question_id, selected_option_id)
        REFERENCES answer_options (question_id, option_id) ON DELETE RESTRICT;
"""

REVERSE_SQL = """
ALTER TABLE submission_answers
    DROP CONSTRAINT fk_answers_option,
    DROP CONSTRAINT fk_answers_exam_question,
    DROP CONSTRAINT fk_answers_submission;
ALTER TABLE submissions DROP CONSTRAINT fk_submissions_participant;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("attempts", "0001_initial"),
        ("exams", "0001_initial"),
        ("questions", "0001_initial"),
    ]
    operations = [migrations.RunSQL(SQL, REVERSE_SQL)]
