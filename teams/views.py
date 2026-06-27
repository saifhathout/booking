# teams/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from datetime import date, timedelta
from django.http import JsonResponse
import json

from accounts.decorators import player_required
from .models import GameRoom, RoomPlayer, RoomChat  # ✅ RoomChat
from notifications.utils import create_notification


# ========== GAME ROOMS ==========

@player_required
def room_list(request):
    today = date.today()
    
    rooms = GameRoom.objects.filter(
        is_active=True,
        date__gte=today
    ).exclude(
        status='CANCELLED'
    ).order_by('date', 'time')
    
    return render(request, 'teams/room_list.html', {'rooms': rooms})


@player_required
def create_room(request):
    if request.method == 'POST':
        room = GameRoom.objects.create(
            host=request.user,
            sport_type=request.POST.get('sport_type'),
            title=request.POST.get('title', f"{request.user.username}'s Room"),
            max_players=request.POST.get('max_players', 4),
            date=request.POST.get('date'),
            time=request.POST.get('time') or None,
        )
        RoomPlayer.objects.create(room=room, player=request.user, status='JOINED')
        messages.success(request, 'Room created!')
        return redirect('teams:room_detail', room_id=room.id)
    return render(request, 'teams/create_room.html')


@player_required
def room_detail(request, room_id):
    room = get_object_or_404(GameRoom, id=room_id)
    
    # ✅ استخدم RoomChat مش RoomMessage
    chat_messages = RoomChat.objects.filter(room=room).select_related('sender').order_by('created_at')
    
    players = RoomPlayer.objects.filter(room=room)
    is_in_room = RoomPlayer.objects.filter(room=room, player=request.user).exists()
    is_host = room.host == request.user
    spots_left = room.max_players - players.count()
    
    context = {
        'room': room,
        'chat_messages': chat_messages,
        'players': players,
        'is_in_room': is_in_room,
        'is_host': is_host,
        'spots_left': spots_left,
    }
    
    return render(request, 'teams/room_detail.html', context)


@player_required
def join_room(request, room_id):
    room = get_object_or_404(GameRoom, id=room_id, is_active=True)
    
    if room.players_joined >= room.max_players:
        messages.error(request, 'Room is full!')
        return redirect('teams:room_list')
    
    room_player, created = RoomPlayer.objects.update_or_create(
        room=room,
        player=request.user,
        defaults={'status': 'JOINED'}
    )
    
    if not created and room_player.status == 'JOINED':
        messages.info(request, 'You are already in this room.')
        return redirect('teams:room_detail', room_id=room.id)
    
    create_notification(
        user=room.host,
        title="👥 New player joined!",
        message=f"{request.user.username} joined your room.",
        url=f"/teams/room/{room.id}/"
    )
    
    messages.success(request, '✅ Joined room successfully!')
    return redirect('teams:room_detail', room_id=room.id)


@player_required
def leave_room(request, room_id):
    room = get_object_or_404(GameRoom, id=room_id)
    room_player = get_object_or_404(RoomPlayer, room=room, player=request.user)
    
    if request.user == room.host:
        messages.error(request, "❌ You are the host. Cancel the room instead.")
        return redirect('teams:room_detail', room_id=room.id)
    
    room_player.delete()
    messages.success(request, '✅ Left room successfully!')
    return redirect('teams:room_list')


@player_required
def kick_player(request, room_id, player_id):
    room = get_object_or_404(GameRoom, id=room_id, host=request.user)
    room_player = get_object_or_404(RoomPlayer, room=room, player_id=player_id)
    
    if room_player.player == room.host:
        messages.error(request, "Can't kick the host!")
        return redirect('teams:room_detail', room_id=room.id)
    
    create_notification(
        user=room_player.player,
        title="🚫 You were kicked",
        message=f"You were kicked from {room.title}.",
        url="/teams/room_list/"
    )
    
    room_player.delete()
    messages.success(request, f"✅ {room_player.player.username} kicked!")
    return redirect('teams:room_detail', room_id=room.id)


@player_required
def cancel_room(request, room_id):
    room = get_object_or_404(GameRoom, id=room_id, host=request.user)
    
    players = RoomPlayer.objects.filter(room=room)
    for rp in players:
        if rp.player != request.user:
            create_notification(
                user=rp.player,
                title="❌ Room cancelled",
                message=f"{room.title} has been cancelled by host.",
                url="/teams/room_list/"
            )
    
    room.delete()
    messages.success(request, '✅ Room cancelled!')
    return redirect('teams:room_list')


# ========== CHAT API (HTTP Polling) ==========

@player_required
def get_chat_messages(request, room_id):
    """API لجلب الرسائل الجديدة (HTTP Polling)"""
    room = get_object_or_404(GameRoom, id=room_id)
    
    last_id = request.GET.get('last_id', 0)
    
    messages = RoomChat.objects.filter(
        room=room,
        id__gt=last_id
    ).select_related('sender').order_by('created_at')[:50]
    
    data = []
    for msg in messages:
        data.append({
            'id': msg.id,
            'username': msg.sender.username,
            'message': msg.message,
            'created_at': msg.created_at.strftime('%I:%M %p'),
        })
    
    return JsonResponse({'messages': data})


@player_required
def send_message(request, room_id):
    """إرسال رسالة جديدة"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    room = get_object_or_404(GameRoom, id=room_id)
    
    if not RoomPlayer.objects.filter(room=room, player=request.user).exists():
        return JsonResponse({'success': False, 'error': 'Not a member'})
    
    try:
        data = json.loads(request.body)
        message = data.get('message', '').strip()
    except:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'})
    
    if not message:
        return JsonResponse({'success': False, 'error': 'Empty message'})
    
    chat = RoomChat.objects.create(
        room=room,
        sender=request.user,
        message=message
    )
    
    return JsonResponse({'success': True, 'id': chat.id})