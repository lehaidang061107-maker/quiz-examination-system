from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
import re

from .models import Role

class StudentRegisterForm(forms.Form):
    full_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập họ và tên'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.com'})
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Ít nhất 8 ký tự, gồm chữ và số'})
    )
    confirm_password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Nhập lại mật khẩu'})
    )

    def clean_email(self):
        email = self.cleaned_data.get('email').strip().lower()
        # Kiểm tra email đã tồn tại trong database chưa (giả sử model User nằm trong accounts.models)
        from accounts.models import User
        if User.objects.filter(email=email).exists():
            raise ValidationError("Email này đã được sử dụng. Vui lòng chọn email khác.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if len(password) < 8:
            raise ValidationError("Mật khẩu phải có độ dài tối thiểu từ 8 ký tự trở lên.")
        if not re.search(r'[A-Za-z]', password) or not re.search(r'[0-9]', password):
            raise ValidationError("Mật khẩu phải bao gồm cả chữ và số.")
        # Thêm các quy tắc chung của hệ thống (AUTH_PASSWORD_VALIDATORS), ví dụ chặn mật khẩu quá phổ biến.
        validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Mật khẩu xác nhận không khớp.")
        return cleaned_data


class AdminUserCreateForm(forms.Form):
    full_name = forms.CharField(
        label="Họ và tên",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Nguyễn Văn A"}),
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "name@example.com"}),
    )
    password = forms.CharField(
        label="Mật khẩu",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    role = forms.ChoiceField(
        label="Vai trò",
        choices=Role.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )


class AdminUserUpdateForm(forms.Form):
    full_name = forms.CharField(
        label="Họ và tên",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )
    role = forms.ChoiceField(
        label="Vai trò",
        choices=Role.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )


class AdminResetPasswordForm(forms.Form):
    """S3-36: Admin đặt lại mật khẩu. Quy tắc mật khẩu kiểm tra ở Admin.reset_password()."""
    new_password = forms.CharField(
        label="Mật khẩu mới",
        help_text="Ít nhất 8 ký tự, gồm cả chữ và số.",
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
    )
    confirm_password = forms.CharField(
        label="Nhập lại mật khẩu mới",
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("new_password") and cleaned.get("confirm_password") \
                and cleaned["new_password"] != cleaned["confirm_password"]:
            self.add_error("confirm_password", "Mật khẩu xác nhận không khớp.")
        return cleaned


class ChangePasswordForm(forms.Form):
    """S3-35: đổi mật khẩu. Kiểm tra mật khẩu hiện tại và quy tắc mật khẩu nằm ở User.change_password()."""
    current_password = forms.CharField(
        label="Mật khẩu hiện tại",
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "current-password"}),
    )
    new_password = forms.CharField(
        label="Mật khẩu mới",
        help_text="Ít nhất 8 ký tự, gồm cả chữ và số.",
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
    )
    confirm_password = forms.CharField(
        label="Nhập lại mật khẩu mới",
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("new_password") and cleaned.get("confirm_password") \
                and cleaned["new_password"] != cleaned["confirm_password"]:
            self.add_error("confirm_password", "Mật khẩu xác nhận không khớp.")
        return cleaned
