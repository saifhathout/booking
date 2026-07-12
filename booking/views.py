# booking/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta, date

from accounts.decorators import player_required
from venues.models import Field, VenueSlot, Booking
from notifications.utils import create_notification
from .utils import format_time, get_booked_set, normalize_hour, get_slot_range


# @player_required
def browse_fields(request):
    """عرض جميع الملاعب - الصفحة الرئيسية"""
    sport_type = request.GET.get('sport_type', '')
    city = request.GET.get('city', '')
    date_val = request.GET.get('date', '')
    
    fields = Field.objects.filter(is_active=True)
    
    if sport_type:
        fields = fields.filter(sport_type=sport_type)
    if city:
        fields = fields.filter(venue__city__icontains=city)
    
    total_fields = fields.count()
    total_bookings = Booking.objects.filter(field__in=fields, status='CONFIRMED').count()
    total_players = Booking.objects.filter(field__in=fields, status='CONFIRMED').values('player').distinct().count()
    
    return render(request, 'booking/field_browse.html', {
        'fields': fields,
        'sport_type': sport_type,
        'city': city,
        'date': date_val,
        'total_fields': total_fields,
        'total_bookings': total_bookings,
        'total_players': total_players,
    })


# @player_required
def field_detail(request, field_id):
    """تفاصيل الملعب مع السلوتات"""
    field = get_object_or_404(Field, id=field_id, is_active=True)
    
    now = timezone.now()
    today = now.date()
    current_hour = now.hour
    
    booked_set = get_booked_set(field, today, today + timedelta(days=6))
    
    all_slots_list = []
    available_today = 0
    
    for i in range(7):
        day = today + timedelta(days=i)
        day_slots = []
        available_count = 0
        
        for hour in range(1, 25):
            is_booked = f"{day}_{hour}" in booked_set
            
            if not is_booked and day == today and hour > current_hour:
                available_count += 1
                if day == today:
                    available_today += 1
            
            end_hour = hour + 1
            if end_hour == 25:
                end_hour = 1
            
            start_display = format_time(hour)
            end_display = format_time(end_hour)
            
            if hour == 24:
                slot_date = day
                slot_hour = 0
            else:
                slot_date = day
                slot_hour = hour
            
            is_past = False
            if day == today and hour <= current_hour:
                is_past = True
            
            day_slots.append({
                'hour': hour,
                'start_time': start_display,
                'end_time': end_display,
                'time': f"{start_display} - {end_display}",
                'is_booked': is_booked,
                'is_locked': False,
                'is_past': is_past,
                'slot_id': f"{field_id}_{slot_date}_{slot_hour}" if not is_booked and not is_past else None,
                'slot_date': slot_date,
                'slot_hour': slot_hour,
            })
        
        if day_slots:
            all_slots_list.append({
                'date': day,
                'slots': day_slots,
                'available_count': available_count,
            })
    
    return render(request, 'booking/field_detail.html', {
        'field': field,
        'all_slots_list': all_slots_list,
        'today': today,
        'current_hour': current_hour,
        'available_today': available_today,
    })


