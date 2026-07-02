# booking/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.utils import timezone
from datetime import datetime, timedelta, date
import logging

from accounts.decorators import player_required
from venues.models import Field, VenueSlot
from .models import Booking, BookingSlot
from notifications.utils import create_notification
from .utils import format_time_display, get_booked_set, is_slot_booked

logger = logging.getLogger(__name__)

# ============================================================
# CONSTANTS
# ============================================================
MAX_BOOKING_DURATION = 4          # أقصى مدة حجز بالساعات
MAX_BOOKING_DAYS_AHEAD = 30       # أقصى عدد أيام مقدمًا
BOOKING_EXPIRY_MINUTES = 20       # مهلة إتمام الدفع بعد الحجز


# ============================================================
# HELPERS - منطق الساعات (نظام 1-24 المعروض / 0-23 المخزّن)
# ============================================================

def display_hour_to_store_hour(display_hour):
    """
    يحوّل ساعة العرض (1-24) لساعة التخزين في DB (0-23).
    الساعة 24 في العرض = الساعة 0 (منتصف الليل) في التخزين.
    """
    if display_hour == 24:
        return 0
    return display_hour % 24


def build_slot_datetime(booking_date, store_hour, hour_offset):
    """
    يحسب التاريخ الفعلي لسلوت معين لما بيكون فيه إزاحة ساعات (multi-hour booking).
    لو (store_hour + hour_offset) عدّى 24، معناه دخلنا اليوم التالي.
    يرجع: (target_date, actual_store_hour لهذا السلوت)
    """
    total_hour = store_hour + hour_offset
    actual_store_hour = total_hour % 24
    days_forward = total_hour // 24
    target_date = booking_date + timedelta(days=days_forward)
    return target_date, actual_store_hour


def get_booking_time_bounds(store_hour, duration):
    """
    يحسب start_time / end_time كـ strings، وهل الحجز بيعدي منتصف الليل ولا لأ.
    يرجع: (start_time_str, end_time_str, crosses_midnight: bool)
    """
    start_time_str = f"{store_hour:02d}:00:00"
    end_store_hour = (store_hour + duration) % 24
    end_time_str = f"{end_store_hour:02d}:00:00"
    crosses_midnight = (store_hour + duration) > 24
    return start_time_str, end_time_str, crosses_midnight


# ============================================================
# 1. BROWSE FIELDS
# ============================================================
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


# ============================================================
# 2. FIELD DETAIL
# ============================================================
@player_required
def field_detail(request, field_id):
    """عرض تفاصيل الملعب مع جميع السلوتات لآخر 7 أيام"""
    field = get_object_or_404(Field, id=field_id, is_active=True)

    today = date.today()
    now = timezone.localtime()
    current_hour = now.hour

    booked_set = get_booked_set(field, today, today + timedelta(days=6))

    all_slots_list = []
    available_today = 0

    for i in range(7):
        day = today + timedelta(days=i)
        day_slots = []
        available_count = 0

        for hour in range(1, 25):
            is_booked = is_slot_booked(booked_set, day, hour)
            is_past = (day == today and hour <= current_hour)
            is_available = not is_booked and not is_past

            if is_available:
                available_count += 1
                if day == today:
                    available_today += 1

            end_hour = hour + 1
            if end_hour == 25:
                end_hour = 1

            day_slots.append({
                'hour': hour,
                'start_time': format_time_display(hour),
                'end_time': format_time_display(end_hour),
                'time': f"{format_time_display(hour)} - {format_time_display(end_hour)}",
                'is_booked': is_booked,
                'is_past': is_past,
                'slot_id': f"{field_id}_{day}_{hour}" if is_available else None,
            })

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


