# booking/utils.py

from datetime import datetime, timedelta
from venues.models import VenueSlot


def format_time(hour):
    """تنسيق الوقت بصيغة 12-hour مع AM/PM"""
    if hour == 0 or hour == 24:
        return '12:00 AM'
    elif hour < 12:
        return f'{hour}:00 AM'
    elif hour == 12:
        return '12:00 PM'
    else:
        return f'{hour - 12}:00 PM'


def get_booked_set(field, start_date, end_date):
    """
    إرجاع مجموعة من السلوتات غير المتاحة (محجوزة أو مقفلة)
    """
    unavailable_slots = VenueSlot.objects.filter(
        field=field,
        date__range=[start_date, end_date],
        is_available=False
    ).values_list('date', 'start_time')
    
    booked_set = set()
    for date, time in unavailable_slots:
        hour = time.hour
        if hour == 0:
            hour = 24
        booked_set.add(f"{date}_{hour}")
    
    return booked_set


def get_slot_status(field, date, hour):
    """
    التحقق من حالة سلوت معين
    Returns: 'available', 'booked', 'locked', 'blocked'
    """
    if hour == 24:
        store_hour = 0
    else:
        store_hour = hour
    
    try:
        slot = VenueSlot.objects.get(
            field=field,
            date=date,
            start_time=f"{store_hour:02d}:00:00"
        )
        
        if not slot.is_available:
            if slot.slot_type == 'LOCKED':
                return 'locked'
            elif slot.slot_type == 'BOOKED':
                return 'booked'
            elif slot.slot_type == 'BLOCKED':
                return 'blocked'
        return 'available'
    except VenueSlot.DoesNotExist:
        return 'available'


def normalize_hour(hour):
    """تحويل الساعة من 1-24 إلى 0-23 للتخزين"""
    if hour == 24:
        return 0
    return hour % 24


def get_slot_range(start_hour, duration):
    """إرجاع قائمة بالساعات المطلوبة للحجز"""
    slots = []
    for i in range(duration):
        h = (start_hour + i) % 24
        slots.append(h)
    return slots