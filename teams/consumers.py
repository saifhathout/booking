# teams/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Room, RoomMessage


class RoomChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'room_{self.room_id}'
        
        # ✅ التحقق من وجود الـ Room
        room = await self.get_room()
        if not room:
            await self.close()
            return
        
        # ✅ انضم للـ Group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get('message')
        username = self.scope['user'].username
        
        # ✅ حفظ الرسالة في الـ DB
        await self.save_message(message)
        
        # ✅ إرسال الرسالة للكل في الـ Group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'username': username,
                'timestamp': str(datethime.now()),
            }
        )
    
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'username': event['username'],
            'timestamp': event['timestamp'],
        }))
    
    @database_sync_to_async
    def get_room(self):
        try:
            return Room.objects.get(id=self.room_id)
        except Room.DoesNotExist:
            return None
    
    @database_sync_to_async
    def save_message(self, message):
        room = Room.objects.get(id=self.room_id)
        RoomMessage.objects.create(
            room=room,
            player=self.scope['user'],
            message=message
        )