from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('player/', views.player_dashboard, name='player_dashboard'),
    path('owner/', views.owner_dashboard, name='owner_dashboard'),
]