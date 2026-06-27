# teams/routing.py

from django.urls import path
from .consumers import RoomChatConsumer

websocket_urlpatterns = [
    path('ws/room/<int:room_id>/', RoomChatConsumer.as_asgi()),
]