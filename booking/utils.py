# booking/utils.py

def format_time(hour):
    """تحويل الساعة من 24 إلى 12 مع AM/PM"""
    if hour == 0 or hour == 24:
        return "12:00 AM"
    elif hour < 12:
        return f"{hour}:00 AM"
    elif hour == 12:
        return "12:00 PM"
    else:
        return f"{hour - 12}:00 PM"

def format_time_range(start_hour, duration=1):
    """تنسيق نطاق زمني مع AM/PM"""
    start = format_time(start_hour % 24)
    end_hour = (start_hour + duration) % 24
    end = format_time(end_hour)
    return f"{start} - {end}"

def normalize_hour(hour):
    """تطبيع الساعة لتكون بين 0 و 23"""
    return hour % 24

def get_slot_range(start_hour, duration):
    """الحصول على نطاق الساعات للحجز"""
    slots = []
    for i in range(duration):
        h = (start_hour + i) % 24
        slots.append(h)
    return slots

# booking/utils.py

# booking/utils.py

# booking/utils.py

# booking/utils.py

from datetime import timedelta


def get_booked_set(field, start_date, end_date):
    """الحصول على مجموعة الحجوزات المحجوزة"""
    from venues.models import VenueSlot
    
    booked_slots = VenueSlot.objects.filter(
        field=field,
        date__range=[start_date, end_date],
        is_available=False
    )
    
    booked_set = set()
    for slot in booked_slots:
        hour = slot.start_time.hour
        if hour == 0:
            # ✅ 12 AM → 24، وترجعه لليوم السابق
            prev_date = slot.date - timedelta(days=1)
            booked_set.add(f"{prev_date}_24")
        else:
            booked_set.add(f"{slot.date}_{hour}")
    
    return booked_set
def display_hour(hour):
    """عرض الساعة بتنسيق 12 ساعة مع AM/PM"""
    return format_time(hour)