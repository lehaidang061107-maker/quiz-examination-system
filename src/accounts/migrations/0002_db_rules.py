"""Ràng buộc và trigger viết bằng SQL vì Django không biểu diễn được (btrim, trigger).

Hàm quiz_set_updated_at() dùng chung cho users, questions, exams: tự cập nhật updated_at
mỗi khi sửa dòng, kể cả khi sửa bằng QuerySet.update() hoặc SQL trực tiếp.
"""
from django.db import migrations

SQL = """
ALTER TABLE users
    ADD CONSTRAINT ck_users_full_name CHECK (length(btrim(full_name)) > 0),
    ADD CONSTRAINT ck_users_email_normalized CHECK (email = lower(btrim(email)) AND length(email) > 0),
    ADD CONSTRAINT ck_users_password_hash CHECK (length(btrim(password_hash)) > 0);

CREATE FUNCTION quiz_set_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = clock_timestamp();
    RETURN NEW;
END;
$$;

CREATE TRIGGER users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION quiz_set_updated_at();
"""

REVERSE_SQL = """
DROP TRIGGER users_updated_at ON users;
DROP FUNCTION quiz_set_updated_at();
ALTER TABLE users
    DROP CONSTRAINT ck_users_password_hash,
    DROP CONSTRAINT ck_users_email_normalized,
    DROP CONSTRAINT ck_users_full_name;
"""


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]
    operations = [migrations.RunSQL(SQL, REVERSE_SQL)]
