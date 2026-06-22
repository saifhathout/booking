from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from accounts.decorators import player_required
from .models import GameRoom, RoomPlayer, RoomChat


# ========== GAME ROOMS ==========

@player_required
def room_list(request):
    rooms = GameRoom.objects.filter(is_active=True).order_by('-created_at')
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
            city=request.POST.get('city', 'Cairo'),
        )
        RoomPlayer.objects.create(room=room, player=request.user, status='JOINED')
        messages.success(request, 'Room created!')
        return redirect('teams:room_detail', room_id=room.id)
    return render(request, 'teams/create_room.html')


@player_required
def room_detail(request, room_id):
    room = get_object_or_404(GameRoom, id=room_id)
    players = room.players.filter(status='JOINED').select_related('player')
    chat_messages = room.messages.all().select_related('sender')
    is_in_room = players.filter(player=request.user).exists()
    is_host = room.host == request.user
    
    if request.method == 'POST':
        msg = request.POST.get('message')
        if msg:
            RoomChat.objects.create(room=room, sender=request.user, message=msg)
        return redirect('teams:room_detail', room_id=room.id)
    
    return render(request, 'teams/room_detail.html', {
        'room': room,
        'players': players,
        'chat_messages': chat_messages,
        'is_in_room': is_in_room,
        'is_host': is_host,
        'spots_left': room.spots_left(),
    })


@player_required
def join_room(request, room_id):
    room = get_object_or_404(GameRoom, id=room_id, is_active=True)
    
    if room.players.filter(player=request.user).exists():
        return redirect('teams:room_detail', room_id=room.id)
    
    if room.spots_left() <= 0:
        messages.error(request, 'Room is full!')
        return redirect('teams:room_list')
    
    RoomPlayer.objects.create(room=room, player=request.user)
    RoomChat.objects.create(
        room=room, sender=request.user,
        message=f"👋 {request.user.username} joined the room!"
    )
    
    if room.spots_left() <= 0:
        room.is_active = False
        room.save()
    
    messages.success(request, 'Joined room!')
    return redirect('teams:room_detail', room_id=room.id)


@player_required
def leave_room(request, room_id):
    room = get_object_or_404(GameRoom, id=room_id)
    
    RoomPlayer.objects.filter(room=room, player=request.user).update(status='LEFT')
    RoomChat.objects.create(
        room=room, sender=request.user,
        message=f"👋 {request.user.username} left the room."
    )
    
    room.is_active = True
    room.save()
    
    messages.success(request, 'Left room.')
    return redirect('teams:room_list')