from django.core.exceptions import ValidationError


class LetterAndDigitValidator:
    """Mật khẩu phải có cả chữ và số (UC đăng ký, UC quản lý tài khoản)."""

    def validate(self, password, user=None):
        if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
            raise ValidationError("Mật khẩu phải có cả chữ và số.", code="password_no_letter_digit")

    def get_help_text(self):
        return "Mật khẩu phải có cả chữ và số."
