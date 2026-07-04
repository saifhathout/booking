# notifications/utils.py

import logging
from .models import Notification

logger = logging.getLogger(__name__)


def create_notification(user, title, message, url='/'):
    """إنشاء إشعار في قاعدة البيانات"""
    if not user:
        return None
    
    try:
        notification = Notification.objects.create(
            user=user,
            title=title,
            message=message,
            url=url,
            is_read=False
        )
        logger.info(f"✅ Notification created for {user.username}: {title}")
        return notification
    except Exception as e:
        logger.error(f"❌ Error creating notification: {e}")
        return None


def get_unread_count(user):
    """عدد الإشعارات غير المقروءة"""
    if not user or not user.is_authenticated:
        return 0
    return Notification.objects.filter(user=user, is_read=False).count()


def mark_as_read(user, notification_id=None):
    """تحديد إشعار كمقروء"""
    if not user:
        return
    
    if notification_id:
        Notification.objects.filter(user=user, id=notification_id).update(is_read=True)
    else:
        Notification.objects.filter(user=user, is_read=False).update(is_read=True)


def mark_all_read(user):
    """تحديد جميع الإشعارات كمقروءة"""
    if not user:
        return
    Notification.objects.filter(user=user, is_read=False).update(is_read=True)