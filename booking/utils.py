from datetime import datetime, timedelta


def normalize_hour(hour):
    """Convert display hour (1-24) to storage hour (0-23)"""
    return hour % 24


def display_hour(hour):
    """Convert storage hour (0-23) to display hour (1-24)"""
    return hour if hour > 0 else 24


def get_slot_range(date_str, start_hour, duration):
    store_hour = normalize_hour(start_hour)
    base_date = datetime.strptime(date_str, '%Y-%m-%d')
    
    # 12 AM (hour 0/24) starts a new day
    if start_hour == 24 or store_hour == 0:
        base_date += timedelta(days=1)
        store_hour = 0
    
    slots = []
    
    for i in range(duration):
        h = (store_hour + i) % 24
        next_h = (h + 1) % 24
        days_ahead = (store_hour + i) // 24
        slot_date = (base_date + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
        
        slots.append({
            'date': slot_date,
            'hour': h,
            'next_hour': next_h,
            'start_time': f"{h}:00:00",
            'end_time': f"{next_h}:00:00",
        })
    
    return slots


def format_time(hour):
    """Format hour for display"""
    if hour == 0 or hour == 24:
        return "12:00 AM"
    elif hour < 12:
        return f"{hour}:00 AM"
    elif hour == 12:
        return "12:00 PM"
    else:
        return f"{hour-12}:00 PM"


def get_booked_set(field, date_from, date_to):
    from venues.models import VenueSlot
    
    all_slots = VenueSlot.objects.filter(
        field=field,
        date__gte=date_from,
        date__lte=date_to,
        is_available=False
    )
    
    booked_set = set()
    for slot in all_slots:
        h = slot.start_time.hour
        booked_set.add(f"{slot.date}_{h}")
        
        # hour 0 on DATE = display hour 24 on PREVIOUS day
        if h == 0:
            from datetime import timedelta
            prev_date = (slot.date - timedelta(days=1)).strftime('%Y-%m-%d')
            booked_set.add(f"{prev_date}_24")
    
    return booked_set