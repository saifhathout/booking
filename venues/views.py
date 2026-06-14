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
                is_available=False
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