# ============================================================
# 3. BOOK SLOT
# ============================================================
@player_required
def book_slot(request, slot_id):
    """
    حجز سلوت (أو عدة سلوتات متتالية) - المرحلة الأولى قبل الدفع.
    الحجز بينشأ بحالة AWAITING_PAYMENT وله مهلة BOOKING_EXPIRY_MINUTES.
    """
    # --- 1. Parse & validate slot_id ---
    parts = slot_id.split('_')
    if len(parts) != 3:
        messages.error(request, 'رابط الحجز غير صالح')
        return redirect('booking:browse')

    field_id, date_str, display_hour_str = parts
    field = get_object_or_404(Field, id=field_id, is_active=True)

    try:
        display_hour = int(display_hour_str)
        booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, 'بيانات الحجز غير صالحة')
        return redirect('booking:field_detail', field_id=field.id)

    store_hour = display_hour_to_store_hour(display_hour)
    if not (0 <= store_hour <= 23):
        messages.error(request, 'وقت غير صالح')
        return redirect('booking:field_detail', field_id=field.id)

    # --- 2. Validate date/time window ---
    today = date.today()

    if booking_date < today:
        messages.error(request, 'لا يمكن الحجز في تاريخ ماضٍ')
        return redirect('booking:field_detail', field_id=field.id)

    if booking_date > today + timedelta(days=MAX_BOOKING_DAYS_AHEAD):
        messages.error(request, f'لا يمكن الحجز أكثر من {MAX_BOOKING_DAYS_AHEAD} يومًا مقدمًا')
        return redirect('booking:field_detail', field_id=field.id)

    if booking_date == today:
        now = timezone.localtime()
        if store_hour <= now.hour:
            messages.error(request, 'لا يمكن حجز وقت فات')
            return redirect('booking:field_detail', field_id=field.id)

    start_time_display = format_time_display(display_hour)
    end_hour_display = display_hour + 1 if display_hour + 1 != 25 else 1
    end_time_display = format_time_display(end_hour_display)

    # --- GET: show confirmation page ---
    if request.method != 'POST':
        return render(request, 'booking/book_slot.html', {
            'field': field,
            'date': date_str,
            'hour': display_hour,
            'start_time_display': start_time_display,
            'end_time_display': end_time_display,
            'price': field.price_per_hour,
        })

    # --- POST: create the booking ---
    try:
        duration = int(request.POST.get('duration', 1))
    except ValueError:
        messages.error(request, 'مدة الحجز غير صالحة')
        return redirect('booking:field_detail', field_id=field.id)

    if not (1 <= duration <= MAX_BOOKING_DURATION):
        messages.error(request, f'المدة يجب أن تكون بين 1 و {MAX_BOOKING_DURATION} ساعات')
        return redirect('booking:field_detail', field_id=field.id)

    start_time_str, end_time_str, crosses_midnight = get_booking_time_bounds(store_hour, duration)

    # --- 3. Check for overlapping bookings by the same player ---
    if _player_has_overlapping_booking(request.user, booking_date, store_hour, duration,
                                        start_time_str, end_time_str, crosses_midnight):
        messages.error(request, 'لديك حجز آخر في نفس هذا التوقيت')
        return redirect('booking:field_detail', field_id=field.id)

    # --- 4. Lock & create slots inside a transaction ---
    try:
        with transaction.atomic():
            slots_to_book = _lock_consecutive_slots(field, booking_date, store_hour, duration)

            if slots_to_book is None:
                messages.error(request, 'أحد الأوقات المطلوبة لم يعد متاحًا')
                return redirect('booking:field_detail', field_id=field.id)

            for slot in slots_to_book:
                slot.is_available = False
                slot.slot_type = 'RESERVED'
            VenueSlot.objects.bulk_update(slots_to_book, ['is_available', 'slot_type'])

            total_amount = field.price_per_hour * duration

            booking = Booking.objects.create(
                field=field,
                player=request.user,
                booking_date=booking_date,
                start_time=start_time_str,
                end_time=end_time_str,
                total_amount=total_amount,
                status='AWAITING_PAYMENT',
                payment_status='PENDING',
                expires_at=timezone.now() + timedelta(minutes=BOOKING_EXPIRY_MINUTES),
            )

            BookingSlot.objects.bulk_create([
                BookingSlot(booking=booking, slot=slot) for slot in slots_to_book
            ])

            # ملحوظة: مفيش إشعار للمالك هنا عمدًا - بيتبعت بعد رفع صورة الدفع (payment/views.py)

            messages.info(
                request,
                f'✅ تم حجز الموعد لك مؤقتًا لمدة {BOOKING_EXPIRY_MINUTES} دقيقة. '
                f'يرجى إتمام الدفع ورفع الصورة للتأكيد.'
            )
            return redirect('payment:initiate_instapay', booking_id=booking.id)

    except IntegrityError as e:
        logger.exception(f"IntegrityError in book_slot: {e}")
        messages.error(request, '❌ فشل الحجز بسبب تعارض. حاول مرة أخرى.')
        return redirect('booking:field_detail', field_id=field.id)
    except Exception as e:
        logger.exception(f"Error in book_slot: {e}")
        messages.error(request, '❌ حدث خطأ أثناء الحجز. حاول مرة أخرى.')
        return redirect('booking:field_detail', field_id=field.id)


