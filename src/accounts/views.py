from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import StudentRegisterForm
from .models import User, Role


def register_view(request):
    if request.method == 'POST':
        form = StudentRegisterForm(request.POST)
        if form.is_valid():
            full_name = form.cleaned_data['full_name']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            User.objects.create_user(
                email=email,
                password=password,
                full_name=full_name,
                role=Role.STUDENT,
            )

            messages.success(request, "Đăng ký tài khoản thành công! Vui lòng đăng nhập.")
            return redirect("accounts:login")
    else:
        form = StudentRegisterForm()

    return render(request, 'accounts/register.html', {'form': form})

from django.contrib.auth import authenticate, login as auth_login
from django.shortcuts import redirect, render


def login_view(request):
    error = None
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        user = authenticate(request, email=email, password=password)
        if user is not None:
            auth_login(request, user)
            next_url = request.POST.get("next") or request.GET.get("next")
            return redirect(next_url or "home")
        error = "Email hoặc mật khẩu không đúng."
    return render(request, "accounts/login.html", {"error": error})