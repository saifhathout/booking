from django.contrib import admin
from .models import Venue, Field, VenueSlot, Booking

@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'city', 'sport_type')

@admin.register(Field)
class FieldAdmin(admin.ModelAdmin):
    list_display = ('name', 'venue', 'sport_type', 'price_per_hour', 'is_active')

@admin.register(VenueSlot)
class VenueSlotAdmin(admin.ModelAdmin):
    list_display = ('field', 'date', 'start_time', 'end_time', 'is_available')

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('field', 'player', 'booking_date', 'start_time', 'status')