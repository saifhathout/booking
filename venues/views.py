# venues/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime, date, timedelta
from django.db.models import Sum, Count
from django.db import transaction, IntegrityError

from accounts.decorators import venue_owner_required, player_required
from .models import Venue, Field, VenueSlot, Booking
from .forms import VenueForm, FieldForm
from payment.models import InstaPayPayment
from notifications.models import Notification
from notifications.utils import create_notification


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
            messages.success(request, '✅ Venue created successfully!')
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
            messages.success(request, '✅ Field created successfully!')
            return redirect('venues:venue_detail', venue_id=venue.id)
    else:
        form = FieldForm()
    return render(request, 'venues/field_form.html', {'form': form, 'venue': venue})


@venue_owner_required
def field_edit(request, field_id):
    """تعديل بيانات الملعب"""
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
        # ✅ استخدام السلوتات بدلاً من الحسابات
        for slot in b.slots.all():
            key = f"{slot.date}_{slot.start_time.hour}"
            booking_map[key] = {
                'player_name': b.player.username,
                'booking_id': b.id,
                'is_locked': False
            }
    
    slot_map = {}
    for slot in all_slots:
        if not slot.is_available:
            key = f"{slot.date}_{slot.start_time.hour}"
            slot_map[key] = {
                'type': slot.slot_type,
                'is_locked': slot.slot_type == 'LOCKED'
            }
    
    def format_time(hour):
        if hour == 0 or hour == 24: return "12:00 AM"
        elif hour < 12: return f"{hour}:00 AM"
        elif hour == 12: return "12:00 PM"
        else: return f"{hour-12}:00 PM"
    
    all_slots_list = []
    for i in range(7):
        day = today + timedelta(days=i)
        day_slots = []
        
        for hour in range(1, 25):
            key = f"{day}_{hour % 24}"
            
            # ✅ جلب البيانات
            slot_data = slot_map.get(key)
            booking_data = booking_map.get(key)
            
            is_booked = booking_data is not None
            is_locked = slot_data and slot_data.get('is_locked', False)
            is_blocked = slot_data and slot_data.get('type') == 'BLOCKED'
            
            day_slots.append({
                'hour': hour,
                'time': format_time(hour % 24),
                'is_booked': is_booked,
                'is_locked': is_locked,
                'is_blocked': is_blocked,
                'booking': booking_data,
                'slot_type': slot_data.get('type') if slot_data else None,
            })
        
        all_slots_list.append({'date': day, 'slots': day_slots})
    
    return render(request, 'venues/field_schedule.html', {
        'field': field,
        'all_slots_list': all_slots_list,
        'today': today,
        'current_hour': current_hour,
    })


# ========== BLOCK / UNBLOCK ==========

@venue_owner_required
def block_slot(request, field_id, date, hour):
    field = get_object_or_404(Field, id=field_id, venue__owner=request.user)
    store_hour = hour % 24
    
    # ✅ تصحيح end_time
    if store_hour == 23:
        end_time = "00:00:00"
    else:
        end_time = f"{store_hour+1}:00:00"
    
    try:
        with transaction.atomic():
            slot, created = VenueSlot.objects.get_or_create(
                field=field, 
                date=date, 
                start_time=f"{store_hour}:00:00",
                defaults={
                    'end_time': end_time, 
                    'is_available': False, 
                    'slot_type': 'BLOCKED'
                }
            )
            
            if not created:
                if not slot.is_available:
                    messages.warning(request, '⚠️ هذا السلوت غير متاح حالياً!')
                    return redirect('venues:field_schedule', field_id=field.id)
                slot.is_available = False
                slot.slot_type = 'BLOCKED'
                slot.save()
            
            messages.success(request, f'✅ تم حظر السلوت {hour}:00')
    except IntegrityError:
        messages.error(request, '❌ فشل حظر السلوت')
    
    return redirect('venues:field_schedule', field_id=field.id)


