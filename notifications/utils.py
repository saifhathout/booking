from .models import Notification

def create_notification(user, title, message, url='/'):
    Notification.objects.create(
        user=user,
        title=title,
        message=message,
        url=url
    )

def get_unread_count(user):
    return Notification.objects.filter(user=user, is_read=False).count()

def send_push(user, title, message, url='/'):
    try:
        from webpush import send_user_notification
        payload = {'head': title, 'body': message, 'url': url}
        send_user_notification(user=user, payload=payload, ttl=1000)
    except Exception as e:
        print(f"Push error: {e}")