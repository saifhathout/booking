# teams/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import GameRoom, RoomChat

User = get_user_model()


class RoomChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'room_{self.room_id}'
        
        if not self.scope['user'].is_authenticated:
            print('❌ User not authenticated')
            await self.close()
            return
        
        room_exists = await self.check_room_exists()
        if not room_exists:
            print('❌ Room not found')
            await self.close()
            return
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        print(f'✅ WebSocket connected for room {self.room_id}')

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        print(f'❌ WebSocket disconnected for room {self.room_id}')

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get('message')
        username = self.scope['user'].username
        
        await self.save_message(message)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'username': username,
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'username': event['username'],
        }))

    @database_sync_to_async
    def check_room_exists(self):
        return GameRoom.objects.filter(id=self.room_id).exists()

    @database_sync_to_async
    def save_message(self, message):
        room = GameRoom.objects.get(id=self.room_id)
        user = self.scope['user']
        
        RoomChat.objects.create(
            room=room,
            sender=user,
            message=message
        )