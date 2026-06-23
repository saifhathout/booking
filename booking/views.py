# booking/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.db.models import Q
from datetime import datetime, timedelta, date

from accounts.decorators import player_required
from venues.models import Field, VenueSlot, Booking
from notifications.utils import create_notification, send_push
from .utils import format_time, get_booked_set, normalize_hour, get_slot_range


@player_required
def browse_fields(request):
    """عرض جميع الملاعب مع فلترة"""
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
    """عرض تفاصيل الملعب مع جميع السلوتات"""
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
            
            # حساب end_time (إضافة ساعة واحدة)
            end_hour = (hour % 24) + 1
            if end_hour == 24:
                end_hour = 0
            
            # تنسيق الوقت مع AM/PM
            start_time_str = format_time(hour % 24)
            end_time_str = format_time(end_hour)
            
            day_slots.append({
                'hour': hour,
                'time': start_time_str,
                'end_time': end_time_str,
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


@player_required
def book_slot(request, slot_id):
    """حجز سلوت معين"""
    parts = slot_id.split('_')
    field_id = parts[0]
    date_str = parts[1]
    display_hour = int(parts[2])  # 1-24
    
    field = get_object_or_404(Field, id=field_id, is_active=True)
    store_hour = display_hour % 24
    
    if store_hour < 0 or store_hour > 23:
        messages.error(request, 'Invalid time.')
        return redirect('booking:field_detail', field_id=field.id)
    
    # تحويل الوقت إلى AM/PM للعرض
    start_time_display = format_time(store_hour)
    end_hour = (store_hour + 1) % 24
    end_time_display = format_time(end_hour)
    
    if request.method == 'POST':
        duration = int(request.POST.get('duration', 1))
        slots_to_book = []
        
        try:
            with transaction.atomic():
                for i in range(duration):
                    h = (store_hour + i) % 24
                    next_h = (h + 1) % 24
                    
                    st = f"{h}:00:00"
                    et = f"{next_h}:00:00"
                    
                    slot, created = VenueSlot.objects.get_or_create(
                        field=field,
                        date=date_str,
                        start_time=st,
                        defaults={
                            'end_time': et,
                            'is_available': True,
                            'slot_type': 'BOOKED'
                        }
                    )
                    
                    if not created:
                        if not slot.is_available:
                            messages.error(request, f'❌ {h}:00 was just taken!')
                            return redirect('booking:field_detail', field_id=field.id)
                        slot.is_available = False
                        slot.slot_type = 'BOOKED'
                        slot.save()
                    
                    slots_to_book.append(slot)
                
                total = field.price_per_hour * duration
                
                # إنشاء الحجز بحالة PENDING
                booking = Booking.objects.create(
                    field=field,
                    player=request.user,
                    slot=slots_to_book[0],
                    booking_date=date_str,
                    start_time=f"{store_hour}:00",
                    end_time=f"{(store_hour + duration) % 24}:00",
                    status='PENDING'
                )
                
                messages.info(request, '✅ تم حجز الملعب، الآن قم بالدفع للتأكيد')
                
                # التوجيه إلى صفحة الدفع
                return redirect('payment:initiate_instapay', booking_id=booking.id)
                
        except IntegrityError:
            messages.error(request, '❌ Booking failed! Slot already taken.')
            return redirect('booking:field_detail', field_id=field.id)
    
    # GET request
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


@player_required
def cancel_booking(request, booking_id):
    """إلغاء حجز معين"""
    booking = get_object_or_404(Booking, id=booking_id, player=request.user)
    
    if booking.status == 'CANCELLED':
        messages.warning(request, 'Already cancelled.')
        return redirect('booking:history')
    
    start_h = booking.start_time.hour
    end_h = booking.end_time.hour
    
    if end_h == 0:
        end_h = 24
    
    duration = end_h - start_h if end_h > start_h else 1
    
    # إلغاء الحجز
    booking.status = 'CANCELLED'
    booking.save()
    
    # حذف السلوتات
    date_str = booking.booking_date.strftime('%Y-%m-%d')
    store_hour = start_h
    
    for i in range(duration):
        h = (store_hour + i) % 24
        VenueSlot.objects.filter(
            field=booking.field,
            date=date_str,
            start_time=f"{h}:00:00"
        ).delete()
    
    messages.success(request, '✅ Booking cancelled successfully!')
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