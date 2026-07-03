# venues/models.py

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from datetime import datetime, timedelta


class Venue(models.Model):
    SPORT_CHOICES = [
        ('FOOTBALL', 'Football'),
        ('CRICKET', 'Cricket'),
        ('BASKETBALL', 'Basketball'),
        ('TENNIS', 'Tennis'),
        ('PADEL', 'Padel'),
        ('BADMINTON', 'Badminton'),
        ('VOLLEYBALL', 'Volleyball'),
        ('MULTI', 'Multi-Sport'),
    ]
    
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='venues')
    name = models.CharField(max_length=200)
    address = models.TextField()
    city = models.CharField(max_length=100)
    sport_type = models.CharField(max_length=20, choices=SPORT_CHOICES)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='venue_logos/', null=True, blank=True)
    brand_color = models.CharField(max_length=7, default='#0066FF')
    brand_name = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def get_brand_name(self):
        return self.brand_name or self.name
    
    def __str__(self):
        return f"{self.name} - {self.city}"


class Field(models.Model):
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='fields')
    name = models.CharField(max_length=200)
    sport_type = models.CharField(max_length=20, choices=Venue.SPORT_CHOICES)
    description = models.TextField(blank=True)
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to='field_images/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['venue', 'is_active']),
            models.Index(fields=['sport_type']),
        ]
    
    def __str__(self):
        return f"{self.venue.name} - {self.name}"


class VenueSlot(models.Model):
    SLOT_TYPE_CHOICES = [
        ('AVAILABLE', 'Available'),
        ('LOCKED', 'Locked - Pending Payment'),
        ('BLOCKED', 'Blocked by Owner'),
        ('BOOKED', 'Booked by Player'),
    ]
    
    field = models.ForeignKey(Field, on_delete=models.CASCADE, related_name='slots')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    slot_type = models.CharField(max_length=20, choices=SLOT_TYPE_CHOICES, default='AVAILABLE')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['field', 'date', 'is_available']),
        ]
        ordering = ['date', 'start_time']
        constraints = [
            models.UniqueConstraint(
                fields=['field', 'date', 'start_time'],
                name='unique_field_slot'
            )
        ]
    
    def __str__(self):
        return f"{self.field.name} - {self.date} {self.start_time}"


class Booking(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('LOCKED', 'Locked - Awaiting Payment'),
        ('CONFIRMED', 'Confirmed'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
        ('EXPIRED', 'Expired'),
    ]
    
    field = models.ForeignKey(Field, on_delete=models.CASCADE, related_name='bookings')
    player = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    
    # ✅ مصدر الحقيقة - جميع السلوتات
    slots = models.ManyToManyField(
        VenueSlot,
        related_name='bookings',
        blank=True
    )
    
    # ✅ للعرض فقط (Display)
    booking_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    locked_until = models.DateTimeField(null=True, blank=True)
    
    payment_screenshot = models.ImageField(upload_to='payments/', null=True, blank=True)
    payment_status = models.CharField(max_length=20, default='PENDING')
    notes = models.TextField(blank=True, null=True)
    
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['booking_date', 'status']),
            models.Index(fields=['player', '-created_at']),
            models.Index(fields=['locked_until']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.player.username} - {self.field.name} - {self.booking_date}"
    
    # ✅ ========== دوال تعتمد على Slots كمصدر الحقيقة ==========
    
    def get_slots_count(self):
        """عدد السلوتات = مدة الحجز بالساعات"""
        return self.slots.count()
    
    def get_first_slot(self):
        """أول سلوت في الحجز"""
        return self.slots.order_by('date', 'start_time').first()
    
    def get_last_slot(self):
        """آخر سلوت في الحجز"""
        return self.slots.order_by('date', 'start_time').last()
    
    def get_duration_hours(self):
        """مدة الحجز بالساعات"""
        return self.slots.count()
    
    def get_total_price(self):
        """السعر الإجمالي"""
        return self.slots.count() * self.field.price_per_hour
    
    def is_locked_expired(self):
        """هل انتهت صلاحية القفل؟"""
        if not self.locked_until:
            return True
        return timezone.now() > self.locked_until
    
    def lock_slots(self, duration_minutes=15):
        """قفل السلوتات لمدة محددة"""
        self.status = 'LOCKED'
        self.locked_until = timezone.now() + timedelta(minutes=duration_minutes)
        self.save()
    
    def release_slots(self):
        """تحرير السلوتات (إلغاء القفل)"""
        for slot in self.slots.all():
            slot.is_available = True
            slot.slot_type = 'AVAILABLE'
            slot.save()
        self.slots.clear()
        self.status = 'CANCELLED'
        self.locked_until = None
        self.save()
    
    def confirm_booking(self):
        """تأكيد الحجز (تحويل LOCKED → BOOKED)"""
        for slot in self.slots.all():
            slot.is_available = False
            slot.slot_type = 'BOOKED'
            slot.save()
        self.status = 'CONFIRMED'
        self.locked_until = None
        self.save()
    
    def update_display_fields(self):
        """تحديث حقول العرض من السلوتات"""
        if self.slots.exists():
            first = self.get_first_slot()
            last = self.get_last_slot()
            
            self.booking_date = first.date
            self.start_time = first.start_time
            self.end_date = last.date
            self.end_time = last.end_time
            self.total_price = self.get_total_price()
            self.save()