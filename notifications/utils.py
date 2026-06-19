import json
from .models import PushSubscription
from pywebpush import webpush, WebPushException
from django.conf import settings


def send_push_notification(user, title, body, url='/'):
    """Send push notification to a user's device"""
    subscriptions = PushSubscription.objects.filter(user=user)
    
    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    'endpoint': sub.endpoint,
                    'keys': {
                        'p256dh': sub.p256dh,
                        'auth': sub.auth
                    }
                },
                data=json.dumps({
                    'title': title,
                    'body': body,
                    'url': url,
                }),
                vapid_private_key=settings.WEBPUSH_VAPID_PRIVATE_KEY,
                vapid_claims=settings.WEBPUSH_VAPID_CLAIMS
            )
        except WebPushException as e:
            if e.response and e.response.status_code == 410:
                sub.delete()