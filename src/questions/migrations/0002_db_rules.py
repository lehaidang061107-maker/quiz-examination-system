"""Ràng buộc viết bằng SQL (btrim) và trigger updated_at cho bảng questions."""
from django.db import migrations

SQL = """
ALTER TABLE questions
    ADD CONSTRAINT ck_questions_active_content
        CHECK (status <> 'ACTIVE' OR (content IS NOT NULL AND length(btrim(content)) > 0));
ALTER TABLE answer_options
    ADD CONSTRAINT ck_options_content CHECK (length(btrim(content)) > 0);

CREATE TRIGGER questions_updated_at BEFORE UPDATE ON questions
    FOR EACH ROW EXECUTE FUNCTION quiz_set_updated_at();
"""

REVERSE_SQL = """
DROP TRIGGER questions_updated_at ON questions;
ALTER TABLE answer_options DROP CONSTRAINT ck_options_content;
ALTER TABLE questions DROP CONSTRAINT ck_questions_active_content;
"""


class Migration(migrations.Migration):
    dependencies = [("questions", "0001_initial"), ("accounts", "0002_db_rules")]
    operations = [migrations.RunSQL(SQL, REVERSE_SQL)]
