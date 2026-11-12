from django import forms
from .models import Exam

class ExamDraftForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['title', 'description', 'duration_minutes', 'pass_score']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập tên đề thi...'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Hướng dẫn làm bài...'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'pass_score': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'min': 0}),
        }