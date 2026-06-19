from django.conf import settings

def webpush_settings(request):
    return {
        'webpush_public_key': getattr(settings, 'WEBPUSH_VAPID_PUBLIC_KEY', ''),
    }