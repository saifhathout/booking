import requests
from django.conf import settings
from .models import Notification

ONESIGNAL_APP_ID = "97a60b44-0546-45e3-8656-8272fa16d4d6"

def create_notification(user, title, message, url='/'):
    Notification.objects.create(user=user, title=title, message=message, url=url)

def get_unread_count(user):
    return Notification.objects.filter(user=user, is_read=False).count()

def send_push(user_id, title, message, url='/'):
    api_key = getattr(settings, 'ONESIGNAL_API_KEY', '')
    if not api_key:
        return
    
    headers = {
        'Authorization': f'Basic {api_key}',
        'Content-Type': 'application/json',
    }
    data = {
        'app_id': ONESIGNAL_APP_ID,
        'headings': {'en': title},
        'contents': {'en': message},
        'url': url,
        'include_external_user_ids': [str(user_id)],
    }
    try:
        requests.post('https://onesignal.com/api/v1/notifications', json=data, headers=headers)
    except:
        pass