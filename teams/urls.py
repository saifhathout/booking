from django.urls import path
from . import views

app_name = 'teams'

urlpatterns = [
    # Game Rooms
    path('rooms/', views.room_list, name='room_list'),
    path('rooms/create/', views.create_room, name='create_room'),
    path('rooms/<int:room_id>/', views.room_detail, name='room_detail'),
    path('rooms/<int:room_id>/join/', views.join_room, name='join_room'),
    path('rooms/<int:room_id>/leave/', views.leave_room, name='leave_room'),
]