# payment/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
import logging
import random
import string

from accounts.decorators import player_required
from booking.models import Booking
from venues.models import VenueSlot
from .models import InstaPayPayment
from notifications.utils import create_notification

logger = logging.getLogger(__name__)

INSTAPAY_NUMBER = '01012345678'
PAYMENT_PENDING_EXPIRY_MINUTES = 30  # نفس القيمة المستخدمة في التنظيف


# ============================================================
# 1. INITIATE PAYMENT
# ============================================================
@player_required
def initiate_instapay_payment(request, booking_id):
    """
    إنشاء/عرض طلب دفع InstaPay لحجز معين.
    الحجز لازم يكون لسه AWAITING_PAYMENT وإلا مفيش داعي (أو مسموح) للدفع.
    """
    booking = get_object_or_404(Booking, id=booking_id, player=request.user)

    if not request.user.id:
        messages.error(request, "❌ يرجى تسجيل الدخول مرة أخرى.")
        return redirect('accounts:login')

    # لازم الحجز يكون في حالة انتظار الدفع - بيمنع إعادة تفعيل
    # دفع مرفوض/منتهي/ملغي لو رجع المستخدم لنفس اللينك بالغلط
    if booking.status != 'AWAITING_PAYMENT':
        messages.error(request, "❌ هذا الحجز لم يعد متاحًا للدفع.")
        return redirect('booking:history')

    if booking.is_expired():
        messages.error(request, "❌ انتهت مهلة هذا الحجز.")
        return redirect('booking:history')

    # المدة والمبلغ بيتحسبوا مرة واحدة وقت الحجز نفسه - بنستخدمهم زي ما هما
    duration = booking.get_duration()
    total_amount = float(booking.total_amount)

    try:
        payment, created = InstaPayPayment.objects.get_or_create(
            booking=booking,
            defaults={
                'user_id': request.user.id,
                'amount': _generate_unique_amount(total_amount),
                'note_code': _generate_note_code(),
                'status': 'pending',
            }
        )
    except Exception as e:
        logger.exception(f"Error creating payment for booking {booking_id}: {e}")
        messages.error(request, "❌ حدث خطأ أثناء إنشاء طلب الدفع.")
        return redirect('booking:history')

    if not created and payment.status != 'pending':
        payment.status = 'pending'
        payment.save(update_fields=['status'])

    context = {
        'payment': payment,
        'booking': booking,
        'instapay_number': INSTAPAY_NUMBER,
        'amount': payment.amount,
        'note_code': payment.note_code,
        'duration': duration,
        'total_amount': total_amount,
    }
    return render(request, 'payment/instapay_payment.html', context)


def _generate_unique_amount(base_amount):
    """
    بيضيف كسر عشوائي صغير للمبلغ عشان يسهل مطابقة التحويل يدويًا
    (كل طلب دفع له مبلغ فريد قريب من المبلغ الأصلي).
    """
    return round(base_amount + (random.randint(10, 99) / 100), 2)


