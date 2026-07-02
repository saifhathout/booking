# booking/utils.py

from datetime import timedelta
from typing import List, Tuple, Set
from venues.models import VenueSlot


def format_time(hour: int) -> str:
    """
    تحويل الساعة من 24 إلى 12 مع AM/PM
    
    Args:
        hour: الساعة (0-23)
    
    Returns:
        str: الوقت بتنسيق 12 ساعة (مثلاً "2:00 PM")
    """
    hour = hour % 24
    
    if hour == 0:
        return "12:00 AM"
    elif hour < 12:
        return f"{hour}:00 AM"
    elif hour == 12:
        return "12:00 PM"
    else:
        return f"{hour - 12}:00 PM"


def format_time_display(hour: int) -> str:
    """
    تنسيق الساعة للعرض (1-24) مع AM/PM
    هذه الدالة هي نفس format_time ولكن مع دعم 24
    """
    if hour == 24 or hour == 0:
        return "12:00 AM"
    elif hour == 12:
        return "12:00 PM"
    elif hour < 12:
        return f"{hour}:00 AM"
    else:
        return f"{hour - 12}:00 PM"


def format_time_range(start_hour: int, duration: int = 1) -> str:
    """
    تنسيق نطاق زمني مع AM/PM
    
    Args:
        start_hour: ساعة البداية (0-23)
        duration: المدة بالساعات
    
    Returns:
        str: النطاق الزمني (مثلاً "2:00 PM - 4:00 PM")
    """
    if duration < 1:
        raise ValueError("Duration must be positive")
    if duration > 24:
        raise ValueError("Duration cannot exceed 24 hours")
    
    start = format_time(start_hour % 24)
    end_hour = (start_hour + duration) % 24
    end = format_time(end_hour)
    
    return f"{start} - {end}"


def normalize_hour(hour: int) -> int:
    """تطبيع الساعة لتكون بين 0 و 23"""
    return hour % 24


def get_slot_range(start_hour: int, duration: int) -> List[int]:
    """الحصول على نطاق الساعات للحجز"""
    if duration < 1:
        raise ValueError("Duration must be positive")
    if duration > 24:
        raise ValueError("Duration cannot exceed 24 hours")
    
    slots = []
    for i in range(duration):
        h = (start_hour + i) % 24
        slots.append(h)
    return slots


def get_booked_set(field, start_date, end_date) -> Set[Tuple]:
    """الحصول على مجموعة الحجوزات المحجوزة"""
    booked_slots = VenueSlot.objects.filter(
        field=field,
        date__range=[start_date, end_date],
        is_available=False
    ).only('date', 'start_time')
    
    booked_set = set()
    for slot in booked_slots:
        hour = slot.start_time.hour
        if hour == 0:
            prev_date = slot.date - timedelta(days=1)
            booked_set.add((prev_date, 24))
        else:
            booked_set.add((slot.date, hour))
    
    return booked_set


def is_slot_booked(booked_set: Set[Tuple], date, hour: int) -> bool:
    """التحقق من أن السلوت محجوز"""
    return (date, hour) in booked_set


def calculate_duration(start_time, end_time) -> int:
    """
    حساب المدة بين وقتين
    
    Args:
        start_time: وقت البداية (TimeField)
        end_time: وقت النهاية (TimeField)
    
    Returns:
        int: المدة بالساعات
    """
    start_h = start_time.hour
    end_h = end_time.hour
    
    if end_h == 0:
        end_h = 24
    
    if end_h <= start_h:
        return 24 - start_h + end_h
    return end_h - start_h


def display_hour(hour: int) -> str:
    """عرض الساعة بتنسيق 12 ساعة مع AM/PM (اختصار لـ format_time)"""
    return format_time(hour)