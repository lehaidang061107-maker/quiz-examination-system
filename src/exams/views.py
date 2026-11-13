from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Exam, ExamParticipant
from .forms import ExamDraftForm

@login_required
def exam_list(request):
    exams = Exam.objects.filter(created_by=request.user).order_by('-created_at')
    return render(request, 'exams/exam_list.html', {'exams': exams})

@login_required
def exam_create_draft(request):
    if request.method == 'POST':
        form = ExamDraftForm(request.POST)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.created_by = request.user
            exam.status = 'DRAFT'
            exam.save()
            messages.success(request, "Đã tạo đề thi nháp thành công!")
            return redirect('exam_edit_draft', exam_id=exam.id)
    else:
        form = ExamDraftForm()
    return render(request, 'exams/exam_form.html', {'form': form, 'is_edit': False})

@login_required
def exam_edit_draft(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, created_by=request.user)
    
    if exam.status != 'DRAFT':
        messages.error(request, "Chỉ được phép chỉnh sửa thông tin khi đề ở trạng thái Nháp!")
        return redirect('exam_list')

    if request.method == 'POST':
        form = ExamDraftForm(request.POST, instance=exam)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã cập nhật bản nháp!")
            return redirect('exam_edit_draft', exam_id=exam.id)
    else:
        form = ExamDraftForm(instance=exam)
        
    return render(request, 'exams/exam_form.html', {'form': form, 'exam': exam, 'is_edit': True})

@login_required
def exam_manage_participants(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, created_by=request.user)
    participants = ExamParticipant.objects.filter(exam=exam).select_related('student')
    
    enrolled_ids = participants.values_list('student_id', flat=True)
    available_students = User.objects.exclude(id__in=enrolled_ids).exclude(id=request.user.id)

    if request.method == 'POST':
        action = request.POST.get('action')
        student_id = request.POST.get('student_id')
        student = get_object_or_404(User, id=student_id)

        if action == 'grant':
            ExamParticipant.objects.update_or_create(
                exam=exam, student=student,
                defaults={'status': 'ALLOWED'}
            )
            messages.success(request, f"Đã cấp quyền dự thi cho {student.username}.")
        elif action == 'revoke':
            participant = get_object_or_404(ExamParticipant, exam=exam, student=student)
            if participant.status == 'COMPLETED':
                messages.error(request, "Không thể thu hồi quyền của thí sinh đã nộp bài!")
            else:
                participant.status = 'REVOKED'
                participant.save()
                messages.warning(request, f"Đã thu hồi quyền dự thi của {student.username}.")

        return redirect('exam_manage_participants', exam_id=exam.id)

    return render(request, 'exams/exam_participants.html', {
        'exam': exam,
        'participants': participants,
        'available_students': available_students
    })