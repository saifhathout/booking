from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from accounts.decorators import player_required, venue_owner_required


@login_required
def home(request):
    if request.user.is_authenticated:
        if request.user.is_player:
            return redirect('dashboard:player_dashboard')
        elif request.user.is_venue_owner:
            return redirect('dashboard:owner_dashboard')
        else:
            return redirect('admin:index')
    return render(request, 'dashboard/home.html')


@player_required
def player_dashboard(request):
    return render(request, 'dashboard/player_dashboard.html')


@venue_owner_required
def owner_dashboard(request):
    return render(request, 'dashboard/owner_dashboard.html')