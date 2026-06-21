from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list, name='list'),
    path('read/<int:notification_id>/', views.mark_read, name='read'),
    path('api/count/', views.unread_count, name='count'),
]