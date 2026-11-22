"""S3-34: thống kê kết quả một đề cho giảng viên (NFR-MAI-02: mở rộng thống kê, báo cáo).

Chỉ tính bài đã chấm (GRADED), đọc từ bảng results và submission_answers có sẵn, không thêm bảng.
"""
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Count, Q

BINS = [(0, 2), (2, 4), (4, 6), (6, 8), (8, 10)]  # khoảng điểm thang 10; khoảng cuối gồm cả 10
PASS_MARK = Decimal("5")


def exam_statistics(exam):
    """Trả về dict số liệu, hoặc graded_count = 0 nếu đề chưa có bài nào được chấm."""
    from attempts.models import SubmissionAnswer, SubmissionStatus
    from results.models import Result

    results = list(
        Result.objects.filter(submission__exam=exam, submission__status=SubmissionStatus.GRADED)
        .select_related("submission")
    )
    stats = {"graded_count": len(results), "participant_count": exam.participants.filter(is_active=True).count()}
    if not results:
        return stats

    scores = [r.score_on_10 for r in results]
    stats.update({
        # Trung bình tính từ điểm chưa làm tròn rồi làm tròn 2 chữ số như score_on_10.
        "average": (sum(r.score * 10 / r.max_score for r in results if r.max_score) / len(results))
        .quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "highest": max(scores),
        "lowest": min(scores),
        "pass_count": sum(score >= PASS_MARK for score in scores),
    })
    stats["pass_percent"] = round(stats["pass_count"] * 100 / len(scores))

    distribution = []
    for low, high in BINS:
        last = high == BINS[-1][1]
        count = sum(low <= score < high or (last and score == high) for score in scores)
        distribution.append({"label": f"{low}–{high}", "count": count, "percent": round(count * 100 / len(scores))})
    stats["distribution"] = distribution

    # Tỷ lệ đúng từng câu: đếm đáp án đã chọn của các bài đã chấm, theo từng câu trong đề.
    submission_ids = [r.submission_id for r in results]
    counts = {
        row["question_id"]: row
        for row in SubmissionAnswer.objects.filter(submission_id__in=submission_ids)
        .values("question_id")
        .annotate(
            correct=Count("pk", filter=Q(selected_option__is_correct=True)),
            answered=Count("pk", filter=Q(selected_option__isnull=False)),
        )
    }
    questions = []
    for item in exam.exam_questions.select_related("question").order_by("position"):
        row = counts.get(item.question_id, {"correct": 0, "answered": 0})
        total = len(results)
        questions.append({
            "position": item.position,
            "content": item.question.content or "",
            "correct": row["correct"],
            "wrong": row["answered"] - row["correct"],
            "blank": total - row["answered"],
            "correct_percent": round(row["correct"] * 100 / total),
        })
    stats["questions"] = questions
    return stats
