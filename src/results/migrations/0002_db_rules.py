"""Ràng buộc điểm viết bằng SQL vì cần chặn NaN (PostgreSQL coi NaN lớn hơn mọi số)."""
from django.db import migrations

SQL = """
ALTER TABLE results
    ADD CONSTRAINT ck_results_score CHECK (
        max_score > 0 AND score >= 0 AND score <= max_score
        AND score <> 'NaN'::numeric AND max_score <> 'NaN'::numeric
    );
"""

REVERSE_SQL = "ALTER TABLE results DROP CONSTRAINT ck_results_score;"


class Migration(migrations.Migration):
    dependencies = [("results", "0001_initial")]
    operations = [migrations.RunSQL(SQL, REVERSE_SQL)]
