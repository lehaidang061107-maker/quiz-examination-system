"""Test lớp User, Admin, Teacher, Student theo sơ đồ lớp.

Chạy riêng: cd src && python manage.py test accounts
"""
from datetime import timedelta

from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import RequestFactory, TestCase
from django.utils import timezone

from accounts.models import Admin, Role, Student, Teacher, User, UserStatus
from config.tests.factories import PASSWORD, make_open_exam, make_question, make_user


def make_request():
    """Tạo một request giả có phiên, giống trình duyệt gửi lên."""
    request = RequestFactory().post("/accounts/login/")
    SessionMiddleware(lambda r: None).process_request(request)
    return request


class LoginTests(TestCase):
    """UC Login (FR-02), NFR-SEC-07: khóa tạm 15 phút sau 5 lần sai."""

    def setUp(self):
        self.student = make_user(Role.STUDENT, email="sv@test.example")

    def test_dang_nhap_dung_thi_tao_phien(self):
        request = make_request()
        self.assertTrue(User.login(request, "  SV@test.example ", PASSWORD))  # email không phân biệt hoa thường
        self.assertEqual(request.session["_auth_user_id"], str(self.student.pk))

    def test_sai_mat_khau_bao_loi_chung(self):
        with self.assertRaisesMessage(ValidationError, "Email hoặc mật khẩu không đúng."):
            User.login(make_request(), "sv@test.example", "saimatkhau1")

    def test_email_khong_ton_tai_bao_cung_loi(self):
        # Không để lộ email nào đã đăng ký.
        with self.assertRaisesMessage(ValidationError, "Email hoặc mật khẩu không đúng."):
            User.login(make_request(), "khongco@test.example", PASSWORD)

    def test_sai_5_lan_thi_khoa_tam_15_phut(self):
        for _ in range(5):
            with self.assertRaises(ValidationError):
                User.login(make_request(), "sv@test.example", "saimatkhau1")
        self.student.refresh_from_db()
        self.assertGreater(self.student.locked_until, timezone.now() + timedelta(minutes=14))
        # Đang khóa tạm thì nhập đúng mật khẩu cũng bị từ chối.
        with self.assertRaisesMessage(ValidationError, "thử lại sau"):
            User.login(make_request(), "sv@test.example", PASSWORD)

    def test_dang_nhap_dung_thi_dat_lai_bo_dem(self):
        for _ in range(3):
            with self.assertRaises(ValidationError):
                User.login(make_request(), "sv@test.example", "saimatkhau1")
        User.login(make_request(), "sv@test.example", PASSWORD)
        self.student.refresh_from_db()
        self.assertEqual(self.student.failed_login_count, 0)

    def test_tai_khoan_bi_admin_khoa_khong_dang_nhap_duoc(self):
        User.objects.filter(pk=self.student.pk).update(status=UserStatus.LOCKED)
        with self.assertRaisesMessage(ValidationError, "bị khóa"):
            User.login(make_request(), "sv@test.example", PASSWORD)


class RoleClassTests(TestCase):
    """Admin, Teacher, Student kế thừa User (sơ đồ lớp, BR-12)."""

    def test_moi_lop_con_chi_lay_dung_vai_tro(self):
        admin, teacher, student = make_user(Role.ADMIN), make_user(Role.TEACHER), make_user(Role.STUDENT)
        self.assertEqual(list(Admin.objects.all()), [admin])
        self.assertEqual(list(Teacher.objects.all()), [teacher])
        self.assertEqual(list(Student.objects.all()), [student])

    def test_as_role_tra_ve_dung_lop_con(self):
        user = User.objects.get(pk=make_user(Role.TEACHER).pk)
        self.assertIsInstance(user.as_role(), Teacher)
        self.assertIsInstance(user.as_role(), User)


