from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('subscribe/', views.save_subscription, name='subscribe'),
]