from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, date, timedelta
from accounts.decorators import venue_owner_required, player_required
from .models import Venue, Field, VenueSlot, Booking
from .forms import VenueForm, FieldForm
from django.db.models import Sum, Count
from django.db import transaction, IntegrityError



# ========== VENUE CRUD ==========

@venue_owner_required
def venue_list(request):
    venues = Venue.objects.filter(owner=request.user)
    return render(request, 'venues/venue_list.html', {'venues': venues})


@venue_owner_required
def venue_create(request):
    if request.method == 'POST':
        form = VenueForm(request.POST, request.FILES)
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


# ========== SCHEDULE ==========

@venue_owner_required
def field_schedule_view(request, field_id):
    field = get_object_or_404(Field, id=field_id, venue__owner=request.user)
    
    today = date.today()
    now = datetime.now()
    current_hour = now.hour
    
    all_slots = VenueSlot.objects.filter(
        field=field, date__gte=today, date__lte=today + timedelta(days=6)
    ).order_by('date', 'start_time')
    
    bookings = Booking.objects.filter(
        field=field, booking_date__gte=today, status='CONFIRMED'
    ).select_related('player')
    
    booking_map = {}
    for b in bookings:
        start_h = b.start_time.hour
        end_h = b.end_time.hour if b.end_time.hour > 0 else 24
        if end_h <= start_h: end_h = start_h + 1
        for h in range(start_h, end_h):
            key = f"{b.booking_date}_{h % 24}"
            booking_map[key] = {'player_name': b.player.username, 'booking_id': b.id}
            if h % 24 == 0:
                booking_map[f"{b.booking_date}_24"] = booking_map[key]
    
    slot_map = {}
    for slot in all_slots:
        if not slot.is_available:
            h = slot.start_time.hour
            key = f"{slot.date}_{h}"
            slot_map[key] = slot.slot_type
            if h == 0:
                slot_map[f"{slot.date}_24"] = slot.slot_type
    
    def format_time(hour):
        if hour == 0 or hour == 24: return "12:00 AM"
        elif hour < 12: return f"{hour}:00 AM"
        elif hour == 12: return "12:00 PM"
        else: return f"{hour-12}:00 PM"
    
    all_slots_list = []
    for i in range(7):
        day = today + timedelta(days=i)
        day_slots = []
        prev_bid = None
        for hour in range(1, 25):
            key = f"{day}_{hour}"
            st = slot_map.get(key)
            bi = booking_map.get(key)
            is_cont = bi and prev_bid == bi['booking_id'] if bi else False
            is_start = bi and not is_cont if bi else False
            prev_bid = bi['booking_id'] if bi else None
            day_slots.append({'hour': hour, 'time': format_time(hour % 24), 'slot_type': st, 'booking': bi, 'is_start': is_start, 'is_continuation': is_cont})
        all_slots_list.append({'date': day, 'slots': day_slots})
    
    return render(request, 'venues/field_schedule.html', {'field': field, 'all_slots_list': all_slots_list, 'today': today, 'current_hour': current_hour})


# ========== BLOCK / UNBLOCK ==========

@venue_owner_required
def block_slot(request, field_id, date, hour):
    field = get_object_or_404(Field, id=field_id, venue__owner=request.user)
    store_hour = hour % 24
    
    end_time = "23:59:00" if store_hour == 23 else f"{store_hour+1}:00:00"
    
    try:
        with transaction.atomic():
            slot, created = VenueSlot.objects.get_or_create(
                field=field, date=date, start_time=f"{store_hour}:00:00",
                defaults={'end_time': end_time, 'is_available': False, 'slot_type': 'BLOCKED'}
            )
            
            if not created:
                if not slot.is_available:
                    messages.warning(request, 'Slot already taken!')
                    return redirect('venues:field_schedule', field_id=field.id)
                slot.is_available = False
                slot.slot_type = 'BLOCKED'
                slot.save()
            
            messages.success(request, f'Blocked!')
    except IntegrityError:
        messages.error(request, 'Failed to block!')
    
    return redirect('venues:field_schedule', field_id=field.id)

@venue_owner_required
def unblock_slot(request, field_id, date, hour):
    field = get_object_or_404(Field, id=field_id, venue__owner=request.user)
    store_hour = hour % 24
    VenueSlot.objects.filter(field=field, date=date, start_time=f"{store_hour}:00:00", is_available=False).delete()
    messages.success(request, f'Opened {date} at {hour}:00')
    return redirect('venues:field_schedule', field_id=field.id)


# ========== BOOKINGS ==========

@venue_owner_required
def booking_requests(request):
    venues = Venue.objects.filter(owner=request.user)
    bookings = Booking.objects.filter(field__venue__in=venues).order_by('-created_at')
    return render(request, 'venues/booking_requests.html', {'bookings': bookings})


# venues/views.py (أضف هذه الدالة في نهاية الملف)

from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from payment.models import InstaPayPayment
from notifications.models import Notification


# venues/views.py

@login_required
def owner_dashboard(request):
    """لوحة تحكم المالك - تعرض الإحصائيات والإشعارات وطلبات المراجعة"""
    
    # ✅ 1. الإحصائيات
    venues = Venue.objects.filter(owner=request.user)
    total_fields = Field.objects.filter(venue__in=venues).count()
    total_bookings = Booking.objects.filter(field__venue__in=venues).count()
    total_revenue = Booking.objects.filter(
        field__venue__in=venues, 
        status='CONFIRMED'
    ).aggregate(total=Sum('field__price_per_hour'))['total'] or 0
    
    # ✅ 2. جميع الملاعب للمالك
    all_fields = Field.objects.filter(venue__in=venues, is_active=True)
    
    # ✅ 3. الإشعارات غير المقروءة
    from notifications.models import Notification
    notifications = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).order_by('-created_at')[:20]
    
    # ✅ 4. طلبات الدفع في انتظار المراجعة
    from payment.models import InstaPayPayment
    pending_reviews = InstaPayPayment.objects.filter(
        status='manual_review',
        booking__field__venue__in=venues
    ).select_related('booking', 'booking__field', 'booking__player').order_by('-created_at')
    
    context = {
        'total_fields': total_fields,
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'all_fields': all_fields,
        'notifications': notifications,
        'pending_reviews': pending_reviews,
        'unread_count': notifications.count(),
    }
    
    # ✅ استخدم الـ template بتاع dashboard (موجود)
    return render(request, 'dashboard/owner_dashboard.html', context)

from payment.models import InstaPayPayment


@venue_owner_required
def booking_details(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related('field', 'player', 'field__venue'),
        id=booking_id,
        field__venue__owner=request.user
    )
    
    # ✅ جلب صورة الدفع
    try:
        payment = InstaPayPayment.objects.get(booking=booking)
    except InstaPayPayment.DoesNotExist:
        payment = None
    
    return render(request, 'venues/booking_details.html', {
        'booking': booking,
        'payment': payment,
    })






    # venues/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from accounts.decorators import venue_owner_required
from .models import Venue, Field
from .forms import FieldForm


@venue_owner_required
def field_edit(request, field_id):
    """تعديل بيانات الملعب (سعر، صورة، اسم، تفاصيل)"""
    field = get_object_or_404(Field, id=field_id, venue__owner=request.user)
    
    if request.method == 'POST':
        form = FieldForm(request.POST, request.FILES, instance=field)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ تم تحديث بيانات الملعب بنجاح!')
            return redirect('venues:field_schedule', field_id=field.id)
    else:
        form = FieldForm(instance=field)
    
    return render(request, 'venues/field_edit.html', {
        'form': form,
        'field': field,
    })