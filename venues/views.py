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

# venues/views.py

@venue_owner_required
def field_schedule_view(request, field_id):
    field = get_object_or_404(Field, id=field_id, venue__owner=request.user)
    
    today = date.today()
    now = datetime.now()
    current_hour = now.hour
    
    # ✅ جلب جميع السلوتات من قاعدة البيانات
    all_slots = VenueSlot.objects.filter(
        field=field, 
        date__gte=today, 
        date__lte=today + timedelta(days=6)
    ).order_by('date', 'start_time')
    
    # ✅ جلب الحجوزات المؤكدة
    bookings = Booking.objects.filter(
        field=field, 
        status='CONFIRMED'
    ).select_related('player')
    
    # ✅ إنشاء قاموس للحجوزات
    booking_map = {}
    for b in bookings:
        for slot in b.slots.all():
            key = f"{slot.date}_{slot.start_time.hour}"
            booking_map[key] = {
                'player_name': b.player.username,
                'booking_id': b.id,
            }
    
    # ✅ إنشاء قاموس للسلوتات
    slot_map = {}
    for slot in all_slots:
        key = f"{slot.date}_{slot.start_time.hour}"
        slot_map[key] = {
            'type': slot.slot_type,
            'is_available': slot.is_available,
        }
    
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
        available_count = 0
        booked_count = 0
        blocked_count = 0
        
        for hour in range(1, 25):  # 1-24
            # ✅ حساب التاريخ الفعلي للسلوت
            # 12:00 AM (hour=24) تنتمي إلى اليوم التالي
            if hour == 24:
                slot_date = day + timedelta(days=1)
                slot_hour = 0
            else:
                slot_date = day
                slot_hour = hour
            
            # ✅ البحث في القواميس
            key = f"{slot_date}_{slot_hour}"
            slot_data = slot_map.get(key)
            booking_data = booking_map.get(key)
            
            # ✅ تحديد حالة السلوت
            is_booked = booking_data is not None
            is_blocked = slot_data and slot_data.get('type') == 'BLOCKED'
            is_locked = slot_data and slot_data.get('type') == 'LOCKED'
            is_available = slot_data and slot_data.get('is_available', True) and not is_booked and not is_blocked and not is_locked
            
            # ✅ إذا كان السلوت غير موجود في قاعدة البيانات، اعتبره متاح
            if not slot_data and not is_booked:
                is_available = True
            
            # ✅ تحديد إذا كان السلوت في الماضي
            is_past = False
            if day == today and hour <= current_hour:
                is_past = True
            
            # ✅ إحصائيات
            if is_booked:
                booked_count += 1
            elif is_blocked:
                blocked_count += 1
            elif is_available and not is_past:
                available_count += 1
            
            # ✅ تحديد slot_type للعرض
            slot_type = None
            if is_booked:
                slot_type = 'BOOKED'
            elif is_locked:
                slot_type = 'LOCKED'
            elif is_blocked:
                slot_type = 'BLOCKED'
            elif is_available and not is_past:
                slot_type = 'AVAILABLE'
            
            day_slots.append({
                'hour': hour,
                'time': format_time(hour),
                'slot_date': slot_date,
                'slot_hour': slot_hour,
                'slot_type': slot_type,
                'is_booked': is_booked,
                'is_locked': is_locked,
                'is_blocked': is_blocked,
                'is_available': is_available,
                'is_past': is_past,
                'booking': booking_data,
            })
        
        all_slots_list.append({
            'date': day,
            'slots': day_slots,
            'available_count': available_count,
            'booked_count': booked_count,
            'blocked_count': blocked_count,
        })
    
    return render(request, 'venues/field_schedule.html', {
        'field': field,
        'all_slots_list': all_slots_list,
        'today': today,
        'current_hour': current_hour,
    })

# ========== BLOCK / UNBLOCK ==========

# venues/views.py

@venue_owner_required
def block_slot(request, field_id, date, hour):
    field = get_object_or_404(Field, id=field_id, venue__owner=request.user)
    
    # ✅ تحويل الساعة من 1-24 إلى 0-23
    if hour == 24:
        store_hour = 0
        slot_date = datetime.strptime(date, '%Y-%m-%d').date() + timedelta(days=1)
    else:
        store_hour = hour
        slot_date = datetime.strptime(date, '%Y-%m-%d').date()
    
    # ✅ حساب end_time
    if store_hour == 23:
        end_time = "00:00:00"
    else:
        end_time = f"{store_hour+1}:00:00"
    
    try:
        with transaction.atomic():
            slot, created = VenueSlot.objects.get_or_create(
                field=field,
                date=slot_date,
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
    
    # ✅ تحويل الساعة من 1-24 إلى 0-23
    if hour == 24:
        store_hour = 0
        slot_date = datetime.strptime(date, '%Y-%m-%d').date() + timedelta(days=1)
    else:
        store_hour = hour
        slot_date = datetime.strptime(date, '%Y-%m-%d').date()
    
    deleted = VenueSlot.objects.filter(
        field=field,
        date=slot_date,
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
    
    # ✅ 2. طلبات الدفع في انتظار المراجعة (الأهم!)
    pending_reviews = InstaPayPayment.objects.filter(
        status__in=['pending', 'manual_review'],
        booking__field__venue__in=venues
    ).select_related(
        'booking', 
        'booking__field', 
        'booking__player'
    ).order_by('-created_at')
    
    # ✅ 3. الإشعارات غير المقروءة
    notifications = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).order_by('-created_at')[:20]
    
    # ✅ 4. الملاعب
    all_fields = Field.objects.filter(venue__in=venues, is_active=True)[:4]
    
    # ✅ للتصحيح - طباعة عدد الطلبات
    print(f"📊 Pending reviews: {pending_reviews.count()}")
    print(f"🔔 Notifications: {notifications.count()}")
    
    context = {
        'total_fields': total_fields,
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'pending_reviews': pending_reviews,
        'notifications': notifications,
        'all_fields': all_fields,
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