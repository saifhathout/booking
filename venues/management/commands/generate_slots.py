# venues/management/commands/generate_slots.py

from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import date, timedelta

from venues.models import Field, VenueSlot

DAYS_AHEAD = 30  # عدد الأيام القادمة لتوليد السلوتات


class Command(BaseCommand):
    help = (
        "يولّد VenueSlot لكل ساعة (0-23) لكل يوم لمدة DAYS_AHEAD يوم قدام، "
        "لكل الملاعب النشطة. آمن للتشغيل بشكل متكرر (بيستخدم get_or_create)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--field-id',
            type=int,
            default=None,
            help='ولّد السلوتات لملعب معين بس (اختياري)',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=DAYS_AHEAD,
            help=f'عدد الأيام قدام (افتراضي {DAYS_AHEAD})',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='ولّد السلوتات لكل الملاعب (حتى غير النشطة)',
        )

    def handle(self, *args, **options):
        # ✅ اختيار الملاعب
        if options['all']:
            fields = Field.objects.all()
        else:
            fields = Field.objects.filter(is_active=True)
        
        if options['field_id']:
            fields = fields.filter(id=options['field_id'])

        days = options['days']
        today = date.today()

        if not fields.exists():
            self.stdout.write(self.style.WARNING(
                "⚠️ لا توجد ملاعب لتوليد سلوتات لها!"
            ))
            return

        total_created = 0
        total_skipped = 0

        self.stdout.write(f"\n🚀 Generating slots for {fields.count()} field(s)...")
        self.stdout.write(f"📅 Days ahead: {days}")
        self.stdout.write("-" * 50)

        for field in fields:
            created, skipped = self._generate_for_field(field, today, days)
            total_created += created
            total_skipped += skipped
            self.stdout.write(f"  ✅ {field.name}: {created} جديد, {skipped} موجود")

        self.stdout.write("-" * 50)
        self.stdout.write(self.style.SUCCESS(
            f"✅ تم توليد {total_created} سلوت جديد لـ {fields.count()} ملعب."
        ))
        if total_skipped > 0:
            self.stdout.write(self.style.WARNING(
                f"⚠️ {total_skipped} سلوت كانت موجودة بالفعل (تم تخطيها)"
            ))

    def _generate_for_field(self, field, start_date, days):
        created_count = 0
        skipped_count = 0
        
        with transaction.atomic():
            for day_offset in range(days):
                target_date = start_date + timedelta(days=day_offset)
                for hour in range(24):
                    start_time_str = f"{hour:02d}:00:00"
                    end_hour = (hour + 1) % 24
                    end_time_str = f"{end_hour:02d}:00:00"

                    slot, created = VenueSlot.objects.get_or_create(
                        field=field,
                        date=target_date,
                        start_time=start_time_str,
                        defaults={
                            'end_time': end_time_str,
                            'is_available': True,
                            'slot_type': 'OPEN',  # ✅ تأكد من وجود هذا الحقل
                        }
                    )
                    if created:
                        created_count += 1
                    else:
                        skipped_count += 1
        return created_count, skipped_count