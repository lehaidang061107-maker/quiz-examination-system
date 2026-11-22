"""S3-15: Kiểm thử tích hợp luồng chính qua giao diện (Django test client).

Đi đúng các trang người dùng bấm: Admin tạo tài khoản -> Teacher soạn câu hỏi, tạo đề, chọn câu,
phân công, phát hành -> Student làm bài, tự lưu, nộp -> Teacher đóng đề, công bố -> Student xem điểm.
Mỗi bước kiểm tra thêm truy cập sai vai trò / sai chủ sở hữu.

Chạy riêng: cd src && python manage.py test config.tests.test_integration_flow
"""
import json
from unittest import mock

from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from accounts.management.commands.seed_demo import EXAM_TITLES
from accounts.models import Role, User
from attempts.models import Submission, SubmissionStatus
from config.tests.factories import make_user
from exams.models import Exam, ExamStatus
from questions.models import Question

PASSWORD = "Kiemthu2026"


def login(email, password=PASSWORD):
    """Đăng nhập thật qua trang Đăng nhập (không dùng force_login) để kiểm tra cả phiên."""
    client = Client()
    response = client.post(reverse("accounts:login"), {"email": email, "password": password})
    assert response.status_code == 302, f"Đăng nhập {email} thất bại"
    return client


def messages_of(response):
    return [str(m) for m in response.context["messages"]]


