from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from accounts.decorators import player_required, venue_owner_required
from venues.models import Field, Booking
from django.db.models import Sum


@login_required
def home(request):
    if request.user.is_authenticated:
        if request.user.is_player:
            return redirect('booking:browse')
        elif request.user.is_venue_owner:
            return redirect('dashboard:owner_dashboard')
    return redirect('accounts:login')


@player_required
def player_dashboard(request):
    fields = Field.objects.filter(is_active=True)
    return render(request, 'dashboard/player_dashboard.html', {
        'fields': fields,
    })

@venue_owner_required
def owner_dashboard(request):
    fields = Field.objects.filter(venue__owner=request.user)
    bookings = Booking.objects.filter(field__in=fields, status='CONFIRMED')
    
    return render(request, 'dashboard/owner_dashboard.html', {
        'fields': fields,
        'total_bookings': bookings.count(),
        'total_revenue': sum(b.field.price_per_hour for b in bookings),
    })