from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.decorators import player_required
from venues.models import Field, VenueSlot, Booking
from datetime import datetime, timedelta, date


@player_required
def browse_fields(request):
    sport_type = request.GET.get('sport_type', '')
    city = request.GET.get('city', '')
    date_val = request.GET.get('date', '')
    
    fields = Field.objects.filter(is_active=True)
    
    if sport_type:
        fields = fields.filter(sport_type=sport_type)
    if city:
        fields = fields.filter(venue__city__icontains=city)
    
    return render(request, 'booking/field_browse.html', {
        'fields': fields,
        'sport_type': sport_type,
        'city': city,
        'date': date_val,
    })


@player_required
def field_detail(request, field_id):
    field = get_object_or_404(Field, id=field_id, is_active=True)
    
    today = date.today()
    tomorrow = today + timedelta(days=1)
    
    all_slots = VenueSlot.objects.filter(
        field=field,
        date__gte=today,
        date__lte=today + timedelta(days=6)
    )
    
    booked_set = set()
    for slot in all_slots:
        if not slot.is_available:
            booked_set.add(f"{slot.date}_{slot.start_time.hour}")
    
    def format_time(hour):
        if hour == 0 or hour == 24:
            return "12:00 AM"
        elif hour < 12:
            return f"{hour}:00 AM"
        elif hour == 12:
            return "12:00 PM"
        else:
            return f"{hour-12}:00 PM"
    
    all_slots_list = []
    for i in range(7):
        day = today + timedelta(days=i)
        day_slots = []
        for hour in range(1, 25):  # 1 AM to 12 AM (midnight)
            is_booked = f"{day}_{hour}" in booked_set
            # hour 24 = midnight of next day
            display_hour = hour if hour < 24 else 0
            day_slots.append({
                'hour': hour,
                'time': format_time(hour % 24),
                'is_booked': is_booked,
                'slot_id': f"{field_id}_{day}_{hour}" if not is_booked else None,
            })
        all_slots_list.append({
            'date': day,
            'slots': day_slots,
        })
    
    return render(request, 'booking/field_detail.html', {
        'field': field,
        'all_slots_list': all_slots_list,
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
    
    if hour > 24:
        messages.error(request, 'Invalid time slot.')
        return redirect('booking:field_detail', field_id=field.id)
    
    slot_taken = VenueSlot.objects.filter(
        field=field,
        date=date_str,
        start_time=f"{hour}:00:00",
        is_available=False
    ).exists()
    
    if slot_taken:
        messages.error(request, '❌ This slot is already booked!')
        return redirect('booking:field_detail', field_id=field.id)
    
    player_already_booked = Booking.objects.filter(
        player=request.user,
        booking_date=date_str,
        start_time=f"{hour}:00",
        status='CONFIRMED'
    ).exists()
    
    if player_already_booked:
        messages.error(request, '⚠️ You already have a booking at this time!')
        return redirect('booking:history')
    
    def format_time(h):
        if h == 0 or h == 24: return "12:00 AM"
        elif h < 12: return f"{h}:00 AM"
        elif h == 12: return "12:00 PM"
        else: return f"{h-12}:00 PM"
    
    if request.method == 'POST':
        end_hour = hour + 1 if hour < 24 else 1
        
        slot = VenueSlot.objects.create(
            field=field,
            date=date_str,
            start_time=f"{hour}:00:00",
            end_time=f"{end_hour}:00:00" if end_hour <= 24 else "1:00:00",
            is_available=False
        )
        
        booking = Booking.objects.create(
            field=field,
            player=request.user,
            slot=slot,
            booking_date=date_str,
            start_time=f"{hour}:00",
            end_time=f"{end_hour}:00" if end_hour <= 24 else "1:00",
            status='CONFIRMED'
        )
        
        messages.success(request, '⚡ Field booked successfully!')
        return redirect('booking:history')
    
    return render(request, 'booking/book_slot.html', {
        'field': field,
        'date': date_str,
        'hour': hour,
        'time_display': format_time(hour),
    })

@player_required
def booking_history(request):
    bookings = Booking.objects.filter(player=request.user).order_by('-created_at')
    return render(request, 'booking/booking_history.html', {'bookings': bookings})