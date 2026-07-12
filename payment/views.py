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


# payment/views.py

def initiate_instapay_payment(request, booking_id):
    # ✅ جلب الحجز (من غير فلتر player عشان الضيف)
    booking = get_object_or_404(Booking, id=booking_id)
    
    # ✅ التحقق من أن المستخدم هو صاحب الحجز (لو مسجل)
    if request.user.is_authenticated:
        if booking.player and booking.player != request.user:
            messages.error(request, "❌ هذا الحجز ليس لك!")
            return redirect('booking:browse')
    else:
        # ✅ لو ضيف، تأكد من الـ session
        if not request.session.get('guest_name'):
            messages.error(request, "❌ يرجى إدخال بياناتك أولاً")
            return redirect('booking:browse')
    
    # ✅ المدة = عدد السلوتات
    duration = booking.slots.count()
    
    # ✅ السعر الإجمالي = عدد السلوتات × سعر الساعة
    total_amount = float(booking.field.price_per_hour) * duration
    
    payment = InstaPayPayment.objects.filter(booking=booking, status='pending').first()
    
    if not payment:
        note_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        unique_amount = total_amount + (random.randint(10, 99) / 100)
        
        # ✅ استخدم request.user لو مسجل، وإلا None
        user = request.user if request.user.is_authenticated else None
        
        payment = InstaPayPayment.objects.create(
            booking=booking,
            user=user,  # ✅ معرفة
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

# payment/views.py

# payment/views.py

# payment/views.py

# payment/views.py

from payment.utils import upload_screenshot_to_supabase, delete_screenshot_from_supabase


# payment/views.py

from payment.utils import upload_screenshot_to_supabase


# payment/views.py

# @player_required
# payment/views.py

def upload_screenshot(request, payment_id):
    # ✅ جلب الدفع (من غير فلتر user)
    payment = get_object_or_404(InstaPayPayment, id=payment_id)
    booking = payment.booking
    
    # ✅ التحقق من الصلاحية
    if request.user.is_authenticated:
        # ✅ مسجل - اتأكد إنه صاحب الحجز
        if booking.player and booking.player != request.user:
            messages.error(request, "❌ هذا الحجز ليس لك!")
            return redirect('booking:browse')
    else:
        # ✅ ضيف - اتأكد من بياناته في الـ session
        guest_name = request.session.get('guest_name')
        if not guest_name:
            messages.error(request, "❌ يرجى تسجيل الدخول أولاً")
            return redirect('accounts:login')
        
        # ✅ اتأكد إن ده حجز الضيف
        if booking.guest_name != guest_name:
            messages.error(request, "❌ هذا الحجز ليس لك!")
            return redirect('booking:browse')
    
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
            'booking': booking,
            'is_expired': False,
        })
    
    if request.method == 'POST' and request.FILES.get('screenshot'):
        # ✅ حفظ الصورة
        file = request.FILES['screenshot']
        
        # ✅ رفع الصورة (لو عندك)
        # public_url = upload_screenshot_to_supabase(file, booking.id)
        
        # ✅ مؤقتاً - حفظ الصورة محلياً (للتجربة)
        payment.screenshot = file
        payment.status = 'manual_review'
        payment.notes = "في انتظار المراجعة من قبل الإدارة"
        payment.save()
        
        # ✅ إرسال إشعار للمالك
        owner = payment.booking.field.venue.owner
        create_notification(
            user=owner,
            title="📸 طلب دفع جديد يحتاج مراجعة",
            message=f"قام {request.user.username if request.user.is_authenticated else booking.guest_name} برفع صورة دفع لحجز ملعب {payment.booking.field.name}.",
            url=f"/payment/verify/{payment.id}/"
        )
        
        messages.success(request, "✅ تم رفع الصورة، سيتم مراجعتها من قبل الإدارة")
        return redirect('payment:payment_pending', payment_id=payment.id)
    
    messages.error(request, "❌ لم يتم اختيار صورة")
    return render(request, 'payment/upload_screenshot.html', {
        'payment': payment,
        'booking': booking,
        'is_expired': False,
    })
# payment/views.py

# payment/views.py

