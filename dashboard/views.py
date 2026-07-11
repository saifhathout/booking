from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from accounts.decorators import player_required, venue_owner_required
from venues.models import Field, Booking
from django.db.models import Sum

# dashboard/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone

from venues.models import Venue, Field, Booking
from payment.models import InstaPayPayment
from notifications.models import Notification


@login_required
def owner_dashboard(request):
    """لوحة تحكم المالك"""
    
    venues = Venue.objects.filter(owner=request.user)
    
    total_fields = Field.objects.filter(venue__in=venues, is_active=True).count()
    total_bookings = Booking.objects.filter(field__venue__in=venues).count()
    
    total_revenue = Booking.objects.filter(
        field__venue__in=venues,
        status='CONFIRMED'
    ).aggregate(total=Sum('total_price'))['total'] or 0
    
    pending_reviews = InstaPayPayment.objects.filter(
        status__in=['pending', 'manual_review'],
        booking__field__venue__in=venues
    ).select_related(
        'booking',
        'booking__field',
        'booking__player'
    ).order_by('-created_at')
    
    notifications = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).order_by('-created_at')[:20]
    
    all_fields = Field.objects.filter(venue__in=venues, is_active=True)
    
    context = {
        'total_fields': total_fields,
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'pending_reviews': pending_reviews,
        'notifications': notifications,
        'all_fields': all_fields,
        'venues': venues,
        'last_updated': timezone.now(),
    }
    
    return render(request, 'dashboard/owner_dashboard.html', context)


@login_required
def player_dashboard(request):
    """لوحة تحكم اللاعب"""
    
    bookings = Booking.objects.filter(
        player=request.user
    ).exclude(
        status='CANCELLED'
    ).order_by('-created_at')[:10]
    
    total_bookings = Booking.objects.filter(
        player=request.user
    ).exclude(
        status='CANCELLED'
    ).count()
    
    upcoming_bookings = Booking.objects.filter(
        player=request.user,
        booking_date__gte=timezone.now().date(),
        status__in=['CONFIRMED', 'LOCKED', 'PENDING']
    ).count()
    
    confirmed_bookings = Booking.objects.filter(
        player=request.user,
        status='CONFIRMED'
    ).count()
    
    notifications = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).order_by('-created_at')[:10]
    
    context = {
        'bookings': bookings,
        'total_bookings': total_bookings,
        'upcoming_bookings': upcoming_bookings,
        'confirmed_bookings': confirmed_bookings,
        'notifications': notifications,
        'last_updated': timezone.now(),
    }
    
    return render(request, 'dashboard/player_dashboard.html', context)


# @login_required
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