class AdminTests(TestCase):
    """UC Manage User Accounts (FR-04), BR-22."""

    def setUp(self):
        self.admin = make_user(Role.ADMIN)

    def test_tao_tai_khoan_hop_le(self):
        user = self.admin.create_user({
            "full_name": "Nguyễn Văn A", "email": " GV@Test.example ", "password": "Giangvien2026", "role": Role.TEACHER,
        })
        self.assertEqual(user.email, "gv@test.example")
        self.assertEqual(user.role, Role.TEACHER)

    def test_tao_tai_khoan_sai_thi_bao_tung_truong(self):
        make_user(email="trung@test.example")
        with self.assertRaises(ValidationError) as ctx:
            self.admin.create_user({"full_name": "", "email": "trung@test.example", "password": "123", "role": "X"})
        self.assertEqual(set(ctx.exception.message_dict), {"full_name", "email", "password", "role"})

    def test_khong_ha_quyen_duoc_admin_cuoi_cung(self):
        with self.assertRaisesMessage(ValidationError, "quản trị viên đang hoạt động cuối cùng"):
            self.admin.update_user(self.admin.pk, {"role": Role.TEACHER})

    def test_khong_tu_khoa_hoac_tu_xoa_chinh_minh(self):
        with self.assertRaisesMessage(ValidationError, "chính tài khoản bạn đang dùng"):
            self.admin.lock_user(self.admin.pk)
        with self.assertRaisesMessage(ValidationError, "chính tài khoản bạn đang dùng"):
            self.admin.delete_user(self.admin.pk)

    def test_khong_khoa_tai_khoan_da_ngung_su_dung(self):
        student = make_user()
        self.admin.delete_user(student.pk)
        with self.assertRaisesMessage(ValidationError, "Chỉ khóa được tài khoản đang hoạt động."):
            self.admin.lock_user(student.pk)
        with self.assertRaisesMessage(ValidationError, "Tài khoản đã ngừng sử dụng."):
            self.admin.delete_user(student.pk)
        student.refresh_from_db()
        self.assertEqual(student.status, UserStatus.DELETED)

    def test_mo_khoa_tai_khoan_bi_khoa(self):
        student = make_user()
        self.admin.lock_user(student.pk)
        User.objects.filter(pk=student.pk).update(failed_login_count=3, locked_until=timezone.now())
        self.admin.unlock_user(student.pk)
        student.refresh_from_db()
        self.assertEqual(student.status, UserStatus.ACTIVE)
        self.assertEqual(student.failed_login_count, 0)
        self.assertIsNone(student.locked_until)
        with self.assertRaisesMessage(ValidationError, "Chỉ mở khóa được tài khoản đang bị khóa."):
            self.admin.unlock_user(student.pk)

    def test_xoa_tai_khoan_chi_danh_dau_deleted(self):
        student = make_user()
        self.admin.delete_user(student.pk)
        student.refresh_from_db()
        self.assertEqual(student.status, UserStatus.DELETED)  # vẫn còn trong bảng để giữ lịch sử
        self.assertFalse(student.is_active)

    def test_khoa_sinh_vien_dang_lam_bai_thi_bai_duoc_nop(self):
        teacher, student = make_user(Role.TEACHER), make_user()
        exam = make_open_exam(teacher, [student], [make_question(teacher)])
        submission = student.start_exam(exam.pk)
        self.admin.lock_user(student.pk)
        submission.refresh_from_db()
        self.assertEqual(submission.status, "GRADED")  # nộp bằng đáp án đã lưu rồi chấm luôn

    def test_khoa_va_xoa_ghi_dung_ly_do_tu_nop(self):
        teacher = make_user(Role.TEACHER)
        question = make_question(teacher)
        for action, reason in ((self.admin.lock_user, "tài khoản bị khóa"),
                               (self.admin.delete_user, "tài khoản ngừng sử dụng")):
            student = make_user()
            exam = make_open_exam(teacher, [student], [question])
            student.start_exam(exam.pk)
            with self.assertLogs("attempts.audit", level="INFO") as logs:
                action(student.pk)
            self.assertIn(f"tự nộp ({reason})", "\n".join(logs.output))

    def test_khong_sua_tai_khoan_da_ngung_su_dung(self):
        student = make_user()
        self.admin.delete_user(student.pk)
        with self.assertRaisesMessage(ValidationError, "đã ngừng sử dụng nên không thể sửa"):
            self.admin.update_user(student.pk, {"full_name": "Tên mới", "email": "moi@test.example"})
        student.refresh_from_db()
        self.assertNotEqual(student.full_name, "Tên mới")

    def test_so_lieu_hoat_dong_theo_vai_tro(self):
        teacher, student = make_user(Role.TEACHER), make_user()
        exam = make_open_exam(teacher, [student], [make_question(teacher)])
        student.start_exam(exam.pk)
        self.assertEqual(dict(teacher.activity_summary()), {"Câu hỏi đã tạo": 1, "Đề thi đã tạo": 1})
        self.assertEqual(dict(student.activity_summary()),
                         {"Đề được phân công": 1, "Bài đã nộp": 0, "Bài đang làm": 1})
        self.assertEqual(self.admin.activity_summary(), [])

    def test_khong_doi_vai_tro_khi_da_co_du_lieu(self):
        teacher = make_user(Role.TEACHER)
        make_question(teacher)
        with self.assertRaisesMessage(ValidationError, "không đổi được vai trò"):
            self.admin.update_user(teacher.pk, {"role": Role.STUDENT})


class TeacherTests(TestCase):
    """Teacher chỉ thao tác trên đề của mình (NFR-SEC-02, NFR-SEC-09)."""

    def test_khong_quan_ly_duoc_de_cua_giang_vien_khac(self):
        owner, other = make_user(Role.TEACHER), make_user(Role.TEACHER)
        exam = owner.create_exam({"title": "Đề của người khác"})
        with self.assertRaises(PermissionDenied):
            other.manage_exam(exam.pk)

    def test_khong_giao_de_cho_giang_vien(self):
        teacher = make_user(Role.TEACHER)
        exam = teacher.create_exam({"title": "Đề nháp"})
        with self.assertRaisesMessage(ValidationError, "không phải sinh viên"):
            teacher.assign_students(exam.pk, [make_user(Role.TEACHER).pk])


class StudentTests(TestCase):
    """UC View Exam List (FR-08), UC Take Exam (FR-09)."""

    def setUp(self):
        self.teacher = make_user(Role.TEACHER)
        self.student = make_user()
        self.exam = make_open_exam(self.teacher, [self.student], [make_question(self.teacher)])

    def test_chi_thay_de_duoc_giao(self):
        outsider = make_user()
        self.assertEqual(list(self.student.view_available_exams()), [self.exam])
        self.assertEqual(list(outsider.view_available_exams()), [])

    def test_mo_lai_de_dung_lai_luot_cu(self):
        # BR-20, BR-21: mở tab khác hoặc đăng nhập lại không tạo lượt mới, không đặt lại giờ.
        first = self.student.start_exam(self.exam.pk)
        again = self.student.start_exam(self.exam.pk)
        self.assertEqual(first.pk, again.pk)
        self.assertEqual(first.deadline_at, again.deadline_at)

    def test_khong_lam_duoc_bai_cua_nguoi_khac(self):
        submission = self.student.start_exam(self.exam.pk)
        with self.assertRaises(PermissionDenied):
            make_user().submit_exam(submission.pk)
