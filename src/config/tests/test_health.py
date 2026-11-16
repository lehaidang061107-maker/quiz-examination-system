from unittest import mock

from django.conf import settings
from django.db import DatabaseError
from django.test import TestCase
from django.urls import reverse


class HealthTests(TestCase):
    def test_health_ok_when_database_reachable(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "ok"})

    def test_health_503_when_database_down(self):
        with mock.patch("config.views.connection.cursor", side_effect=DatabaseError):
            response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["database"], "error")

    def test_health_rejects_post(self):
        self.assertEqual(self.client.post(reverse("health")).status_code, 405)


class SettingsTests(TestCase):
    def test_uses_postgresql(self):
        self.assertEqual(settings.DATABASES["default"]["ENGINE"], "django.db.backends.postgresql")

    def test_session_expires_after_30_minutes_of_inactivity(self):
        self.assertEqual(settings.SESSION_COOKIE_AGE, 1800)
        self.assertTrue(settings.SESSION_SAVE_EVERY_REQUEST)

    def test_password_min_length_is_8(self):
        validator = next(v for v in settings.AUTH_PASSWORD_VALIDATORS if v["NAME"].endswith("MinimumLengthValidator"))
        self.assertEqual(validator["OPTIONS"]["min_length"], 8)

    def test_time_zone(self):
        self.assertTrue(settings.USE_TZ)
        self.assertEqual(settings.TIME_ZONE, "Asia/Ho_Chi_Minh")
