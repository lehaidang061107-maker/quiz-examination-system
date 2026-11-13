from django.db import models
from django.contrib.auth.models import User

class Exam(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Đề nháp'),
        ('PUBLISHED', 'Đã phát hành'),
        ('CLOSED', 'Đã đóng'),
    ]

    title = models.CharField(max_length=255, verbose_name="Tên đề thi")
    description = models.TextField(blank=True, null=True, verbose_name="Mô tả đề thi")
    duration_minutes = models.PositiveIntegerField(default=60, verbose_name="Thời gian làm bài (phút)")
    pass_score = models.DecimalField(max_digits=5, decimal_places=2, default=5.0, verbose_name="Điểm đạt")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT', verbose_name="Trạng thái")
    is_score_published = models.BooleanField(default=False, verbose_name="Đã công bố điểm")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_exams')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"


class ExamParticipant(models.Model):
    ACCESS_STATUS = [
        ('ALLOWED', 'Được phép thi'),
        ('REVOKED', 'Đã thu hồi quyền'),
        ('COMPLETED', 'Đã hoàn thành'),
    ]

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='participants')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exam_enrollments')
    status = models.CharField(max_length=20, choices=ACCESS_STATUS, default='ALLOWED')
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('exam', 'student')

    def __str__(self):
        return f"{self.student.username} - {self.exam.title}"