def book_slot(request, slot_id):
    """صفحة الحجز - يدعم المسجلين والضيوف"""
    parts = slot_id.split('_')
    field_id = parts[0]
    date_str = parts[1]
    slot_hour = int(parts[2])
    
    field = get_object_or_404(Field, id=field_id, is_active=True)
    store_hour = slot_hour
    
    # ✅ التحقق من الوقت
    now = timezone.now()
    slot_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    
    if slot_date == now.date():
        if store_hour < now.hour:
            messages.error(request, '❌ هذا الوقت قد مضى!')
            return redirect('booking:field_detail', field_id=field.id)
        elif store_hour == now.hour:
            messages.error(request, '❌ هذا الوقت قد بدأ بالفعل!')
            return redirect('booking:field_detail', field_id=field.id)
    
    if request.method == 'POST':
        duration = int(request.POST.get('duration', 1))
        
        if duration <= 0:
            messages.error(request, '❌ المدة يجب أن تكون أكبر من صفر!')
            return redirect('booking:field_detail', field_id=field.id)
        
        # ✅ جلب بيانات المستخدم
        if request.user.is_authenticated:
            # ✅ مسجل → استخدم بياناته
            name = request.user.get_full_name() or request.user.username
            email = request.user.email
            phone = getattr(request.user, 'phone', '') or ''
            is_guest = False
        else:
            # ✅ ضيف → يطلب بياناته
            name = request.POST.get('name')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            is_guest = True
            
            if not name or not email or not phone:
                messages.error(request, '❌ Please fill all your details')
                return render(request, 'booking/book_slot.html', {
                    'field': field,
                    'date': date_str,
                    'hour': slot_hour,
                    'price': field.price_per_hour,
                    'show_guest_form': True,
                    'start_time_display': format_time(store_hour),
                    'end_time_display': format_time(store_hour + 1),
                    'guest_name': request.session.get('guest_name', ''),
                    'guest_email': request.session.get('guest_email', ''),
                    'guest_phone': request.session.get('guest_phone', ''),
                })
            
            # ✅ حفظ بيانات الضيف في الـ session
            request.session['guest_name'] = name
            request.session['guest_email'] = email
            request.session['guest_phone'] = phone
        
        try:
            with transaction.atomic():
                start_datetime = datetime.combine(slot_date, datetime.min.time().replace(hour=store_hour))
                
                slots_to_lock = []
                
                for i in range(duration):
                    current = start_datetime + timedelta(hours=i)
                    
                    slot_date_current = current.date()
                    slot_time = current.time().replace(minute=0, second=0, microsecond=0)
                    
                    end_slot_datetime = current + timedelta(hours=1)
                    end_slot_time = end_slot_datetime.time().replace(
                        minute=0, second=0, microsecond=0
                    )
                    
                    # ✅ قفل السلوت
                    slot, created = VenueSlot.objects.select_for_update().get_or_create(
                        field=field,
                        date=slot_date_current,
                        start_time=slot_time,
                        defaults={
                            "end_time": end_slot_time,
                            "is_available": True,
                            "slot_type": "AVAILABLE",
                        }
                    )
                    
                    if not slot.is_available:
                        for s in slots_to_lock:
                            s.is_available = True
                            s.slot_type = 'AVAILABLE'
                            s.save()
                        
                        messages.error(request, f'❌ الساعة {current.hour}:00 غير متاحة!')
                        return redirect('booking:field_detail', field_id=field.id)
                    
                    # ✅ قفل السلوت مؤقتاً
                    slot.is_available = False
                    slot.slot_type = 'LOCKED'
                    slot.save()
                    
                    slots_to_lock.append(slot)
                
                # ✅ حساب end_time و end_date
                end_datetime = start_datetime + timedelta(hours=duration)
                end_hour = end_datetime.hour
                if end_hour == 0:
                    end_hour = 24
                
                # ✅ إنشاء الحجز
                booking = Booking.objects.create(
                    field=field,
                    player=request.user if request.user.is_authenticated else None,
                    booking_date=slot_date,
                    start_time=f"{store_hour:02d}:00:00",
                    end_time=f"{end_hour:02d}:00:00",
                    status='LOCKED',
                    payment_status='PENDING',
                    total_price=field.price_per_hour * duration,
                    guest_name=name if is_guest else '',
                    guest_email=email if is_guest else '',
                    guest_phone=phone if is_guest else '',
                )
                
                # ✅ ربط السلوتات
                booking.slots.set(slots_to_lock)
                
                # ✅ تحديث end_date
                last_slot = booking.get_last_slot()
                if last_slot:
                    booking.end_date = last_slot.date
                    booking.save()
                
                # ✅ تحديث حقول العرض
                booking.update_display_fields()
                
                # ✅ تحديد وقت انتهاء القفل
                booking.locked_until = timezone.now() + timedelta(minutes=15)
                booking.save()
                
                messages.info(request, '✅ تم قفل الحجز مؤقتاً لمدة 15 دقيقة، قم بالدفع للتأكيد')
                return redirect('payment:initiate_instapay', booking_id=booking.id)
                
        except Exception as e:
            messages.error(request, f'❌ حدث خطأ: {str(e)}')
            return redirect('booking:field_detail', field_id=field.id)
    
    # ✅ GET - عرض الصفحة
    start_time_display = format_time(store_hour)
    end_time_display = format_time(store_hour + 1)
    
    # ✅ لو مسجل، جيب بياناته
    if request.user.is_authenticated:
        guest_name = request.user.get_full_name() or request.user.username
        guest_email = request.user.email
        guest_phone = getattr(request.user, 'phone', '') or ''
    else:
        guest_name = request.session.get('guest_name', '')
        guest_email = request.session.get('guest_email', '')
        guest_phone = request.session.get('guest_phone', '')
    
    return render(request, 'booking/book_slot.html', {
        'field': field,
        'date': date_str,
        'hour': slot_hour,
        'price': field.price_per_hour,
        'start_time_display': start_time_display,
        'end_time_display': end_time_display,
        'show_guest_form': not request.user.is_authenticated,
        'guest_name': guest_name,
        'guest_email': guest_email,
        'guest_phone': guest_phone,
    })


