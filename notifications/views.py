from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Notification
from .utils import get_unread_count


@login_required
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user)[:50]
    return render(request, 'notifications/list.html', {'notifications': notifications})


@login_required
def mark_read(request, notification_id):
    notif = get_object_or_404(Notification, id=notification_id, user=request.user)
    notif.is_read = True
    notif.save()
    if notif.url:
        return redirect(notif.url)
    return redirect('notifications:list')


@login_required
def unread_count(request):
    count = get_unread_count(request.user)
    return JsonResponse({'count': count})