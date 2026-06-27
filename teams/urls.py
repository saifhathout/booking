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
    path('room/<int:room_id>/kick/<int:player_id>/', views.kick_player, name='kick_player'),
    path('room/<int:room_id>/cancel/', views.cancel_room, name='cancel_room'),
        path('room/<int:room_id>/messages/', views.get_chat_messages, name='get_chat_messages'),
    path('room/<int:room_id>/send-message/', views.send_message, name='send_message'),

]