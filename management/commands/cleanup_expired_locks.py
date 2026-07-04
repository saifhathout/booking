# management/commands/cleanup_expired_locks.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from venues.models import Booking

class Command(BaseCommand):
    help = 'تحرير السلوتات المقفلة التي انتهت صلاحيتها'

    def handle(self, *args, **options):
        # ✅ الحجوزات المقفلة التي انتهت صلاحيتها
        expired_bookings = Booking.objects.filter(
            status='LOCKED',
            locked_until__lt=timezone.now()
        )
        
        count = expired_bookings.count()
        
        with transaction.atomic():
            for booking in expired_bookings:
                # ✅ تحرير السلوتات
                booking.release_slots()
                booking.status = 'EXPIRED'
                booking.save()
                self.stdout.write(f'✅ Released locks for booking #{booking.id}')
        
        self.stdout.write(f'✅ تم تحرير {count} حجز منتهي الصلاحية')