def payment_pending(request, payment_id):
    payment = get_object_or_404(InstaPayPayment, id=payment_id)
    booking = payment.booking
    
    # ✅ التحقق من الصلاحية
    if request.user.is_authenticated:
        if booking.player and booking.player != request.user:
            messages.error(request, "❌ هذا الحجز ليس لك!")
            return redirect('booking:browse')
        # ✅ مسجل → استخدم بيانات المستخدم
        user_name = request.user.username
        user_email = request.user.email
        user_phone = request.user.phone if hasattr(request.user, 'phone') else ''
        is_guest = False
    else:
        # ✅ ضيف → استخدم بيانات الضيف من الحجز
        guest_name = request.session.get('guest_name')
        if not guest_name:
            messages.error(request, "❌ يرجى تسجيل الدخول أولاً")
            return redirect('accounts:login')
        
        if booking.guest_name != guest_name:
            messages.error(request, "❌ هذا الحجز ليس لك!")
            return redirect('booking:browse')
        
        user_name = booking.guest_name
        user_email = booking.guest_email
        user_phone = booking.guest_phone
        is_guest = True
    
    # ✅ حالة الحجز
    status_map = {
        'LOCKED': {'text': '⏳ قيد المراجعة', 'color': 'text-yellow-400', 'bg': 'bg-yellow-500/20 border-yellow-500/30'},
        'CONFIRMED': {'text': '✅ تم التأكيد', 'color': 'text-green-400', 'bg': 'bg-green-500/20 border-green-500/30'},
        'REJECTED': {'text': '❌ مرفوض', 'color': 'text-red-400', 'bg': 'bg-red-500/20 border-red-500/30'},
        'CANCELLED': {'text': '❌ ملغي', 'color': 'text-red-400', 'bg': 'bg-red-500/20 border-red-500/30'},
        'EXPIRED': {'text': '⏰ منتهي', 'color': 'text-white/40', 'bg': 'bg-white/10 border-white/10'},
    }
    
    status_info = status_map.get(booking.status, {'text': '⏳ قيد المعالجة', 'color': 'text-yellow-400', 'bg': 'bg-yellow-500/20 border-yellow-500/30'})
    
    context = {
        'payment': payment,
        'booking': booking,
        'status_info': status_info,
        'user_name': user_name,
        'user_email': user_email,
        'user_phone': user_phone,
        'is_guest': is_guest,
    }
    
    return render(request, 'payment/payment_pending.html', context)

# payment/views.py

# payment/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import transaction

from venues.models import Booking, VenueSlot
from notifications.utils import create_notification
from .models import InstaPayPayment


# payment/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import transaction

from venues.models import Booking, VenueSlot
from notifications.utils import create_notification
from .models import InstaPayPayment
from .utils import delete_screenshot_from_supabase  # ✅ استيراد دالة الحذف


@login_required
def verify_payment(request, payment_id):
    payment = get_object_or_404(InstaPayPayment, id=payment_id)
    booking = payment.booking
    
    # ✅ التحقق من الصلاحية - المالك بس
    if request.user != booking.field.venue.owner:
        messages.error(request, "❌ ليس لديك صلاحية")
        return redirect('dashboard:owner_dashboard')
    
    # ✅ منع الضغط المكرر
    if payment.status == 'approved':
        messages.warning(request, '⚠️ هذا الدفع تم تأكيده بالفعل')
        return redirect('dashboard:owner_dashboard')
    
    if payment.status == 'rejected':
        messages.warning(request, '⚠️ هذا الدفع مرفوض سابقاً')
        return redirect('dashboard:owner_dashboard')
    
    # ✅ عرض الصفحة
    if request.method == 'GET':
        return render(request, 'payment/verify_payment.html', {
            'payment': payment,
            'booking': booking,
        })
    
    # ✅ معالجة POST (Approve / Reject)
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            try:
                with transaction.atomic():
                    # ✅ التحقق من حالة الحجز
                    if booking.status == 'CONFIRMED':
                        messages.warning(request, '⚠️ هذا الحجز مؤكد بالفعل')
                        return redirect('dashboard:owner_dashboard')
                    
                    if booking.status in ['CANCELLED', 'EXPIRED']:
                        messages.warning(request, '⚠️ هذا الحجز ملغى أو منتهي الصلاحية')
                        return redirect('dashboard:owner_dashboard')
                    
                    # ✅ التحقق من صلاحية القفل
                    if booking.is_locked_expired():
                        booking.release_slots()
                        booking.status = 'EXPIRED'
                        booking.save()
                        messages.error(request, '❌ انتهت صلاحية الحجز')
                        return redirect('dashboard:owner_dashboard')
                    
                    # ✅ التحقق من السلوتات
                    for slot in booking.slots.all():
                        slot = VenueSlot.objects.select_for_update().get(pk=slot.pk)
                        if slot.is_available or slot.slot_type != 'LOCKED':
                            booking.release_slots()
                            messages.error(request, '❌ السلوتات غير متاحة حالياً')
                            return redirect('dashboard:owner_dashboard')
                    
                    # ✅ تأكيد الدفع
                    payment.status = 'approved'
                    payment.verified_at = timezone.now()
                    payment.save()
                    
                    # ✅ تأكيد الحجز (قفل السلوتات)
                    booking.confirm_booking()
                    
                    # ✅ ✅ ✅ حذف الصورة من Supabase بعد الموافقة
                    if payment.screenshot_url:
                        delete_screenshot_from_supabase(payment.screenshot_url)
                        payment.screenshot_url = None
                        payment.save()
                    
                    # ✅ إشعار للاعب
                    create_notification(
                        user=booking.player,
                        title="✅ تم تأكيد حجزك!",
                        message=f"تم تأكيد حجز ملعب {booking.field.name}.",
                        url="/booking/history/"
                    )
                    
                    messages.success(request, '✅ تم تأكيد الدفع والحجز بنجاح!')
                    
            except Exception as e:
                messages.error(request, f'❌ حدث خطأ: {str(e)}')
                return redirect('dashboard:owner_dashboard')
                
        elif action == 'reject':
            try:
                with transaction.atomic():
                    # ✅ رفض الدفع
                    payment.status = 'rejected'
                    payment.save()
                    
                    # ✅ تحرير السلوتات
                    booking.release_slots()
                    
                    # ✅ ✅ ✅ حذف الصورة من Supabase بعد الرفض
                    if payment.screenshot_url:
                        delete_screenshot_from_supabase(payment.screenshot_url)
                        payment.screenshot_url = None
                        payment.save()
                    
                    # ✅ إشعار للاعب
                    create_notification(
                        user=booking.player,
                        title="❌ تم رفض حجزك",
                        message=f"تم رفض حجز ملعب {booking.field.name}.",
                        url="/booking/history/"
                    )
                    
                messages.warning(request, '❌ تم رفض الدفع')
                
            except Exception as e:
                messages.error(request, f'❌ حدث خطأ: {str(e)}')
        
        return redirect('dashboard:owner_dashboard')
    
    return redirect('dashboard:owner_dashboard')