class EndToEndFlowTests(TestCase):
    """Một kịch bản xuyên suốt; các bước chạy nối tiếp nên viết trong một test, chia thành hàm nhỏ cho dễ đọc."""

    def setUp(self):
        User.objects.create_user("admin@flow.example", PASSWORD, full_name="Quản trị", role=Role.ADMIN)
        self.admin = login("admin@flow.example")

    # ---------- Bước 1: Admin tạo tài khoản ----------
    def admin_creates_accounts(self):
        for email, name, role in (
            ("gv@flow.example", "Giảng viên Lan", Role.TEACHER),
            ("sv1@flow.example", "Sinh viên An", Role.STUDENT),
            ("sv2@flow.example", "Sinh viên Bình", Role.STUDENT),
        ):
            response = self.admin.post(
                reverse("accounts:admin_user_create"),
                {"full_name": name, "email": email, "password": PASSWORD, "role": role},
                follow=True,
            )
            self.assertIn(f"Đã tạo tài khoản {email}.", messages_of(response))
        # Teacher/Student không vào được trang quản lý tài khoản.
        teacher = login("gv@flow.example")
        self.assertEqual(teacher.get(reverse("accounts:admin_user_list")).status_code, 403)
        return teacher, login("sv1@flow.example"), login("sv2@flow.example")

    # ---------- Bước 2: Teacher soạn câu hỏi ----------
    def teacher_creates_questions(self, teacher):
        for content, options in (("2 + 2 = ?", ["4", "5", "6"]), ("Thủ đô Việt Nam?", ["Hà Nội", "Huế"])):
            response = teacher.post(
                reverse("questions:create"),
                {"content": content, "option_content": options, "correct_option": "0", "action": "activate"},
                follow=True,
            )
            self.assertIn("Tạo và kích hoạt câu hỏi thành công.", messages_of(response))
        return list(Question.objects.filter(teacher__email="gv@flow.example").order_by("question_id"))

    # ---------- Bước 3: Teacher tạo đề, chọn câu, phân công, phát hành ----------
    def teacher_builds_exam(self, teacher, questions):
        response = teacher.post(
            reverse("exams:create"),
            {"title": "Kiểm tra tích hợp", "duration_minutes": "30", "description": "",
             "opens_at": "", "closes_at": ""},
            follow=True,
        )
        self.assertIn("Đã tạo đề thi nháp.", messages_of(response))
        exam = Exam.objects.get(title="Kiểm tra tích hợp")

        response = teacher.post(
            reverse("exams:questions", args=[exam.pk]),
            {"action": "add", "question_ids": [q.pk for q in questions], "points": "5"},
            follow=True,
        )
        self.assertIn("Đã thêm 2 câu hỏi vào đề.", messages_of(response))

        sv1 = User.objects.get(email="sv1@flow.example")
        response = teacher.post(
            reverse("exams:participants", args=[exam.pk]), {"action": "grant", "student_ids": [sv1.pk]}, follow=True
        )
        self.assertIn("Đã cấp quyền dự thi cho 1 sinh viên.", messages_of(response))

        response = teacher.post(reverse("exams:publish", args=[exam.pk]), follow=True)
        self.assertIn("Đã phát hành đề thi.", messages_of(response))
        exam.refresh_from_db()
        self.assertEqual(exam.status, ExamStatus.PUBLISHED)
        return exam

    # ---------- Bước 4: Student làm bài, tự lưu, nộp ----------
    def student_takes_exam(self, student, exam, questions):
        response = student.get(reverse("attempts:exam_list"))
        self.assertContains(response, "Kiểm tra tích hợp")
        response = student.post(reverse("attempts:start_exam", args=[exam.pk]), follow=True)
        submission = Submission.objects.get(exam=exam, student__email="sv1@flow.example")
        self.assertContains(response, "2 + 2 = ?")
        self.assertNotContains(response, "is_correct")  # NFR-SEC-09: không lộ đáp án đúng

        # Câu 1 chọn đúng, câu 2 chọn sai; mỗi lần lưu trả về version mới.
        version = submission.version
        save_url = reverse("attempts:save_answer_api", args=[submission.pk])
        for question, pick in ((questions[0], 0), (questions[1], 1)):
            option = question.options.order_by("display_order")[pick]
            response = student.post(
                save_url,
                json.dumps({"question_id": question.pk, "option_id": option.pk, "version": version}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200, response.content)
            version = response.json()["version"]

        # Lưu bằng version cũ (tab khác) bị từ chối, không ghi đè.
        stale = student.post(
            save_url,
            json.dumps({"question_id": questions[0].pk, "option_id": None, "version": version - 1}),
            content_type="application/json",
        )
        self.assertEqual(stale.status_code, 409)

        response = student.post(reverse("attempts:submit_exam", args=[submission.pk]), follow=True)
        self.assertIn("Đã nộp bài thi 'Kiểm tra tích hợp' thành công!", messages_of(response))
        submission.refresh_from_db()
        self.assertEqual(submission.status, SubmissionStatus.GRADED)
        return submission

    def test_luong_xuyen_suot_tu_tao_tai_khoan_den_xem_diem(self):
        teacher, sv1, sv2 = self.admin_creates_accounts()
        questions = self.teacher_creates_questions(teacher)
        exam = self.teacher_builds_exam(teacher, questions)

        # Sinh viên không được giao không thấy đề và không bắt đầu được.
        self.assertNotContains(sv2.get(reverse("attempts:exam_list")), "Kiểm tra tích hợp")
        response = sv2.post(reverse("attempts:start_exam", args=[exam.pk]), follow=True)
        self.assertIn("Bạn không được giao đề thi này.", messages_of(response))

        submission = self.student_takes_exam(sv1, exam, questions)

        # Sinh viên khác không mở được bài của sv1.
        self.assertEqual(sv2.get(reverse("attempts:take_exam", args=[submission.pk])).status_code, 404)

        # Chưa công bố: Student chưa thấy điểm, Teacher đã thấy.
        detail_url = reverse("results:student_detail", args=[exam.pk])
        self.assertNotContains(sv1.get(detail_url), "5,00 / 10,00")
        self.assertContains(teacher.get(reverse("results:teacher_exam", args=[exam.pk])), "5,00 / 10,00")
        # Chưa đóng đề thì không công bố được.
        response = teacher.post(reverse("exams:publish_results", args=[exam.pk]), follow=True)
        self.assertIn("Chỉ công bố điểm sau khi đã đóng đề.", messages_of(response))

        # Teacher đóng đề, công bố điểm.
        response = teacher.post(reverse("exams:close", args=[exam.pk]), follow=True)
        self.assertIn("Đã đóng đề thi.", messages_of(response))
        response = teacher.post(reverse("exams:publish_results", args=[exam.pk]), follow=True)
        self.assertIn("Đã công bố điểm. Sinh viên đã xem được kết quả của mình.", messages_of(response))

        # Student xem điểm: đúng 1/2 câu, 5/10 điểm.
        response = sv1.get(detail_url)
        self.assertContains(response, "5,00 / 10,00")
        self.assertContains(sv1.get(reverse("results:student_list")), "Kiểm tra tích hợp")

        # Sau cùng: lưu trữ đề, điểm đã công bố vẫn xem được.
        response = teacher.post(reverse("exams:archive", args=[exam.pk]), follow=True)
        self.assertIn("Đã lưu trữ đề thi.", messages_of(response))
        self.assertContains(sv1.get(detail_url), "5,00 / 10,00")

    def test_sai_quyen_tung_buoc(self):
        teacher, sv1, _ = self.admin_creates_accounts()
        questions = self.teacher_creates_questions(teacher)
        exam = self.teacher_builds_exam(teacher, questions)
        make_user(Role.TEACHER, email="gv2@flow.example")
        User.objects.filter(email="gv2@flow.example").update(password=User.objects.get(email="gv@flow.example").password)
        other_teacher = login("gv2@flow.example")

        teacher_urls = [
            ("get", reverse("exams:list")),
            ("get", reverse("exams:detail", args=[exam.pk])),
            ("get", reverse("exams:participants", args=[exam.pk])),
            ("post", reverse("exams:close", args=[exam.pk])),
            ("post", reverse("exams:publish_results", args=[exam.pk])),
            ("get", reverse("questions:list")),
            ("get", reverse("results:teacher_exam", args=[exam.pk])),
        ]
        for method, url in teacher_urls:
            with self.subTest(student=url):
                self.assertEqual(getattr(sv1, method)(url).status_code, 403)
            with self.subTest(admin=url):
                self.assertEqual(getattr(self.admin, method)(url).status_code, 403)
        # Teacher khác: danh sách của mình thì vào được, đề của người khác thì 403.
        for method, url in teacher_urls[1:5] + teacher_urls[6:]:
            with self.subTest(other_teacher=url):
                self.assertEqual(getattr(other_teacher, method)(url).status_code, 403)
        exam.refresh_from_db()
        self.assertEqual(exam.status, ExamStatus.PUBLISHED)

        # Teacher không vào được trang làm bài của Student.
        self.assertEqual(teacher.get(reverse("attempts:exam_list")).status_code, 403)

        # Chưa đăng nhập: chuyển về trang Đăng nhập.
        response = Client().get(reverse("exams:list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_dang_xuat_xong_khong_dung_lai_phien(self):
        teacher, _, _ = self.admin_creates_accounts()
        teacher.post(reverse("accounts:logout"))
        self.assertEqual(teacher.get(reverse("exams:list")).status_code, 302)


class SeedDataFlowTests(TestCase):
    """Dữ liệu mẫu (seed_demo) dùng được với các trang quản lý đề."""

    def setUp(self):
        with mock.patch.dict("os.environ", {"DEMO_PASSWORD": PASSWORD}):
            call_command("seed_demo", stdout=mock.MagicMock())

    def test_tai_khoan_mau_dang_nhap_va_thay_de_demo(self):
        teacher = login("teacher@demo.example")
        response = teacher.get(reverse("exams:list"))
        for title in EXAM_TITLES:
            self.assertContains(response, title)
        # Đề của giảng viên demo không hiện với giảng viên hai.
        self.assertNotContains(login("teacher2@demo.example").get(reverse("exams:list")), EXAM_TITLES[0])

    def test_mo_duoc_moi_trang_cua_de_demo(self):
        teacher = login("teacher@demo.example")
        for exam in Exam.objects.filter(title__in=EXAM_TITLES):
            for name in ("exams:detail", "exams:participants"):
                with self.subTest(exam=exam.title, page=name):
                    self.assertEqual(teacher.get(reverse(name, args=[exam.pk])).status_code, 200)
        draft = Exam.objects.get(title=EXAM_TITLES[0])
        self.assertEqual(teacher.get(reverse("exams:questions", args=[draft.pk])).status_code, 200)

    def test_sinh_vien_mau_xem_danh_sach_bai_thi(self):
        response = login("student1@demo.example").get(reverse("attempts:exam_list"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, EXAM_TITLES[0])  # đề nháp không hiện với sinh viên
