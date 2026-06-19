import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import PushSubscription
from pywebpush import webpush, WebPushException
from django.conf import settings

@csrf_exempt
@login_required
def save_subscription(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    
    data = json.loads(request.body)
    
    PushSubscription.objects.get_or_create(
        user=request.user,
        endpoint=data['endpoint'],
        defaults={
            'p256dh': data['keys']['p256dh'],
            'auth': data['keys']['auth']
        }
    )
    
    return JsonResponse({'status': 'ok'})


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
                    'icon': '/static/icons/icon-192x192.png',
                    'badge': '/static/icons/icon-72x72.png',
                }),
                vapid_private_key=settings.WEBPUSH_VAPID_PRIVATE_KEY,
                vapid_claims=settings.WEBPUSH_VAPID_CLAIMS
            )
        except WebPushException as e:
            if e.response and e.response.status_code == 410:
                sub.delete()    
