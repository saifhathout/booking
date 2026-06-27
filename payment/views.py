# payment/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from accounts.decorators import player_required
from venues.models import Booking
from django.contrib.auth.decorators import login_required  # ✅ أضف هذا

from .models import InstaPayPayment
import random
import string
from django.utils import timezone
from notifications.utils import create_notification  # ✅ استخدم دالة الإشعارات الموجودة



# payment/views.py

@player_required
def initiate_instapay_payment(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, player=request.user)
    
    # ✅ حساب المدة من start_time و end_time
    start_h = booking.start_time.hour
    end_h = booking.end_time.hour
    
    # ✅ حساب عدد الساعات
    if end_h <= start_h:
        duration = 24 - start_h + end_h
    else:
        duration = end_h - start_h
    
    # ✅ السعر الإجمالي = سعر الساعة × المدة
    total_amount = float(booking.field.price_per_hour) * duration
    
    payment = InstaPayPayment.objects.filter(booking=booking, status='pending').first()
    
    if not payment:
        note_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        unique_amount = total_amount + (random.randint(10, 99) / 100)  # ✅ استخدم total_amount
        
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
        'duration': duration,  # ✅ أضف المدة للعرض
        'total_amount': total_amount,  # ✅ أضف السعر الإجمالي
    }
    
    return render(request, 'payment/instapay_payment.html', context)


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from accounts.decorators import player_required
from venues.models import Booking
from .models import InstaPayPayment
from notifications.utils import create_notification
import random
import string


@player_required
def upload_screenshot(request, payment_id):
    payment = get_object_or_404(InstaPayPayment, id=payment_id, user=request.user)
    
    if request.method == 'GET':
        return render(request, 'payment/upload_screenshot.html', {'payment': payment})
    
    if request.method == 'POST' and request.FILES.get('screenshot'):
        payment.screenshot = request.FILES['screenshot']
        payment.status = 'manual_review'
        payment.notes = "في انتظار المراجعة من قبل الإدارة"
        payment.save()
        
        # ✅ إرسال إشعار للمالك
        owner = payment.booking.field.venue.owner
        create_notification(
            user=owner,
            title="📸 طلب دفع جديد يحتاج مراجعة",
            message=f"قام {request.user.username} برفع صورة دفع لحجز ملعب {payment.booking.field.name}.",
            url=f"/venues/booking/{payment.booking.id}/details/"
        )
        
        messages.success(request, "✅ تم رفع الصورة، سيتم مراجعتها من قبل الإدارة")
        return redirect('booking:history')
    
    messages.error(request, "❌ لم يتم اختيار صورة")
    return render(request, 'payment/upload_screenshot.html', {'payment': payment})
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


# payment/views.py

@login_required
def verify_payment(request, payment_id):
    payment = get_object_or_404(InstaPayPayment, id=payment_id)
    
    if request.user != payment.booking.field.venue.owner:
        messages.error(request, "❌ ليس لديك صلاحية")
        return redirect('venues:owner_dashboard')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            # ✅ قبول الدفع
            payment.status = 'approved'
            payment.verified_at = timezone.now()
            payment.save()
            
            # ✅ تأكيد الحجز
            booking = payment.booking
            booking.status = 'CONFIRMED'
            booking.save()
            
            # ✅ **تقفيل السلوتات هنا (بس بعد الدفع)**
            start_h = booking.start_time.hour
            end_h = booking.end_time.hour
            if end_h == 0:
                end_h = 24
            duration = end_h - start_h if end_h > start_h else 1
            date_str = booking.booking_date.strftime('%Y-%m-%d')
            
            for i in range(duration):
                h = (start_h + i) % 24
                st = f"{h:02d}:00:00"
                slot = booking.slot.objects.filter(
                    field=booking.field,
                    date=date_str,
                    start_time=st
                ).first()
                if slot:
                    slot.is_available = False
                    slot.slot_type = 'BOOKED'
                    slot.save()
            
            # ✅ إشعار للاعب
            from notifications.utils import create_notification
            create_notification(
                user=booking.player,
                title="✅ تم تأكيد حجزك!",
                message=f"تم تأكيد حجز ملعب {booking.field.name} بتاريخ {booking.booking_date}.",
                url="/booking/history/"
            )
            
            messages.success(request, '✅ تم تأكيد الدفع والحجز بنجاح!')
            
        elif action == 'reject':
            # ❌ رفض الدفع
            payment.status = 'rejected'
            payment.save()
            
            booking = payment.booking
            booking.status = 'CANCELLED'
            booking.save()
            
            # ✅ إشعار للاعب
            from notifications.utils import create_notification
            create_notification(
                user=booking.player,
                title="❌ تم رفض حجزك",
                message=f"تم رفض حجز ملعب {booking.field.name}.",
                url="/booking/history/"
            )
            
            messages.warning(request, '❌ تم رفض الدفع')
        
        return redirect('venues:owner_dashboard')

@player_required
def manual_review(request, payment_id):
    """صفحة المراجعة اليدوية للمدفوعات"""
    payment = get_object_or_404(InstaPayPayment, id=payment_id, user=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        
        if action == 'approve':
            payment.status = 'approved'
            payment.verified_at = timezone.now()
            payment.booking.status = 'CONFIRMED'
            payment.booking.save()
            messages.success(request, '✅ تم تأكيد الدفع والحجز بنجاح!')
        elif action == 'reject':
            payment.status = 'rejected'
            messages.warning(request, '❌ تم رفض الدفع')
        elif action == 'pending':
            payment.status = 'pending'
            messages.info(request, '⏳ تم إرجاع الدفع للحالة المعلقة')
        
        if notes:
            payment.notes = notes
        payment.save()
        return redirect('booking:history')
    
    context = {
        'payment': payment,
        'booking': payment.booking,
    }
    
    return render(request, 'payment/manual_review.html', context)



    