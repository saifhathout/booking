# payment/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from accounts.decorators import player_required
from venues.models import Booking  # ✅ من venues
from .models import InstaPayPayment
import random
import string
from django.utils import timezone


@player_required
def initiate_instapay_payment(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, player=request.user)
    
    payment = InstaPayPayment.objects.filter(booking=booking, status='pending').first()
    
    if not payment:
        note_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        unique_amount = float(booking.field.price_per_hour) + (random.randint(10, 99) / 100)
        
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
    }
    
    return render(request, 'payment/instapay_payment.html', context)


@player_required
def upload_screenshot(request, payment_id):
    payment = get_object_or_404(InstaPayPayment, id=payment_id, user=request.user)
    
    if request.method == 'POST' and request.FILES.get('screenshot'):
        payment.screenshot = request.FILES['screenshot']
        payment.save()
        messages.info(request, '✅ تم رفع الصورة بنجاح! جاري المراجعة...')
        return redirect('payment:payment_pending', payment_id=payment.id)
    
    return render(request, 'payment/upload_screenshot.html', {'payment': payment})


@player_required
def payment_pending(request, payment_id):
    """صفحة انتظار التأكيد"""
    payment = get_object_or_404(InstaPayPayment, id=payment_id, user=request.user)
    return render(request, 'payment/payment_pending.html', {'payment': payment})


@player_required
def verify_payment(request, payment_id):
    """تأكيد الدفع يدوياً (للمسؤول)"""
    payment = get_object_or_404(InstaPayPayment, id=payment_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            payment.status = 'approved'
            payment.verified_at = timezone.now()
            payment.booking.status = 'CONFIRMED'
            payment.booking.save()
            messages.success(request, '✅ تم تأكيد الدفع والحجز بنجاح!')
        elif action == 'reject':
            payment.status = 'rejected'
            messages.warning(request, '❌ تم رفض الدفع')
        
        payment.save()
        return redirect('booking:history')
    
    return render(request, 'payment/verify_payment.html', {'payment': payment})