def _player_has_overlapping_booking(player, booking_date, store_hour, duration,
                                     start_time_str, end_time_str, crosses_midnight):
    """
    يتحقق إن اللاعب مالوش حجز نشط بيتعارض مع الفترة المطلوبة.
    بيغطي حالة العبور لليوم التالي (crosses_midnight) بالكامل.
    """
    active_statuses = ['AWAITING_PAYMENT', 'PAYMENT_REVIEW', 'CONFIRMED']

    if not crosses_midnight:
        return Booking.objects.filter(
            player=player,
            status__in=active_statuses,
            booking_date=booking_date,
            start_time__lt=end_time_str,
            end_time__gt=start_time_str,
        ).exists()

    # الحجز بيعدي منتصف الليل: لازم نفحص جزئين
    # الجزء الأول: من start_time لحد 24:00 في booking_date
    part1_overlap = Booking.objects.filter(
        player=player,
        status__in=active_statuses,
        booking_date=booking_date,
        start_time__lt="23:59:59",
        end_time__gt=start_time_str,
    ).exists()
    if part1_overlap:
        return True

    # الجزء التاني: من 00:00 لحد end_time في اليوم التالي
    next_day = booking_date + timedelta(days=1)
    part2_overlap = Booking.objects.filter(
        player=player,
        status__in=active_statuses,
        booking_date=next_day,
        start_time__lt=end_time_str,
        end_time__gt="00:00:00",
    ).exists()
    return part2_overlap


def _lock_consecutive_slots(field, booking_date, store_hour, duration):
    """
    يقفل (select_for_update) كل السلوتات المطلوبة بالترتيب، ويرجعهم كـ list.
    لو أي سلوت مش متاح، يرجع None (يعني فشل كامل - يتم الـ rollback في الطبقة اللي فوق).
    """
    slots = []
    for i in range(duration):
        target_date, actual_hour = build_slot_datetime(booking_date, store_hour, i)
        start_time_str = f"{actual_hour:02d}:00:00"

        slot = VenueSlot.objects.select_for_update().filter(
            field=field,
            date=target_date,
            start_time=start_time_str,
            is_available=True,
        ).first()

        if not slot:
            return None

        slots.append(slot)

    return slots


# ============================================================
# 4. BOOKING HISTORY
# ============================================================
@player_required
def booking_history(request):
    """عرض تاريخ الحجوزات للمستخدم مقسّمة لقادمة وسابقة"""
    today = date.today()
    now_time = timezone.localtime().time()

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
            if booking.start_time >= now_time:
                upcoming_bookings.append(booking)
            else:
                past_bookings.append(booking)
        else:
            past_bookings.append(booking)

    return render(request, 'booking/booking_history.html', {
        'upcoming_bookings': upcoming_bookings,
        'past_bookings': past_bookings,
    })


# ============================================================
# 5. CANCEL BOOKING
# ============================================================
@player_required
def cancel_booking(request, booking_id):
    """إلغاء حجز من طرف اللاعب (قبل بدء وقته)"""
    booking = get_object_or_404(Booking, id=booking_id, player=request.user)

    if not booking.can_cancel():
        messages.warning(request, 'لا يمكن إلغاء هذا الحجز.')
        return redirect('booking:history')

    field_name = booking.field.name
    booking_date = booking.booking_date
    start_time = booking.start_time
    owner = booking.field.venue.owner

    try:
        with transaction.atomic():
            booking.status = 'CANCELLED'
            booking.payment_status = 'CANCELLED'
            booking.save()

            slots_to_update = []
            for bs in booking.booking_slots.select_related('slot'):
                slot = bs.slot
                slot.is_available = True
                slot.slot_type = 'OPEN'
                slots_to_update.append(slot)

            if slots_to_update:
                VenueSlot.objects.bulk_update(slots_to_update, ['is_available', 'slot_type'])

            create_notification(
                user=owner,
                title="❌ تم إلغاء حجز",
                message=f"قام {request.user.username} بإلغاء حجز ملعب {field_name} "
                        f"بتاريخ {booking_date} الساعة {start_time}.",
                url=f"/venues/booking/{booking.id}/details/"
            )

            messages.success(request, '✅ تم إلغاء الحجز وفتح الأوقات المرتبطة به.')
            return redirect('booking:history')

    except Exception as e:
        logger.exception(f"Error cancelling booking {booking_id}: {e}")
        messages.error(request, '❌ حدث خطأ أثناء الإلغاء. حاول مرة أخرى.')
        return redirect('booking:history')


# ============================================================
# ملحوظة: cleanup_expired_bookings اتنقلت لـ management command مستقل
# راجع: booking/management/commands/cleanup_expired.py
# ============================================================