@venue_owner_required
def unblock_slot(request, field_id, date, hour):
    field = get_object_or_404(Field, id=field_id, venue__owner=request.user)
    store_hour = hour % 24
    
    deleted = VenueSlot.objects.filter(
        field=field, 
        date=date, 
        start_time=f"{store_hour}:00:00", 
        is_available=False,
        slot_type='BLOCKED'
    ).delete()
    
    if deleted[0] > 0:
        messages.success(request, f'✅ تم فتح السلوت {hour}:00')
    else:
        messages.warning(request, '⚠️ السلوت غير موجود أو غير محظور')
    
    return redirect('venues:field_schedule', field_id=field.id)


# ========== OWNER DASHBOARD ==========

# venues/views.py

@login_required
def owner_dashboard(request):
    """لوحة تحكم المالك"""
    
    venues = Venue.objects.filter(owner=request.user)
    
    # ✅ 1. الإحصائيات
    total_fields = Field.objects.filter(venue__in=venues).count()
    total_bookings = Booking.objects.filter(field__venue__in=venues).count()
    
    total_revenue = Booking.objects.filter(
        field__venue__in=venues, 
        status='CONFIRMED'
    ).aggregate(total=Sum('total_price'))['total'] or 0
    
    # ✅ 2. حساب التغير في الإيرادات (اختياري)
    # احسب إيرادات الشهر الماضي والشهر الحالي
    from django.db.models.functions import TruncMonth
    current_month = timezone.now().month
    last_month = timezone.now().month - 1 or 12
    
    current_revenue = Booking.objects.filter(
        field__venue__in=venues,
        status='CONFIRMED',
        created_at__month=current_month
    ).aggregate(total=Sum('total_price'))['total'] or 0
    
    last_month_revenue = Booking.objects.filter(
        field__venue__in=venues,
        status='CONFIRMED',
        created_at__month=last_month
    ).aggregate(total=Sum('total_price'))['total'] or 1  # تجنب القسمة على صفر
    
    revenue_change = int(((current_revenue - last_month_revenue) / last_month_revenue) * 100)
    
    # ✅ 3. طلبات الدفع في انتظار المراجعة
    pending_reviews = InstaPayPayment.objects.filter(
        status__in=['pending', 'manual_review'],
        booking__field__venue__in=venues
    ).select_related(
        'booking', 
        'booking__field', 
        'booking__player'
    ).order_by('-created_at')
    
    # ✅ 4. الإشعارات غير المقروءة (مع إضافة notification_type مؤقتاً)
    notifications = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).order_by('-created_at')[:10]
    
    # ✅ 5. الملاعب (أول 4 فقط)
    all_fields = Field.objects.filter(venue__in=venues, is_active=True)[:4]
    
    # ✅ 6. آخر تحديث
    last_updated = timezone.now()
    
    context = {
        'total_fields': total_fields,
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'revenue_change': revenue_change,
        'pending_reviews': pending_reviews,
        'notifications': notifications,
        'all_fields': all_fields,
        'last_updated': last_updated,
        'venues': venues,
    }
    
    return render(request, 'venues/owner_dashboard.html', context)


# ========== BOOKING DETAILS ==========

@venue_owner_required
def booking_details(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related('field', 'player', 'field__venue'),
        id=booking_id,
        field__venue__owner=request.user
    )
    
    # ✅ جلب الدفع
    try:
        payment = InstaPayPayment.objects.get(booking=booking)
    except InstaPayPayment.DoesNotExist:
        payment = None
    
    return render(request, 'venues/booking_details.html', {
        'booking': booking,
        'payment': payment,
    })


# ========== BOOKING REQUESTS (للتوافق مع الكود القديم) ==========

@venue_owner_required
def booking_requests(request):
    """عرض طلبات الحجز (قديم - يُفضل استخدام owner_dashboard)"""
    venues = Venue.objects.filter(owner=request.user)
    bookings = Booking.objects.filter(
        field__venue__in=venues,
        status='PENDING'
    ).order_by('-created_at')
    return render(request, 'venues/booking_requests.html', {'bookings': bookings})