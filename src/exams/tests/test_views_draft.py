"""S3-11: Tạo và chỉnh sửa đề nháp (FR-06, FR-07, BR-14, BR-17, UC Create Exam).

Chạy riêng: cd src && python manage.py test exams.tests.test_views_draft
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role
from config.tests.factories import make_open_exam, make_question, make_user
from exams.models import Exam, ExamStatus

VN = ZoneInfo("Asia/Ho_Chi_Minh")


def form_data(**overrides):
    data = {
        "title": "Kiểm tra giữa kỳ",
        "description": "Chương 1-3",
        "duration_minutes": "45",
        "opens_at": "2030-01-10T08:00",
        "closes_at": "2030-01-10T10:00",
    }
    data.update(overrides)
    return data


class ExamListTests(TestCase):
    def setUp(self):
        self.teacher = make_user(Role.TEACHER)
        self.other = make_user(Role.TEACHER)
        self.client.force_login(self.teacher)

    def test_chi_thay_de_cua_minh(self):
        self.teacher.create_exam({"title": "Đề của tôi", "duration_minutes": 30})
        self.other.create_exam({"title": "Đề người khác", "duration_minutes": 30})
        response = self.client.get(reverse("exams:list"))
        self.assertContains(response, "Đề của tôi")
        self.assertNotContains(response, "Đề người khác")

    def test_loc_theo_trang_thai(self):
        self.teacher.create_exam({"title": "Đề nháp A", "duration_minutes": 30})
        make_open_exam(self.teacher, [], [make_question(self.teacher)])  # tên "Đề kiểm tra", PUBLISHED
        response = self.client.get(reverse("exams:list"), {"status": ExamStatus.PUBLISHED})
        self.assertContains(response, "Đề kiểm tra")
        self.assertNotContains(response, "Đề nháp A")

    def test_trang_thai_loc_sai_thi_bo_qua(self):
        self.teacher.create_exam({"title": "Đề nháp A", "duration_minutes": 30})
        response = self.client.get(reverse("exams:list"), {"status": "abc"})
        self.assertContains(response, "Đề nháp A")
        self.assertEqual(response.context["selected_status"], "")

    def test_chua_co_de(self):
        response = self.client.get(reverse("exams:list"))
        self.assertContains(response, "Bạn chưa có đề thi nào.")

    def test_sai_vai_tro_bi_chan(self):
        for role in (Role.STUDENT, Role.ADMIN):
            with self.subTest(role=role):
                self.client.force_login(make_user(role))
                self.assertEqual(self.client.get(reverse("exams:list")).status_code, 403)

    def test_chua_dang_nhap_chuyen_toi_dang_nhap(self):
        self.client.logout()
        response = self.client.get(reverse("exams:list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)


class ExamCreateTests(TestCase):
    def setUp(self):
        self.teacher = make_user(Role.TEACHER)
        self.client.force_login(self.teacher)
        self.url = reverse("exams:create")

    def test_tao_de_nhap_thanh_cong_luu_utc(self):
        response = self.client.post(self.url, form_data(), follow=True)
        exam = Exam.objects.get(teacher=self.teacher)
        self.assertRedirects(response, reverse("exams:detail", args=[exam.pk]))
        self.assertContains(response, "Đã tạo đề thi nháp.")
        self.assertEqual(exam.status, ExamStatus.DRAFT)
        self.assertEqual(exam.duration_minutes, 45)
        # Nhập 08:00 giờ Việt Nam -> lưu 01:00 UTC, trang chi tiết hiện lại 08:00.
        self.assertEqual(exam.opens_at, datetime(2030, 1, 10, 8, 0, tzinfo=VN))
        self.assertEqual(exam.opens_at.astimezone(ZoneInfo("UTC")).hour, 1)
        self.assertContains(response, "10/01/2030 08:00")

    def test_khong_nhap_lich_thi_van_tao_duoc(self):
        self.client.post(self.url, form_data(opens_at="", closes_at="", description=""))
        exam = Exam.objects.get(teacher=self.teacher)
        self.assertIsNone(exam.opens_at)
        self.assertIsNone(exam.closes_at)
        self.assertIsNone(exam.description)

    def test_thieu_ten(self):
        response = self.client.post(self.url, form_data(title="   "))
        self.assertContains(response, "Vui lòng nhập tên đề thi.")
        self.assertFalse(Exam.objects.exists())

    def test_thieu_thoi_luong(self):
        response = self.client.post(self.url, form_data(duration_minutes=""))
        self.assertContains(response, "Vui lòng nhập thời lượng làm bài.")
        self.assertFalse(Exam.objects.exists())

    def test_thoi_luong_khong_duong(self):
        for value in ("0", "-5"):
            with self.subTest(value=value):
                response = self.client.post(self.url, form_data(duration_minutes=value))
                self.assertContains(response, "Thời lượng phải lớn hơn 0 phút.")
        self.assertFalse(Exam.objects.exists())

    def test_thoi_luong_khong_phai_so_hoac_qua_lon(self):
        response = self.client.post(self.url, form_data(duration_minutes="abc"))
        self.assertContains(response, "Thời lượng phải là số nguyên.")
        response = self.client.post(self.url, form_data(duration_minutes="99999999999"))
        self.assertContains(response, "Thời lượng tối đa 1440 phút (24 giờ).")
        self.assertFalse(Exam.objects.exists())

    def test_gio_dong_truoc_gio_mo(self):
        response = self.client.post(self.url, form_data(closes_at="2030-01-10T07:00"))
        self.assertContains(response, "Thời gian đóng phải sau thời gian mở.")
        self.assertFalse(Exam.objects.exists())

    def test_ngay_gio_sai_dinh_dang(self):
        response = self.client.post(self.url, form_data(opens_at="10/01/2030"))
        self.assertContains(response, "Thời gian mở không đúng định dạng.")

    def test_ten_qua_dai(self):
        response = self.client.post(self.url, form_data(title="a" * 201))
        self.assertContains(response, "Tên đề thi tối đa 200 ký tự.")

    def test_noi_dung_duoc_ma_hoa_khi_hien_thi(self):
        self.client.post(self.url, form_data(title="<script>alert(1)</script>"))
        exam = Exam.objects.get(teacher=self.teacher)
        response = self.client.get(reverse("exams:detail", args=[exam.pk]))
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;")

    def test_sinh_vien_khong_tao_duoc(self):
        self.client.force_login(make_user(Role.STUDENT))
        self.assertEqual(self.client.post(self.url, form_data()).status_code, 403)
        self.assertFalse(Exam.objects.exists())


class ExamEditTests(TestCase):
    def setUp(self):
        self.teacher = make_user(Role.TEACHER)
        self.exam = self.teacher.create_exam({"title": "Đề cũ", "duration_minutes": 30})
        self.client.force_login(self.teacher)
        self.url = reverse("exams:edit", args=[self.exam.pk])

    def test_form_sua_hien_gia_tri_hien_tai(self):
        Exam.objects.filter(pk=self.exam.pk).update(opens_at=datetime(2030, 1, 10, 1, 0, tzinfo=ZoneInfo("UTC")))
        response = self.client.get(self.url)
        self.assertContains(response, 'value="Đề cũ"')
        self.assertContains(response, 'value="2030-01-10T08:00"')  # 01:00 UTC hiện thành 08:00 giờ VN

    def test_sua_de_nhap_thanh_cong(self):
        response = self.client.post(self.url, form_data(title="Đề mới", duration_minutes="60"), follow=True)
        self.assertContains(response, "Đã lưu thay đổi đề thi.")
        self.exam.refresh_from_db()
        self.assertEqual((self.exam.title, self.exam.duration_minutes), ("Đề mới", 60))

    def test_sua_sai_du_lieu_khong_luu(self):
        response = self.client.post(self.url, form_data(title=""))
        self.assertContains(response, "Vui lòng nhập tên đề thi.")
        self.exam.refresh_from_db()
        self.assertEqual(self.exam.title, "Đề cũ")

    def test_de_da_phat_hanh_khong_sua_duoc(self):
        exam = make_open_exam(self.teacher, [], [make_question(self.teacher)])
        url = reverse("exams:edit", args=[exam.pk])
        response = self.client.post(url, form_data(title="Đổi tên"), follow=True)
        self.assertContains(response, "Đề đã phát hành, không thể sửa nội dung.")
        exam.refresh_from_db()
        self.assertEqual(exam.title, "Đề kiểm tra")
        # Trang chi tiết không hiện nút sửa.
        self.assertNotContains(self.client.get(reverse("exams:detail", args=[exam.pk])), url)

    def test_giang_vien_khac_khong_xem_khong_sua_duoc(self):
        self.client.force_login(make_user(Role.TEACHER))
        self.assertEqual(self.client.get(reverse("exams:detail", args=[self.exam.pk])).status_code, 403)
        self.assertEqual(self.client.post(self.url, form_data(title="Hack")).status_code, 403)
        self.exam.refresh_from_db()
        self.assertEqual(self.exam.title, "Đề cũ")

    def test_de_khong_ton_tai_tra_403(self):
        self.assertEqual(self.client.get(reverse("exams:detail", args=[999999])).status_code, 403)

    def test_xem_chi_tiet(self):
        Exam.objects.filter(pk=self.exam.pk).update(closes_at=timezone.now() + timedelta(days=1))
        response = self.client.get(reverse("exams:detail", args=[self.exam.pk]))
        self.assertContains(response, "Đề cũ")
        self.assertContains(response, "30 phút")
        self.assertContains(response, self.url)
