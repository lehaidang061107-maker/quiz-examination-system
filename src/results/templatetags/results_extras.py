from django import template

register = template.Library()


@register.filter
def duration(value):
    """timedelta -> '1 giờ 05 phút 09 giây' / '12 phút 30 giây'."""
    if value is None:
        return ""
    seconds = max(0, int(value.total_seconds()))
    hours, rest = divmod(seconds, 3600)
    minutes, seconds = divmod(rest, 60)
    if hours:
        return f"{hours} giờ {minutes:02d} phút {seconds:02d} giây"
    return f"{minutes} phút {seconds:02d} giây"
