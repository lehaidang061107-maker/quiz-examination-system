"""Ràng buộc viết bằng SQL (btrim, chặn NaN) và trigger updated_at cho bảng exams."""
from django.db import migrations

SQL = """
ALTER TABLE exams
    ADD CONSTRAINT ck_exams_title CHECK (length(btrim(title)) > 0);
-- PostgreSQL coi NaN lớn hơn mọi số, nên phải chặn riêng.
ALTER TABLE exam_questions
    ADD CONSTRAINT ck_exam_questions_points CHECK (points > 0 AND points <> 'NaN'::numeric);

CREATE TRIGGER exams_updated_at BEFORE UPDATE ON exams
    FOR EACH ROW EXECUTE FUNCTION quiz_set_updated_at();
"""

REVERSE_SQL = """
DROP TRIGGER exams_updated_at ON exams;
ALTER TABLE exam_questions DROP CONSTRAINT ck_exam_questions_points;
ALTER TABLE exams DROP CONSTRAINT ck_exams_title;
"""


class Migration(migrations.Migration):
    dependencies = [("exams", "0001_initial"), ("accounts", "0002_db_rules")]
    operations = [migrations.RunSQL(SQL, REVERSE_SQL)]
