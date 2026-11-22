"""Kiểm tra chung cho file giao diện.

Ghi chú {# ... #} của Django chỉ được nằm trên một dòng; viết nhiều dòng thì chữ bị in ra trang.
Ghi chú dài thì dùng {% comment %} ... {% endcomment %}.
"""
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class TemplateCommentTests(SimpleTestCase):
    def test_ghi_chu_mot_dong(self):
        problems = []
        for folder in settings.TEMPLATES[0]["DIRS"]:
            for path in Path(folder).rglob("*.html"):
                for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                    if "{#" in line and "#}" not in line.split("{#", 1)[1]:
                        problems.append(f"{path.name}:{number}")
        self.assertEqual(problems, [], "Ghi chú {# #} viết trên nhiều dòng sẽ hiện ra trang")
