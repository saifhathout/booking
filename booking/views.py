# booking/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.db.models import Q
from datetime import datetime, timedelta, date
from django.utils import timezone  # ✅ مهم للـ timezone.now()
from datetime import datetime, timedelta  # ✅ مهم للـ datetime.combine و timedelta


from accounts.decorators import player_required
from venues.models import Field, VenueSlot, Booking
from notifications.utils import create_notification  # ✅ فقط create_notification
from .utils import format_time, get_booked_set, normalize_hour, get_slot_range



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
    
    # Stats حقيقية
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


# booking/views.py - field_detail

@player_required
def field_detail(request, field_id):
    field = get_object_or_404(Field, id=field_id, is_active=True)
    
    today = now.date()
    now = timezone.now()
    current_hour = now.hour
    
    # ✅ جلب جميع السلوتات من قاعدة البيانات دفعة واحدة
    end_date = today + timedelta(days=6)
    all_slots = VenueSlot.objects.filter(
        field=field,
        date__range=[today, end_date]
    ).select_related('field')
    
    # ✅ إنشاء قاموس للسلوتات للوصول السريع
    slots_dict = {}
    for slot in all_slots:
        key = f"{slot.date}_{slot.start_time.hour}"
        slots_dict[key] = slot
    
    all_slots_list = []
    available_today = 0
    
    for i in range(7):
        day = today + timedelta(days=i)
        day_slots = []
        available_count = 0
        
        for hour in range(1, 25):  # 1-24
            # ✅ حساب التاريخ الفعلي للسلوت
            if hour == 24:
                slot_date = day + timedelta(days=1)
                slot_hour = 0
            else:
                slot_date = day
                slot_hour = hour
            
            # ✅ البحث عن السلوت في القاموس
            key = f"{slot_date}_{slot_hour}"
            slot_obj = slots_dict.get(key)
            
            # ✅ تحديد حالة السلوت
            is_booked = False
            is_locked = False
            is_available = False
            
            if slot_obj:
                if slot_obj.slot_type == 'BOOKED':
                    is_booked = True
                elif slot_obj.slot_type == 'LOCKED':
                    is_locked = True
                elif slot_obj.is_available and slot_obj.slot_type == 'AVAILABLE':
                    is_available = True
            else:
                # ✅ السلوت غير موجود => متاح
                is_available = True
            
            # ✅ حساب السلوتات المتاحة اليوم
            if is_available and day == today and hour > current_hour:
                available_count += 1
                if day == today:
                    available_today += 1
            
            # ✅ تنسيق الوقت للعرض
            end_hour = hour + 1
            if end_hour == 25:
                end_hour = 1
            
            start_display = format_time(hour)
            end_display = format_time(end_hour)
            
            # ✅ إنشاء slot_id فقط إذا كان السلوت متاحاً
            if is_available:
                slot_id = f"{field_id}_{slot_date}_{slot_hour}"
            else:
                slot_id = None
            
            day_slots.append({
                'hour': hour,
                'start_time': start_display,
                'end_time': end_display,
                'time': f"{start_display} - {end_display}",
                'is_booked': is_booked,
                'is_locked': is_locked,
                'is_available': is_available,
                'slot_id': slot_id,
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
@player_required
def book_slot(request, slot_id):
    parts = slot_id.split('_')
    field_id = parts[0]
    date_str = parts[1]  # ✅ التاريخ الفعلي
    slot_hour = int(parts[2])  # ✅ 0-23
    
    field = get_object_or_404(Field, id=field_id, is_active=True)
    
    # ✅ الساعة الفعلية (0-23)
    store_hour = slot_hour
    
    if request.method == 'POST':
        duration = int(request.POST.get('duration', 1))
        
        if duration <= 0:
            messages.error(request, '❌ المدة يجب أن تكون أكبر من صفر!')
            return redirect('booking:field_detail', field_id=field.id)
        
        slot_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
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
                        # ❌ تحرير السلوتات المقفلة
                        for s in slots_to_lock:
                            s.is_available = True
                            s.slot_type = 'AVAILABLE'
                            s.save()
                        
                        messages.error(request, f'❌ الساعة {current.hour}:00 غير متاحة!')
                        return redirect('booking:field_detail', field_id=field.id)
                    
                    # ✅ قفل السلوت
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
                    player=request.user,
                    booking_date=slot_date,
                    start_time=f"{store_hour:02d}:00:00",
                    end_time=f"{end_hour:02d}:00:00",
                    status='LOCKED',
                    payment_status='PENDING',
                    total_price=field.price_per_hour * duration,
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
    
    return render(request, 'booking/book_slot.html', {
        'field': field,
        'date': date_str,
        'hour': slot_hour,
        'price': field.price_per_hour,
    })
@player_required
def booking_history(request):
    """عرض تاريخ الحجوزات للمستخدم"""
    today = date.today()
    now = datetime.now().time()
    
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


# booking/views.py

@player_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, player=request.user)
    
    # ✅ التحقق من الحالة
    if booking.status == 'CANCELLED':
        messages.warning(request, '⚠️ هذا الحجز ملغى بالفعل.')
        return redirect('booking:history')
    
    if booking.status == 'EXPIRED':
        messages.warning(request, '⚠️ هذا الحجز منتهي الصلاحية.')
        return redirect('booking:history')
    
    if booking.status == 'CONFIRMED':
        if booking.booking_date < date.today():
            messages.error(request, '❌ لا يمكن إلغاء حجز مضى عليه!')
            return redirect('booking:history')
        elif booking.booking_date == date.today():
            now = datetime.now().time()
            if booking.start_time < now:
                messages.error(request, '❌ لا يمكن إلغاء حجز بدأ بالفعل!')
                return redirect('booking:history')
    
    with transaction.atomic():
        # ✅ تحرير السلوتات - بدون حسابات!
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
    
    # تنسيق الوقت مع AM/PM
    start_time_display = format_time(booking.start_time.hour)
    end_time_display = format_time(booking.end_time.hour)
    
    return render(request, 'booking/booking_detail.html', {
        'booking': booking,
        'start_time_display': start_time_display,
        'end_time_display': end_time_display,
    })