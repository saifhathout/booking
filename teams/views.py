from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from accounts.decorators import player_required
from .models import PlayerPost, PlayerRequest, ChatMessage
from datetime import date


@player_required
def find_players(request):
    posts = PlayerPost.objects.filter(is_active=True)
    return render(request, 'teams/find_players.html', {'posts': posts})


@player_required
def create_post(request):
    if request.method == 'POST':
        PlayerPost.objects.create(
            player=request.user,
            sport_type=request.POST.get('sport_type'),
            players_needed=request.POST.get('players_needed', 1),
            city='shbinelkoom',
            date=request.POST.get('date'),
            time=request.POST.get('time') or None,
            description=request.POST.get('description', ''),
        )
        messages.success(request, 'Post created!')
        return redirect('teams:find_players')
    return render(request, 'teams/create_post.html')

@player_required
def join_post(request, post_id):
    post = get_object_or_404(PlayerPost, id=post_id, is_active=True)
    
    if post.player == request.user:
        messages.warning(request, 'This is your own post!')
        return redirect('teams:find_players')
    
    if PlayerRequest.objects.filter(post=post, player=request.user).exists():
        return redirect('teams:chat', post_id=post.id)
    
    # Create request and close post
    PlayerRequest.objects.create(post=post, player=request.user, status='ACCEPTED')
    post.is_active = False
    post.save()
    
    # Auto message
    ChatMessage.objects.create(
        post=post,
        sender=request.user,
        message=f"👋 Hey! Let's play {post.get_sport_type_display()}!"
    )
    
    messages.success(request, 'Connected! Open chat.')
    return redirect('teams:chat', post_id=post.id)


@player_required
def chat_view(request, post_id):
    post = get_object_or_404(PlayerPost, id=post_id)
    
    is_owner = post.player == request.user
    is_joined = PlayerRequest.objects.filter(post=post, player=request.user).exists()
    
    if not is_owner and not is_joined:
        return redirect('teams:find_players')
    
    if request.method == 'POST':
        action = request.POST.get('action', '')
        
        if action == 'send':
            msg = request.POST.get('message')
            if msg:
                ChatMessage.objects.create(post=post, sender=request.user, message=msg)
        
        elif action == 'delete_chat':
            ChatMessage.objects.filter(post=post).delete()
            PlayerRequest.objects.filter(post=post).delete()
            post.delete()
            messages.success(request, 'Chat deleted.')
            return redirect('teams:my_chats')
    
    messages_list = post.messages.all().order_by('created_at')
    
    if is_owner:
        req = PlayerRequest.objects.filter(post=post).first()
        other = req.player if req else None
    else:
        other = post.player
    
    return render(request, 'teams/chat.html', {
        'post': post,
        'messages_list': messages_list,
        'other': other,
    })


@player_required
def my_chats(request):
    posts1 = PlayerPost.objects.filter(player=request.user, is_active=False)
    requests = PlayerRequest.objects.filter(player=request.user)
    posts2 = [r.post for r in requests if not r.post.is_active]
    
    chats = list(posts1) + list(posts2)
    
    return render(request, 'teams/my_chats.html', {'chats': chats})



@player_required
def delete_chat(request, post_id):
    post = get_object_or_404(PlayerPost, id=post_id)
    
    is_owner = post.player == request.user
    is_joined = PlayerRequest.objects.filter(post=post, player=request.user).exists()
    
    if not is_owner and not is_joined:
        return redirect('teams:find_players')
    
    ChatMessage.objects.filter(post=post).delete()
    PlayerRequest.objects.filter(post=post).delete()
    post.delete()
    
    messages.success(request, 'Chat deleted!')
    return redirect('teams:find_players')