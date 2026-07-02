# booking/models.py

from django.db import models
from django.conf import settings
from venues.models import Field, VenueSlot


class Booking(models.Model):
    """
    نموذج الحجوزات الرئيسي
    """
    STATUS_CHOICES = [
        ('AWAITING_PAYMENT', 'في انتظار الدفع'),      # ✅ المستخدم لم يرفع إثبات الدفع بعد
        ('PAYMENT_REVIEW', 'مراجعة الدفع'),          # ✅ رفع الصورة وينتظر مراجعة المالك
        ('CONFIRMED', 'مؤكد'),                       # ✅ المالك وافق
        ('REJECTED', 'مرفوض'),                       # ❌ المالك رفض
        ('CANCELLED', 'ملغي'),                       # ❌ المستخدم ألغى
        ('EXPIRED', 'منتهي'),                        # ⏳ انتهت المهلة
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'قيد الانتظار'),
        ('PAID', 'مدفوع'),
        ('CANCELLED', 'ملغي'),
        ('REJECTED', 'مرفوض'),
        ('EXPIRED', 'منتهي'),
    ]
    
    # العلاقات
    field = models.ForeignKey(
        Field, 
        on_delete=models.CASCADE, 
        related_name='booking_bookings'
    )
    player = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='booking_bookings'
    )
    
    # معلومات الحجز
    booking_date = models.DateField(db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # الحالة
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='AWAITING_PAYMENT', 
        db_index=True
    )
    payment_status = models.CharField(
        max_length=20, 
        choices=PAYMENT_STATUS_CHOICES, 
        default='PENDING'
    )
    
    # الصلاحية
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # ملاحظات
    notes = models.TextField(blank=True, null=True)
    
    # التواريخ
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['booking_date', 'status']),
            models.Index(fields=['player', '-created_at']),
            models.Index(fields=['status', 'expires_at']),
        ]
        ordering = ['-created_at']
        db_table = 'booking_booking'
    
    def __str__(self):
        return f"{self.player.username} - {self.field.name} - {self.booking_date}"
    
    def get_slots(self):
        """الحصول على جميع السلوتات المرتبطة بالحجز"""
        return self.booking_slots.select_related('slot').all()
    
    def get_slots_list(self):
        """الحصول على قائمة السلوتات (للتوافق مع الكود القديم)"""
        return [bs.slot for bs in self.booking_slots.all()]
    
    def get_duration(self):
        """حساب المدة بالساعات"""
        from .utils import calculate_duration
        return calculate_duration(self.start_time, self.end_time)
    
    def is_expired(self):
        """التحقق من انتهاء صلاحية الحجز"""
        if not self.expires_at:
            return False
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    def can_cancel(self):
        """التحقق من إمكانية إلغاء الحجز"""
        if self.status in ['CANCELLED', 'REJECTED', 'EXPIRED', 'CONFIRMED']:
            return False
        from django.utils import timezone
        now = timezone.localtime()
        if self.booking_date < now.date():
            return False
        if self.booking_date == now.date() and self.start_time <= now.time():
            return False
        return True
    
    def get_status_display_ar(self):
        """الحصول على اسم الحالة بالعربية"""
        return dict(self.STATUS_CHOICES).get(self.status, self.status)
    
    def get_payment_status_display_ar(self):
        """الحصول على اسم حالة الدفع بالعربية"""
        return dict(self.PAYMENT_STATUS_CHOICES).get(self.payment_status, self.payment_status)


class BookingSlot(models.Model):
    """
    ربط الحجز بالسلوتات (مع مرونة للمستقبل)
    """
    booking = models.ForeignKey(
        Booking, 
        on_delete=models.CASCADE, 
        related_name='booking_slots'
    )
    slot = models.ForeignKey(
        VenueSlot, 
        on_delete=models.CASCADE, 
        related_name='slot_bookings'
    )
    
    # ✅ يمكن إضافة حقول مستقبلية هنا:
    # price_at_booking = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    # is_used = models.BooleanField(default=False)
    # cancelled_at = models.DateTimeField(null=True, blank=True)
    # notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['booking', 'slot']  # ✅ منع التكرار
        indexes = [
            models.Index(fields=['booking', 'slot']),
        ]
        db_table = 'booking_booking_slot'
    
    def __str__(self):
        return f"{self.booking} - {self.slot}"