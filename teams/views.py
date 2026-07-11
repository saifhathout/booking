# teams/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone

from accounts.decorators import player_required
from notifications.utils import create_notification
from .models import GameRoom, RoomPlayer, RoomChat  # ✅ GameRoom


@player_required
def room_list(request):
    rooms = GameRoom.objects.filter(status='OPEN').order_by('-created_at')
    return render(request, 'teams/room_list.html', {'rooms': rooms})


# teams/views.py

@player_required
def create_room(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        sport_type = request.POST.get('sport_type')
        max_players = request.POST.get('max_players', 4)
        date = request.POST.get('date')
        time = request.POST.get('time')
        
        # ✅ استخدم الحقول الموجودة فقط
        room = GameRoom.objects.create(
            host=request.user,
            title=title,
            sport_type=sport_type,
            max_players=int(max_players),
            date=date,
            time=time,
            status='OPEN'
        )
        
        # ✅ المضيف ينضم تلقائياً
        RoomPlayer.objects.create(room=room, player=request.user)
        
        messages.success(request, f'✅ Room "{room.title}" created successfully!')
        return redirect('teams:room_detail', room_id=room.id)
    
    return render(request, 'teams/create_room.html')


@player_required
def room_detail(request, room_id):
    room = get_object_or_404(GameRoom, id=room_id)
    players = RoomPlayer.objects.filter(room=room).select_related('player')
    chat_messages = RoomChat.objects.filter(room=room).order_by('created_at')[:50]
    
    players_count = players.count()
    is_host = request.user == room.host
    is_in_room = RoomPlayer.objects.filter(room=room, player=request.user).exists()
    spots_left = room.max_players - players_count
    
    context = {
        'room': room,
        'players': players,
        'chat_messages': chat_messages,
        'is_host': is_host,
        'is_in_room': is_in_room,
        'spots_left': spots_left,
    }
    return render(request, 'teams/room_detail.html', context)


@player_required
def join_room(request, room_id):
    room = get_object_or_404(GameRoom, id=room_id)
    
    players_count = RoomPlayer.objects.filter(room=room).count()
    
    if players_count >= room.max_players:
        messages.error(request, '❌ This room is full!')
        return redirect('teams:room_list')
    
    if RoomPlayer.objects.filter(room=room, player=request.user).exists():
        messages.warning(request, '⚠️ You are already in this room!')
        return redirect('teams:room_detail', room_id=room.id)
    
    RoomPlayer.objects.create(room=room, player=request.user)
    
    if players_count + 1 >= room.max_players:
        room.status = 'FULL'
        room.save()
    
    create_notification(
        user=room.host,
        title=f"👥 New player joined {room.title}",
        message=f"{request.user.username} joined your room.",
        url=f"/teams/rooms/{room.id}/"
    )
    
    messages.success(request, f'✅ You joined "{room.title}"!')
    return redirect('teams:room_detail', room_id=room.id)


@player_required
def leave_room(request, room_id):
    room = get_object_or_404(GameRoom, id=room_id)
    
    if request.user == room.host:
        messages.error(request, '❌ You are the host. Cancel the room instead.')
        return redirect('teams:room_detail', room_id=room.id)
    
    RoomPlayer.objects.filter(room=room, player=request.user).delete()
    
    if room.status == 'FULL':
        room.status = 'OPEN'
        room.save()
    
    messages.success(request, f'✅ You left "{room.title}".')
    return redirect('teams:room_list')


@player_required
def cancel_room(request, room_id):
    room = get_object_or_404(GameRoom, id=room_id, host=request.user)
    
    room.status = 'CANCELLED'
    room.save()
    
    for player in RoomPlayer.objects.filter(room=room).select_related('player'):
        if player.player != request.user:
            create_notification(
                user=player.player,
                title=f"❌ Room cancelled: {room.title}",
                message=f"{request.user.username} cancelled the room.",
                url="/teams/rooms/"
            )
    
    messages.success(request, f'✅ Room "{room.title}" cancelled.')
    return redirect('teams:room_list')


@player_required
def kick_player(request, room_id, player_id):
    room = get_object_or_404(GameRoom, id=room_id, host=request.user)
    
    if request.user.id == player_id:
        messages.error(request, '❌ You cannot kick yourself.')
        return redirect('teams:room_detail', room_id=room.id)
    
    RoomPlayer.objects.filter(room=room, player_id=player_id).delete()
    
    if room.status == 'FULL':
        room.status = 'OPEN'
        room.save()
    
    messages.success(request, '✅ Player kicked from the room.')
    return redirect('teams:room_detail', room_id=room.id)


# teams/views.py

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.decorators import player_required
from .models import GameRoom, RoomPlayer, RoomChat
import json


@player_required
def send_message(request, room_id):
    """إرسال رسالة في الشات"""
    
    # ✅ التحقق من وجود الغرفة
    room = get_object_or_404(GameRoom, id=room_id)
    
    # ✅ التحقق من أن المستخدم في الغرفة
    if not RoomPlayer.objects.filter(room=room, player=request.user).exists():
        return JsonResponse({
            'success': False, 
            'error': 'You are not in this room.'
        }, status=403)
    
    # ✅ التحقق من الطريقة
    if request.method != 'POST':
        return JsonResponse({
            'success': False, 
            'error': 'Invalid method.'
        }, status=405)
    
    try:
        # ✅ قراءة البيانات
        data = json.loads(request.body)
        message = data.get('message', '').strip()
        
        # ✅ التحقق من الرسالة
        if not message:
            return JsonResponse({
                'success': False, 
                'error': 'Message cannot be empty.'
            }, status=400)
        
        # ✅ حفظ الرسالة
        chat = RoomChat.objects.create(
            room=room,
            sender=request.user,
            message=message
        )
        
        return JsonResponse({
            'success': True, 
            'message_id': chat.id,
            'message': message,
            'username': request.user.username,
            'created_at': chat.created_at.strftime('%I:%M %p')
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False, 
            'error': 'Invalid JSON.'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'error': str(e)
        }, status=500)

@player_required
def get_messages(request, room_id):
    room = get_object_or_404(GameRoom, id=room_id)
    last_id = request.GET.get('last_id', 0)
    
    messages_list = RoomChat.objects.filter(
        room=room,
        id__gt=last_id
    ).order_by('created_at')[:50]
    
    data = {
        'messages': [
            {
                'id': msg.id,
                'username': msg.sender.username,
                'message': msg.message,
                'created_at': msg.created_at.strftime('%I:%M %p'),
            }
            for msg in messages_list
        ]
    }
    return JsonResponse(data)