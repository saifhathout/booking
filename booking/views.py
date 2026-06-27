# booking/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.db.models import Q
from datetime import datetime, timedelta, date
from notifications.utils import create_notification  # ✅ لازم تكون موجودة


from accounts.decorators import player_required
from venues.models import Field, VenueSlot, Booking
from notifications.utils import create_notification, send_push
from .utils import format_time, get_booked_set, normalize_hour, get_slot_range


# booking/views.py

# booking/views.py

def format_time_display(hour):
    """تحويل الساعة (1-24) إلى نص عرض (12:00 AM/PM)"""
    if hour == 24 or hour == 0:
        return "12:00 AM"
    elif hour == 12:
        return "12:00 PM"
    elif hour < 12:
        return f"{hour}:00 AM"
    else:
        return f"{hour-12}:00 PM"
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
    
    # ✅ Stats حقيقية
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


# booking/views.py

# booking/views.py

# booking/views.py

# booking/views.py

# booking/views.py

# booking/views.py

@player_required
def field_detail(request, field_id):
    field = get_object_or_404(Field, id=field_id, is_active=True)
    
    today = date.today()
    now = datetime.now()
    current_hour = now.hour
    
    booked_set = get_booked_set(field, today, today + timedelta(days=6))
    
    all_slots_list = []
    available_today = 0
    
    for i in range(7):
        day = today + timedelta(days=i)
        day_slots = []
        available_count = 0
        
        for hour in range(1, 25):  # 1-24
            is_booked = f"{day}_{hour}" in booked_set
            
            if not is_booked and day == today and hour > current_hour:
                available_count += 1
                if day == today:
                    available_today += 1
            
            end_hour = hour + 1
            if end_hour == 25:
                end_hour = 1
            
            start_display = format_time_display(hour)
            end_display = format_time_display(end_hour)
            
            day_slots.append({
                'hour': hour,
                'start_time': start_display,
                'end_time': end_display,
                'time': f"{start_display} - {end_display}",
                'is_booked': is_booked,
                'slot_id': f"{field_id}_{day}_{hour}" if not is_booked else None,
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

# booking/views.py
# booking/views.py

# booking/views.py

# booking/views.py

# booking/views.py

# booking/views.py

# booking/views.py

# booking/views.py

# booking/views.py

from datetime import datetime, timedelta

@player_required
def book_slot(request, slot_id):
    parts = slot_id.split('_')
    field_id = parts[0]
    date_str = parts[1]
    display_hour = int(parts[2])  # 1-24
    
    field = get_object_or_404(Field, id=field_id, is_active=True)
    
    if display_hour == 24:
        store_hour = 0
    else:
        store_hour = display_hour % 24
    
    if store_hour < 0 or store_hour > 23:
        messages.error(request, 'Invalid time.')
        return redirect('booking:field_detail', field_id=field.id)
    
    start_time_display = format_time_display(display_hour)
    end_hour = display_hour + 1
    if end_hour == 25:
        end_hour = 1
    end_time_display = format_time_display(end_hour)
    
    if request.method == 'POST':
        duration = int(request.POST.get('duration', 1))
        
        try:
            with transaction.atomic():
                # ✅ تحويل string إلى date
                booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                
                slots_to_book = []
                for i in range(duration):
                    h = (store_hour + i) % 24
                    st = f"{h:02d}:00:00"
                    
                    # ✅ لو عدينا منتص الليل، نغير التاريخ
                    if (store_hour + i) >= 24:
                        slot_date = booking_date + timedelta(days=1)
                    else:
                        slot_date = booking_date
                    
                    slot = VenueSlot.objects.filter(
                        field=field,
                        date=slot_date,  # ✅ التاريخ الصح
                        start_time=st,
                        is_available=True
                    ).first()
                    
                    if not slot:
                        messages.error(request, f'❌ {h}:00 is not available!')
                        return redirect('booking:field_detail', field_id=field.id)
                    
                    slots_to_book.append(slot)
                
                # ✅ قفل السلوتات
                for slot in slots_to_book:
                    slot.is_available = False
                    slot.save()
                
                # ✅ حساب end_time الصحيح
                end_hour = (store_hour + duration) % 24
                if end_hour == 0:
                    end_hour = 24
                
                # ✅ التاريخ الصحيح لـ end_time
                end_date = booking_date + timedelta(days=1) if (store_hour + duration) >= 24 else booking_date
                
                # ✅ إنشاء الحجز
                total = field.price_per_hour * duration
                booking = Booking.objects.create(
                    field=field,
                    player=request.user,
                    slot=slots_to_book[0],
                    booking_date=date_str,  # ✅ التاريخ الأصلي
                    start_time=f"{store_hour:02d}:00:00",
                    end_time=f"{end_hour:02d}:00:00",
                    status='PENDING',
                    payment_status='PENDING'
                )
                
                messages.info(request, '✅ تم إنشاء طلب الحجز، الآن قم بالدفع للتأكيد')
                return redirect('payment:initiate_instapay', booking_id=booking.id)
                
        except IntegrityError:
            messages.error(request, '❌ Booking failed!')
            return redirect('booking:field_detail', field_id=field.id)
    
    return render(request, 'booking/book_slot.html', {
        'field': field,
        'date': date_str,
        'hour': display_hour,
        'start_time_display': start_time_display,
        'end_time_display': end_time_display,
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

# booking/views.py

@player_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, player=request.user)
    
    if booking.status == 'CANCELLED':
        messages.warning(request, 'Already cancelled.')
        return redirect('booking:history')
    
    field_name = booking.field.name
    booking_date = booking.booking_date
    start_time = booking.start_time
    owner = booking.field.venue.owner
    
    start_h = booking.start_time.hour
    end_h = booking.end_time.hour
    
    # ✅ حساب المدة صح
    if end_h == 0:
        end_h = 24
    
    # ✅ لو end_h <= start_h يبقى الحجز تعدى منتصف الليل
    if end_h <= start_h:
        duration = 24 - start_h + end_h
    else:
        duration = end_h - start_h
    
    # ✅ إلغاء الحجز
    booking.status = 'CANCELLED'
    booking.save()
    
    # ✅ فتح السلوتات (مش حذفها)
    date_str = booking.booking_date.strftime('%Y-%m-%d')
    store_hour = start_h
    
    for i in range(duration):
        h = (store_hour + i) % 24
        st = f"{h:02d}:00:00"
        
        # ✅ update is_available = True
        VenueSlot.objects.filter(
            field=booking.field,
            date=date_str,
            start_time=st
        ).update(
            is_available=True,
            slot_type='BOOKED'
        )
    
    # ✅ إشعار للمالك
    create_notification(
        user=owner,
        title="❌ تم إلغاء حجز",
        message=f"قام {request.user.username} بإلغاء حجز ملعب {field_name} بتاريخ {booking_date} الساعة {start_time}.",
        url=f"/venues/booking/{booking.id}/details/"
    )
    
    messages.success(request, '✅ Booking cancelled and slots reopened!')
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