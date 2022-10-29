import django.utils.timezone as tz


def year(request):
    """Добавляет переменную с текущим годом."""
    return {
        'year': tz.now().year,
    }
