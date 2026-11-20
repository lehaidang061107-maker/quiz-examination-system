from django import forms
from django.core.exceptions import ValidationError
import re

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
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Mật khẩu xác nhận không khớp.")
        return cleaned_data