# payment/views.py

@player_required
def manual_review(request, payment_id):
    """
    صفحة المراجعة اليدوية للمدفوعات (للمستخدم نفسه)
    """
    payment = get_object_or_404(InstaPayPayment, id=payment_id, user=request.user)
    booking = payment.booking
    
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        
        if action == 'approve':
            try:
                with transaction.atomic():
                    # ✅ التحقق من صلاحية القفل
                    if booking.is_locked_expired():
                        booking.release_slots()
                        booking.status = 'EXPIRED'
                        booking.save()
                        messages.error(request, '❌ انتهت صلاحية الحجز')
                        return redirect('booking:history')
                    
                    # ✅ التحقق من السلوتات
                    for slot in booking.slots.all():
                        slot = VenueSlot.objects.select_for_update().get(pk=slot.pk)
                        if slot.is_available or slot.slot_type != 'LOCKED':
                            booking.release_slots()
                            messages.error(request, '❌ السلوتات غير متاحة حالياً')
                            return redirect('booking:history')
                    
                    # ✅ تأكيد الدفع
                    payment.status = 'approved'
                    payment.verified_at = timezone.now()
                    payment.save()
                    
                    # ✅ تأكيد الحجز (قفل السلوتات)
                    booking.confirm_booking()
                    
                    # ✅ إشعار للاعب
                    create_notification(
                        user=booking.player,
                        title="✅ تم تأكيد حجزك!",
                        message=f"تم تأكيد حجز ملعب {booking.field.name}.",
                        url="/booking/history/"
                    )
                    
                    messages.success(request, '✅ تم تأكيد الدفع والحجز بنجاح!')
                    
            except Exception as e:
                messages.error(request, f'❌ حدث خطأ: {str(e)}')
                
        elif action == 'reject':
            try:
                with transaction.atomic():
                    # ✅ رفض الدفع
                    payment.status = 'rejected'
                    payment.save()
                    
                    # ✅ تحرير السلوتات
                    booking.release_slots()
                    
                    # ✅ إشعار للاعب
                    create_notification(
                        user=booking.player,
                        title="❌ تم رفض حجزك",
                        message=f"تم رفض حجز ملعب {booking.field.name}.",
                        url="/booking/history/"
                    )
                    
                messages.warning(request, '❌ تم رفض الدفع')
                
            except Exception as e:
                messages.error(request, f'❌ حدث خطأ: {str(e)}')
            
        elif action == 'pending':
            # ✅ إرجاع الدفع للحالة المعلقة
            payment.status = 'pending'
            messages.info(request, '⏳ تم إرجاع الدفع للحالة المعلقة')
        
        # ✅ حفظ الملاحظات
        if notes:
            payment.notes = notes
        payment.save()
        
        return redirect('booking:history')
    
    # ✅ GET request - عرض صفحة المراجعة
    context = {
        'payment': payment,
        'booking': booking,
    }
    
    return render(request, 'payment/manual_review.html', context)


