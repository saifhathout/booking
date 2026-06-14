from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.decorators import player_required
from venues.models import Field, VenueSlot, Booking
from django.utils import timezone
from datetime import datetime, timedelta

@player_required
def browse_fields(request):
    sport_type = request.GET.get('sport_type', '')
    city = request.GET.get('city', '')
    date = request.GET.get('date', '')
    
    fields = Field.objects.filter(is_active=True)
    
    if sport_type:
        fields = fields.filter(sport_type=sport_type)
    if city:
        fields = fields.filter(venue__city__icontains=city)
    
    return render(request, 'booking/field_browse.html', {
        'fields': fields,
        'sport_type': sport_type,
        'city': city,
        'date': date
    })

@player_required
def field_detail(request, field_id):
    field = get_object_or_404(Field, id=field_id, is_active=True)
    
    from datetime import date
    today = date.today()
    tomorrow = today + timedelta(days=1)
    
    blocked_slots = VenueSlot.objects.filter(
        field=field,
        is_available=False,
        date__gte=today
    ).values_list('date', 'start_time', 'end_time')
    
    blocked_set = set()
    for d, st, et in blocked_slots:
        blocked_set.add(f"{d}_{st}")
    
    available_slots = []
    for i in range(7):
        day = today + timedelta(days=i)
        for hour in range(6, 23):
            time_key = f"{day}_{hour}:00:00"
            if time_key not in blocked_set:
                available_slots.append({
                    'id': f"{field_id}_{day}_{hour}",
                    'date': day,
                    'start_time': f"{hour}:00",
                    'end_time': f"{hour+1}:00",
                    'field': field,
                })
    
    return render(request, 'booking/field_detail.html', {
        'field': field,
        'available_slots': available_slots,
        'today': today,
        'tomorrow': tomorrow,
    })


@player_required
def book_slot(request, slot_id):
    parts = slot_id.split('_')
    field_id = parts[0]
    date_str = parts[1]
    hour = int(parts[2])
    
    field = get_object_or_404(Field, id=field_id, is_active=True)
    
    if request.method == 'POST':
        # Validate hour
        if hour >= 23:
            messages.error(request, 'Invalid time slot.')
            return redirect('booking:field_detail', field_id=field.id)
        
        end_hour = hour + 1
        
        slot = VenueSlot.objects.create(
            field=field,
            date=date_str,
            start_time=f"{hour}:00:00",
            end_time=f"{end_hour}:00:00",
            is_available=False
        )
        
        booking = Booking.objects.create(
            field=field,
            player=request.user,
            slot=slot,
            booking_date=date_str,
            start_time=f"{hour}:00",
            end_time=f"{end_hour}:00",
            status='CONFIRMED'
        )
        
        messages.success(request, 'Field booked successfully! 🎉')
        return redirect('booking:history')
    
    return render(request, 'booking/book_slot.html', {
        'field': field,
        'date': date_str,
        'hour': hour,
    })

@player_required
def booking_history(request):
    bookings = Booking.objects.filter(player=request.user).order_by('-created_at')
    return render(request, 'booking/booking_history.html', {'bookings': bookings})