# notifications/context_processors.py

from .models import Notification


def unread_count(request):
    """إضافة عدد الإشعارات غير المقروءة لكل الطلبات"""
    if request.user.is_authenticated:
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return {'unread_notifications_count': count}
    return {'unread_notifications_count': 0}