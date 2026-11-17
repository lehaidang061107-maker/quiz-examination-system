# Website Django chạy bằng Docker (S3-30). Dùng cho máy cá nhân và buổi demo, không phải máy chủ thật.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ src/
RUN useradd --create-home --uid 1000 app
USER app
WORKDIR /app/src

EXPOSE 8000
# Tự tạo/cập nhật bảng mỗi lần khởi động, rồi chạy website.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec python manage.py runserver 0.0.0.0:8000"]