def _generate_note_code(length=5):
    """كود مرجعي قصير يُطلب من المستخدم كتابته في خانة الملاحظات وقت التحويل."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


# ============================================================
# 2. UPLOAD SCREENSHOT
# ============================================================
@player_required
def upload_screenshot(request, payment_id):
    """
    اللاعب بيرفع صورة إثبات الدفع.
    بعد الرفع: الحجز بيتحول لـ PAYMENT_REVIEW ويتبعت إشعار للمالك.
    """
    payment = get_object_or_404(InstaPayPayment, id=payment_id, user=request.user)
    booking = payment.booking

    if booking.status != 'AWAITING_PAYMENT':
        messages.error(request, "❌ هذا الحجز لا ينتظر رفع صورة دفع حاليًا.")
        return redirect('booking:history')

    if request.method != 'POST' or not request.FILES.get('screenshot'):
        messages.error(request, "❌ لم يتم اختيار صورة")
        return render(request, 'payment/upload_screenshot.html', {'payment': payment})

    try:
        with transaction.atomic():
            payment.screenshot = request.FILES['screenshot']
            payment.status = 'manual_review'
            payment.notes = "في انتظار المراجعة من قبل الإدارة"
            payment.save()

            booking.status = 'PAYMENT_REVIEW'
            booking.save(update_fields=['status'])

            owner = booking.field.venue.owner
            if owner:
                create_notification(
                    user=owner,
                    title="📸 طلب دفع جديد يحتاج مراجعة",
                    message=f"قام {request.user.username} برفع صورة دفع لحجز ملعب "
                            f"{booking.field.name} بتاريخ {booking.booking_date}.",
                    url=f"/venues/booking/{booking.id}/details/"
                )
    except Exception as e:
        logger.exception(f"Error uploading screenshot for payment {payment_id}: {e}")
        messages.error(request, "❌ حدث خطأ أثناء رفع الصورة. حاول مرة أخرى.")
        return render(request, 'payment/upload_screenshot.html', {'payment': payment})

    messages.success(request, "✅ تم رفع الصورة، في انتظار مراجعة المالك")
    return redirect('booking:history')


# ============================================================
# 3. PAYMENT PENDING PAGE
# ============================================================
@player_required
def payment_pending(request, payment_id):
    """صفحة انتظار مراجعة الدفع من المالك"""
    payment = get_object_or_404(InstaPayPayment, id=payment_id, user=request.user)

    if payment.status == 'approved':
        messages.info(request, '✅ هذا الدفع تم تأكيده بالفعل')
        return redirect('booking:history')

    if payment.status == 'rejected':
        messages.warning(request, '❌ هذا الدفع مرفوض')
        return redirect('booking:history')

    if payment.status == 'expired':
        messages.warning(request, '⏳ انتهت صلاحية طلب الدفع هذا')
        return redirect('booking:history')

    return render(request, 'payment/payment_pending.html', {
        'payment': payment,
        'booking': payment.booking,
    })


# ============================================================
# 4 & 5. OWNER REVIEW ACTIONS (verify_payment + manual_review)
#
# الدالتين القديمتين كانوا بينفذوا نفس الفعل (approve/reject) بمنطق
# متكرر ومتناقض شوية (verify_payment كان بيحط REJECTED، manual_review
# كان بيحط CANCELLED). دلوقتي المنطق الفعلي موحّد في دالتين مساعدتين،
# والـ views بس بتتحقق من الصلاحيات وتستدعيهم.
# ============================================================

def _approve_payment(payment, booking, approved_by, notes=None):
    """يوافق على الدفع، يأكد الحجز، يقفل السلوتات، ويبعت الإشعارات."""
    with transaction.atomic():
        payment.status = 'approved'
        payment.verified_at = timezone.now()
        if notes:
            payment.notes = notes
        payment.save()

        booking.status = 'CONFIRMED'
        booking.payment_status = 'PAID'
        booking.save()

        slots_to_close = []
        for bs in booking.booking_slots.select_related('slot'):
            slot = bs.slot
            if slot.is_available or slot.slot_type != 'BOOKED':
                slot.is_available = False
                slot.slot_type = 'BOOKED'
                slots_to_close.append(slot)
        if slots_to_close:
            VenueSlot.objects.bulk_update(slots_to_close, ['is_available', 'slot_type'])

        create_notification(
            user=booking.player,
            title="✅ تم تأكيد حجزك!",
            message=f"تم تأكيد حجز ملعب {booking.field.name} بتاريخ "
                    f"{booking.booking_date} الساعة {booking.start_time}.",
            url="/booking/history/"
        )
        create_notification(
            user=approved_by,
            title="✅ تم تأكيد الدفع",
            message=f"تم تأكيد دفع حجز {booking.player.username} في ملعب {booking.field.name}.",
            url="/venues/booking_requests/"
        )


def _reject_payment(payment, booking, rejected_by, notes=None):
    """يرفض الدفع، يرفض الحجز (REJECTED دايمًا)، يفتح السلوتات، ويبعت الإشعارات."""
    with transaction.atomic():
        payment.status = 'rejected'
        if notes:
            payment.notes = notes
        payment.save()

        # ✅ REJECTED دايمًا (مش CANCELLED) - رفض المالك يختلف عن إلغاء اللاعب
        booking.status = 'REJECTED'
        booking.payment_status = 'REJECTED'
        booking.save()

        slots_to_open = []
        for bs in booking.booking_slots.select_related('slot'):
            slot = bs.slot
            if not slot.is_available:
                slot.is_available = True
                slot.slot_type = 'OPEN'
                slots_to_open.append(slot)
        if slots_to_open:
            VenueSlot.objects.bulk_update(slots_to_open, ['is_available', 'slot_type'])

        create_notification(
            user=booking.player,
            title="❌ تم رفض حجزك",
            message=f"تم رفض حجز ملعب {booking.field.name} بتاريخ "
                    f"{booking.booking_date}. يرجى التواصل مع الإدارة.",
            url="/booking/history/"
        )
        create_notification(
            user=rejected_by,
            title="❌ تم رفض الدفع",
            message=f"تم رفض دفع حجز {booking.player.username} في ملعب {booking.field.name}.",
            url="/venues/booking_requests/"
        )


@login_required
def verify_payment(request, payment_id):
    """تأكيد أو رفض الدفع من طرف مالك الملعب - المسار السريع (زر approve/reject مباشر)"""
    payment = get_object_or_404(InstaPayPayment, id=payment_id)
    booking = payment.booking

    if request.user != booking.field.venue.owner:
        messages.error(request, "❌ ليس لديك صلاحية لهذا الإجراء")
        return redirect('venues:owner_dashboard')

    if booking.status != 'PAYMENT_REVIEW':
        messages.warning(request, f"⚠️ هذا الحجز بحالة {booking.get_status_display()}")
        return redirect('venues:owner_dashboard')

    if payment.status == 'expired':
        messages.error(request, "❌ انتهت صلاحية طلب الدفع")
        return redirect('venues:owner_dashboard')

    if request.method != 'POST':
        return redirect('venues:owner_dashboard')

    action = request.POST.get('action')

    try:
        if action == 'approve':
            _approve_payment(payment, booking, approved_by=request.user)
            messages.success(request, '✅ تم تأكيد الدفع والحجز بنجاح!')
            logger.info(f"Payment {payment_id} approved by {request.user.username}")
        elif action == 'reject':
            _reject_payment(payment, booking, rejected_by=request.user)
            messages.warning(request, '❌ تم رفض الدفع')
            logger.info(f"Payment {payment_id} rejected by {request.user.username}")
        else:
            messages.error(request, '❌ إجراء غير صحيح')
    except Exception as e:
        logger.exception(f"Error processing payment {payment_id} action={action}: {e}")
        messages.error(request, '❌ حدث خطأ أثناء تنفيذ الإجراء. يرجى المحاولة مرة أخرى.')

    return redirect('venues:owner_dashboard')


@login_required
def manual_review(request, payment_id):
    """صفحة المراجعة اليدوية التفصيلية (approve/reject/pending + ملاحظات)"""
    payment = get_object_or_404(InstaPayPayment, id=payment_id)
    booking = payment.booking

    if request.user != booking.field.venue.owner:
        messages.error(request, "❌ ليس لديك صلاحية لهذا الإجراء")
        return redirect('venues:owner_dashboard')

    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '').strip() or None

        try:
            if action == 'approve':
                _approve_payment(payment, booking, approved_by=request.user, notes=notes)
                messages.success(request, '✅ تم تأكيد الدفع والحجز بنجاح!')
            elif action == 'reject':
                _reject_payment(payment, booking, rejected_by=request.user, notes=notes)
                messages.warning(request, '❌ تم رفض الدفع')
            elif action == 'pending':
                payment.status = 'pending'
                if notes:
                    payment.notes = notes
                payment.save()
                messages.info(request, '⏳ تم إرجاع الدفع للحالة المعلقة')
            else:
                messages.error(request, '❌ إجراء غير صحيح')
        except Exception as e:
            logger.exception(f"Error in manual_review action={action} for payment {payment_id}: {e}")
            messages.error(request, '❌ حدث خطأ أثناء تنفيذ الإجراء. يرجى المحاولة مرة أخرى.')

        return redirect('venues:owner_dashboard')

    return render(request, 'payment/manual_review.html', {
        'payment': payment,
        'booking': booking,
        'screenshot_url': payment.screenshot.url if payment.screenshot else None,
    })


# ============================================================
# ملحوظة: cleanup_expired_payments اتنقلت لـ management command مستقل
# راجع: payment/management/commands/cleanup_expired.py
# (نفس الأمر اللي فيه cleanup الحجوزات المنتهية من booking app)
# ============================================================