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


from .utils import format_time, get_booked_set, display_hour

@player_required
def field_detail(request, field_id):
    field = get_object_or_404(Field, id=field_id, is_active=True)
    
    today = date.today()
    now = datetime.now()
    current_hour = now.hour
    
    booked_set = get_booked_set(field, today, today + timedelta(days=6))
    
    all_slots_list = []
    for i in range(7):
        day = today + timedelta(days=i)
        day_slots = []
        
        for hour in range(1, 25):  # 1 AM to 12 AM
            is_booked = f"{day}_{hour}" in booked_set
            day_slots.append({
                'hour': hour,
                'time': format_time(hour % 24),
                'is_booked': is_booked,
                'slot_id': f"{field_id}_{day}_{hour}" if not is_booked else None,
            })
        
        if day_slots:
            all_slots_list.append({'date': day, 'slots': day_slots})
    
    return render(request, 'booking/field_detail.html', {
        'field': field,
        'all_slots_list': all_slots_list,
        'today': today,
        'current_hour': current_hour,
    })
from .utils import normalize_hour, get_slot_range, format_time

@player_required
def book_slot(request, slot_id):
    parts = slot_id.split('_')
    field_id = parts[0]
    date_str = parts[1]
    display_hour = int(parts[2])
    
    field = get_object_or_404(Field, id=field_id, is_active=True)
    store_hour = normalize_hour(display_hour)
    
    if request.method == 'POST':
        duration = int(request.POST.get('duration', 1))
        slot_range = get_slot_range(date_str, display_hour, duration)
        
        # Check all slots
        for s in slot_range:
            taken = VenueSlot.objects.filter(
                field=field, date=s['date'],
                start_time=s['start_time'], is_available=False
            ).exists()
            if taken:
                messages.error(request, f'❌ {s["date"]} {format_time(s["hour"])} is already booked!')
                return redirect('booking:field_detail', field_id=field.id)
        
        # Create and book slots
        slots_to_book = []
        for s in slot_range:
            slot, _ = VenueSlot.objects.get_or_create(
                field=field, date=s['date'], start_time=s['start_time'],
                defaults={'end_time': s['end_time'], 'is_available': True}
            )
            slots_to_book.append(slot)
        
        for slot in slots_to_book:
            slot.is_available = False
            slot.slot_type = 'BOOKED'
            slot.save()
        
        total = field.price_per_hour * duration
        
        first_slot = slot_range[0]
        last_slot = slot_range[-1]
        
        Booking.objects.create(
            field=field, player=request.user, slot=slots_to_book[0],
            booking_date=first_slot['date'],
            start_time=first_slot['start_time'],
            end_time=last_slot['end_time'],
            status='CONFIRMED'
        )
        
        messages.success(request, f'⚡ Booked {duration} hour(s) for ${total}!')
        return redirect('booking:history')
    
    return render(request, 'booking/book_slot.html', {
        'field': field, 'date': date_str, 'hour': display_hour, 'price': field.price_per_hour,
    })
@player_required
def booking_history(request):
    today = date.today()
    now = datetime.now().time()
    
    all_bookings = Booking.objects.select_related(
        'field', 'field__venue', 'player'
    ).filter(player=request.user).exclude(status='CANCELLED').order_by('booking_date', 'start_time')
    
    upcoming_bookings = []
    past_bookings = []
    
    for booking in all_bookings:
        if booking.booking_date > today:
            upcoming_bookings.append(booking)
        elif booking.booking_date == today:
            booking_time = datetime.strptime(str(booking.start_time), '%H:%M:%S').time()
            if booking_time >= now:
                upcoming_bookings.append(booking)
            else:
                past_bookings.append(booking)
        else:
            past_bookings.append(booking)
    
    return render(request, 'booking/booking_history.html', {
        'upcoming_bookings': upcoming_bookings,
        'past_bookings': past_bookings,
    })


from .utils import normalize_hour, get_slot_range

@player_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, player=request.user)
    if booking.status == 'CANCELLED':
        messages.warning(request, 'Already cancelled.')
        return redirect('booking:history')  
    start_h = booking.start_time.hour
    end_h = booking.end_time.hour
    
    if end_h == 0:
        end_h = 24
    
    duration = end_h - start_h if end_h > start_h else 1
    
    # Delete the booking first (breaks FK to slot)
    booking.status = 'CANCELLED'
    booking.save()
    
    # Now safe to delete slots
    date_str = booking.booking_date.strftime('%Y-%m-%d')
    store_hour = start_h
    
    for i in range(duration):
        h = (store_hour + i) % 24
        VenueSlot.objects.filter(
            field=booking.field,
            date=date_str,
            start_time=f"{h}:00:00"
        ).delete()
    
    messages.success(request, 'Booking cancelled!')
    return redirect('booking:history')