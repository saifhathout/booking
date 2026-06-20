from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator


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
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.city}"


class Field(models.Model):
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='fields')
    name = models.CharField(max_length=200)
    sport_type = models.CharField(max_length=20, choices=Venue.SPORT_CHOICES)
    description = models.TextField(blank=True)
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)
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
        ('BLOCKED', 'Blocked by Owner'),
        ('BOOKED', 'Booked by Player'),
    ]
    
    field = models.ForeignKey(Field, on_delete=models.CASCADE, related_name='slots')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    slot_type = models.CharField(max_length=20, choices=SLOT_TYPE_CHOICES, default='BLOCKED')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['field', 'date', 'is_available']),
            models.Index(fields=['date', 'is_available']),
        ]
        ordering = ['date', 'start_time']
    
    def __str__(self):
        return f"{self.field.name} - {self.date} {self.start_time}"


class Booking(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    field = models.ForeignKey(Field, on_delete=models.CASCADE, related_name='bookings')
    player = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    slot = models.ForeignKey(VenueSlot, on_delete=models.CASCADE, related_name='bookings')
    booking_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='CONFIRMED')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['booking_date', 'status']),
            models.Index(fields=['player', '-created_at']),
            models.Index(fields=['field', 'booking_date']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.player.email} - {self.field.name} - {self.booking_date}"