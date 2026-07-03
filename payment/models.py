# payment/models.py

from django.db import models
from django.conf import settings
from venues.models import Booking


class InstaPayPayment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'قيد المراجعة'),
        ('approved', 'تم التأكيد'),
        ('rejected', 'مرفوض'),
        ('manual_review', 'مراجعة يدوية'),
    )

    booking = models.ForeignKey(
        Booking, 
        on_delete=models.CASCADE, 
        related_name='payments'
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE
    )

    # بيانات الدفع
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    reference_number = models.CharField(max_length=50, blank=True, null=True, unique=True)
    sender_phone = models.CharField(max_length=20, blank=True, null=True)
    note_code = models.CharField(max_length=10, blank=True, null=True)

    screenshot = models.ImageField(
        upload_to='payments/screenshots/%Y/%m/%d/', 
        null=True, 
        blank=True
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    confidence_score = models.FloatField(default=0.0)
    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"InstaPay #{self.id} - {self.status} - {self.amount} EGP"

    class Meta:
        verbose_name = "InstaPay Payment"
        verbose_name_plural = "InstaPay Payments"
        ordering = ['-created_at']