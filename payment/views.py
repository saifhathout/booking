# payment/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required  # ✅ تأكد من الاستيراد
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta

from accounts.decorators import player_required
from venues.models import Booking, VenueSlot
from notifications.utils import create_notification
from .models import InstaPayPayment

import random
import string


@player_required
def initiate_instapay_payment(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, player=request.user)
    
    # ✅ المدة = عدد السلوتات
    duration = booking.slots.count()
    
    # ✅ السعر الإجمالي = عدد السلوتات × سعر الساعة
    total_amount = float(booking.field.price_per_hour) * duration
    
    payment = InstaPayPayment.objects.filter(booking=booking, status='pending').first()
    
    if not payment:
        note_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        unique_amount = total_amount + (random.randint(10, 99) / 100)
        
        payment = InstaPayPayment.objects.create(
            booking=booking,
            user=request.user,
            amount=unique_amount,
            note_code=note_code,
        )
    
    context = {
        'payment': payment,
        'booking': booking,
        'instapay_number': '01012345678',
        'amount': payment.amount,
        'note_code': payment.note_code,
        'duration': duration,
        'total_amount': total_amount,
    }
    
    return render(request, 'payment/instapay_payment.html', context)

# payment/views.py

@player_required
def upload_screenshot(request, payment_id):
    payment = get_object_or_404(InstaPayPayment, id=payment_id, user=request.user)
    booking = payment.booking  # ✅ جلب الحجز
    
    # ✅ التحقق من صلاحية القفل
    if booking.is_locked_expired():
        booking.release_slots()
        booking.status = 'EXPIRED'
        booking.save()
        messages.error(request, '⏰ انتهت صلاحية الحجز، يرجى إعادة المحاولة')
        return redirect('booking:field_detail', field_id=booking.field.id)
    
    if request.method == 'GET':
        return render(request, 'payment/upload_screenshot.html', {
            'payment': payment,
            'booking': booking,  # ✅ إرسال booking إلى القالب
        })
    
    if request.method == 'POST' and request.FILES.get('screenshot'):
        payment.screenshot = request.FILES['screenshot']
        payment.status = 'manual_review'
        payment.notes = "في انتظار المراجعة من قبل الإدارة"
        payment.save()
        
        owner = payment.booking.field.venue.owner
        create_notification(
            user=owner,
            title="📸 طلب دفع جديد يحتاج مراجعة",
            message=f"قام {request.user.username} برفع صورة دفع لحجز ملعب {payment.booking.field.name}.",
            url=f"/payment/verify/{payment.id}/"
        )
        
        messages.success(request, "✅ تم رفع الصورة، سيتم مراجعتها من قبل الإدارة")
        return redirect('booking:history')
    
    messages.error(request, "❌ لم يتم اختيار صورة")
    return render(request, 'payment/upload_screenshot.html', {
        'payment': payment,
        'booking': booking,  # ✅ إرسال booking حتى في حالة الخطأ
    })


@player_required
def payment_pending(request, payment_id):
    """صفحة انتظار التأكيد"""
    payment = get_object_or_404(InstaPayPayment, id=payment_id, user=request.user)
    
    if payment.status == 'approved':
        messages.info(request, '✅ هذا الدفع تم تأكيده بالفعل')
        return redirect('booking:history')
    
    if payment.status == 'rejected':
        messages.warning(request, '❌ هذا الدفع مرفوض')
        return redirect('booking:history')
    
    context = {
        'payment': payment,
        'booking': payment.booking,
        'time_remaining': 15,
    }
    
    return render(request, 'payment/payment_pending.html', context)


@login_required
def verify_payment(request, payment_id):
    payment = get_object_or_404(InstaPayPayment, id=payment_id)
    
    if request.user != payment.booking.field.venue.owner:
        messages.error(request, "❌ ليس لديك صلاحية")
        return redirect('venues:owner_dashboard')
    
    if payment.status == 'approved':
        messages.warning(request, '⚠️ هذا الدفع تم تأكيده بالفعل')
        return redirect('venues:owner_dashboard')
    
    if payment.status == 'rejected':
        messages.warning(request, '⚠️ هذا الدفع مرفوض سابقاً')
        return redirect('venues:owner_dashboard')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            try:
                with transaction.atomic():
                    booking = payment.booking
                    
                    if booking.status == 'CONFIRMED':
                        messages.warning(request, '⚠️ هذا الحجز مؤكد بالفعل')
                        return redirect('venues:owner_dashboard')
                    
                    if booking.status in ['CANCELLED', 'EXPIRED']:
                        messages.warning(request, '⚠️ هذا الحجز ملغى أو منتهي الصلاحية')
                        return redirect('venues:owner_dashboard')
                    
                    # ✅ التحقق من صلاحية القفل
                    if booking.is_locked_expired():
                        booking.release_slots()
                        booking.status = 'EXPIRED'
                        booking.save()
                        messages.error(request, '❌ انتهت صلاحية الحجز')
                        return redirect('venues:owner_dashboard')
                    
                    # ✅ التحقق من السلوتات - بدون حسابات!
                    for slot in booking.slots.all():
                        slot = VenueSlot.objects.select_for_update().get(pk=slot.pk)
                        if slot.is_available or slot.slot_type != 'LOCKED':
                            booking.release_slots()
                            messages.error(request, '❌ السلوتات غير متاحة حالياً')
                            return redirect('venues:owner_dashboard')
                    
                    # ✅ تأكيد الحجز
                    payment.status = 'approved'
                    payment.verified_at = timezone.now()
                    payment.save()
                    
                    booking.confirm_booking()
                    
                    create_notification(
                        user=booking.player,
                        title="✅ تم تأكيد حجزك!",
                        message=f"تم تأكيد حجز ملعب {booking.field.name}.",
                        url="/booking/history/"
                    )
                    
                    messages.success(request, '✅ تم تأكيد الدفع والحجز بنجاح!')
                    
            except Exception as e:
                messages.error(request, f'❌ حدث خطأ: {str(e)}')
                return redirect('venues:owner_dashboard')
                
        elif action == 'reject':
            with transaction.atomic():
                payment.status = 'rejected'
                payment.save()
                booking = payment.booking
                booking.release_slots()
                
                create_notification(
                    user=booking.player,
                    title="❌ تم رفض حجزك",
                    message=f"تم رفض حجز ملعب {booking.field.name}.",
                    url="/booking/history/"
                )
                
            messages.warning(request, '❌ تم رفض الدفع')
        
        return redirect('venues:owner_dashboard')
    
    return redirect('venues:owner_dashboard')