@player_required
def booking_history(request):
    """عرض تاريخ الحجوزات للمستخدم"""
    now = timezone.now()
    today = now.date()
    
    all_bookings = Booking.objects.select_related(
        'field', 'field__venue', 'player'
    ).filter(
        player=request.user
    ).exclude(
        status='CANCELLED'
    ).order_by('booking_date', 'start_time')
    
    upcoming_bookings = []
    past_bookings = []
    
    for booking in all_bookings:
        if booking.booking_date > today:
            upcoming_bookings.append(booking)
        elif booking.booking_date == today:
            booking_time = datetime.strptime(str(booking.start_time), '%H:%M:%S').time()
            if booking_time >= now.time():
                upcoming_bookings.append(booking)
            else:
                past_bookings.append(booking)
        else:
            past_bookings.append(booking)
    
    return render(request, 'booking/booking_history.html', {
        'upcoming_bookings': upcoming_bookings,
        'past_bookings': past_bookings,
    })


@player_required
def cancel_booking(request, booking_id):
    """إلغاء الحجز"""
    booking = get_object_or_404(Booking, id=booking_id, player=request.user)
    
    if booking.status == 'CANCELLED':
        messages.warning(request, '⚠️ هذا الحجز ملغى بالفعل.')
        return redirect('booking:history')
    
    now = timezone.now()
    if booking.booking_date < now.date():
        messages.error(request, '❌ لا يمكن إلغاء حجز مضى عليه!')
        return redirect('booking:history')
    elif booking.booking_date == now.date():
        booking_start = datetime.strptime(str(booking.start_time), '%H:%M:%S').time()
        if booking_start < now.time():
            messages.error(request, '❌ لا يمكن إلغاء حجز بدأ بالفعل!')
            return redirect('booking:history')
    
    with transaction.atomic():
        booking.release_slots()
    
    create_notification(
        user=booking.field.venue.owner,
        title="❌ تم إلغاء حجز",
        message=f"قام {request.user.username} بإلغاء حجز ملعب {booking.field.name}.",
        url=f"/venues/booking/{booking.id}/details/"
    )
    
    messages.success(request, '✅ تم إلغاء الحجز وفتح السلوتات مرة أخرى!')
    return redirect('booking:history')


@player_required
def booking_detail(request, booking_id):
    """عرض تفاصيل حجز معين"""
    booking = get_object_or_404(
        Booking, 
        id=booking_id, 
        player=request.user
    )
    
    start_time_display = format_time(booking.start_time.hour)
    end_time_display = format_time(booking.end_time.hour)
    
    return render(request, 'booking/booking_detail.html', {
        'booking': booking,
        'start_time_display': start_time_display,
        'end_time_display': end_time_display,
    })