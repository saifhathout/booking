from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from accounts.decorators import venue_owner_required
from .models import Venue, Field, VenueSlot, Booking
from .forms import VenueForm, FieldForm
from datetime import datetime, timedelta


@venue_owner_required
def venue_list(request):
    venues = Venue.objects.filter(owner=request.user)
    return render(request, 'venues/venue_list.html', {'venues': venues})


@venue_owner_required
def venue_create(request):
    if request.method == 'POST':
        form = VenueForm(request.POST)
        if form.is_valid():
            venue = form.save(commit=False)
            venue.owner = request.user
            venue.save()
            messages.success(request, 'Venue created!')
            return redirect('venues:list')
    else:
        form = VenueForm()
    return render(request, 'venues/venue_form.html', {'form': form})


@venue_owner_required
def venue_detail(request, venue_id):
    venue = get_object_or_404(Venue, id=venue_id, owner=request.user)
    fields = venue.fields.all()
    return render(request, 'venues/venue_detail.html', {'venue': venue, 'fields': fields})


@venue_owner_required
def field_create(request, venue_id):
    venue = get_object_or_404(Venue, id=venue_id, owner=request.user)
    if request.method == 'POST':
        form = FieldForm(request.POST)
        if form.is_valid():
            field = form.save(commit=False)
            field.venue = venue
            field.save()
            messages.success(request, 'Field created!')
            return redirect('venues:venue_detail', venue_id=venue.id)
    else:
        form = FieldForm()
    return render(request, 'venues/field_form.html', {'form': form, 'venue': venue})


@venue_owner_required
def slot_calendar(request, field_id):
    field = get_object_or_404(Field, id=field_id, venue__owner=request.user)
    
    blocked_slots = VenueSlot.objects.filter(
        field=field,
        is_available=False,
        date__gte=datetime.now().date()
    ).order_by('date', 'start_time')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        date_str = request.POST.get('date')
        hour_val = int(request.POST.get('hour'))
        
        if action == 'block':
            VenueSlot.objects.create(
                field=field,
                date=date_str,
                start_time=f"{hour_val}:00:00",
                end_time=f"{hour_val+1}:00:00",
                is_available=False,
                slot_type='BLOCKED'
            )
            messages.success(request, f'Blocked: {date_str} at {hour_val}:00')
            return redirect('venues:slot_calendar', field_id=field.id)
    
    return render(request, 'venues/slot_calendar.html', {
        'field': field,
        'blocked_slots': blocked_slots,
    })
@venue_owner_required
def booking_requests(request):
    venues = Venue.objects.filter(owner=request.user)
    bookings = Booking.objects.filter(field__venue__in=venues).order_by('-created_at')
    return render(request, 'venues/booking_requests.html', {'bookings': bookings})


@venue_owner_required
def handle_booking(request, booking_id, action):
    booking = get_object_or_404(Booking, id=booking_id, field__venue__owner=request.user)
    if action == 'confirm':
        booking.status = 'CONFIRMED'
    elif action == 'reject':
        booking.status = 'REJECTED'
    booking.save()
    return redirect('venues:booking_requests')  


@venue_owner_required
def unblock_slot(request, field_id, date, hour):
    field = get_object_or_404(Field, id=field_id, venue__owner=request.user)
    
    VenueSlot.objects.filter(
        field=field,
        date=date,
        start_time=f"{hour}:00:00",
        is_available=False
    ).delete()
    
    messages.success(request, f'Opened: {date} at {hour}:00')
    return redirect('venues:slot_calendar', field_id=field.id)

@venue_owner_required
def field_schedule_view(request, field_id):
    from datetime import datetime, date, timedelta
    
    field = get_object_or_404(Field, id=field_id, venue__owner=request.user)
    
    today = date.today()
    now = datetime.now()
    current_hour = now.hour
    
    all_slots = VenueSlot.objects.filter(
        field=field,
        date__gte=today,
        date__lte=today + timedelta(days=6)
    ).order_by('date', 'start_time')
    
    bookings = Booking.objects.filter(
        field=field,
        booking_date__gte=today,
        status='CONFIRMED'
    ).select_related('player', 'player__player_profile')
    
    # Build booking map: key -> booking info
    booking_map = {}
    for b in bookings:
        for h in range(b.start_time.hour, b.end_time.hour):
            key = f"{b.booking_date}_{h}"
            booking_map[key] = {
                'player_name': b.player.username,
                'booking_id': b.id,
                'booking_start': b.start_time.hour,
                'booking_end': b.end_time.hour,
            }
    
    # Build slot type map
    slot_map = {}
    for slot in all_slots:
        key = f"{slot.date}_{slot.start_time.hour}"
        if not slot.is_available:
            slot_map[key] = slot.slot_type
    
    def format_time(hour):
        if hour == 0 or hour == 24: return "12:00 AM"
        elif hour < 12: return f"{hour}:00 AM"
        elif hour == 12: return "12:00 PM"
        else: return f"{hour-12}:00 PM"
    
    all_slots_list = []
    for i in range(7):
        day = today + timedelta(days=i)
        day_slots = []
        prev_booking_id = None
        
        for hour in range(1, 25):
            key = f"{day}_{hour}"
            slot_type = slot_map.get(key)
            booking_info = booking_map.get(key)
            
            # Check if this is continuation of same booking
            is_continuation = False
            if booking_info and prev_booking_id == booking_info['booking_id']:
                is_continuation = True
            
            # Check if this is start of a booking
            is_start = False
            if booking_info and booking_info['booking_start'] == hour:
                is_start = True
            
            prev_booking_id = booking_info['booking_id'] if booking_info else None
            
            day_slots.append({
                'hour': hour,
                'time': format_time(hour % 24),
                'slot_type': slot_type,
                'booking': booking_info,
                'is_start': is_start,
                'is_continuation': is_continuation,
            })
        
        all_slots_list.append({'date': day, 'slots': day_slots})
    
    return render(request, 'venues/field_schedule.html', {
        'field': field,
        'all_slots_list': all_slots_list,
        'today': today,
        'current_hour': current_hour,
    })
@venue_owner_required
def booking_details(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related('field', 'field__venue', 'player', 'player__player_profile', 'slot'),
        id=booking_id,
        field__venue__owner=request.user  # التأكد إن صاحب الملعب هو اللي شايف
    )
    
    return render(request, 'venues/booking_details.html', {
        'booking': booking,
    })




@venue_owner_required
def block_slot(request, field_id, date, hour):
    field = get_object_or_404(Field, id=field_id, venue__owner=request.user)
    
    VenueSlot.objects.create(
        field=field,
        date=date,
        start_time=f"{hour}:00:00",
        end_time=f"{hour+1}:00:00",
        is_available=False,
        slot_type='BLOCKED'
    )
    messages.success(request, f'Blocked {date} at {hour}:00')
    return redirect('venues:field_schedule', field_id=field.id)


@venue_owner_required
def unblock_slot(request, field_id, date, hour):
    field = get_object_or_404(Field, id=field_id, venue__owner=request.user)
    
    VenueSlot.objects.filter(
        field=field,
        date=date,
        start_time=f"{hour}:00:00",
        is_available=False
    ).delete()
    
    messages.success(request, f'Opened {date} at {hour}:00')
    return redirect('venues:field_schedule', field_id=field.id)