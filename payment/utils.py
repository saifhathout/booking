# payment/utils.py

import os
import uuid
from supabase import create_client
from django.conf import settings

# ✅ إنشاء عميل Supabase
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


def upload_screenshot_to_supabase(file, booking_id):
    """رفع الصورة إلى Supabase Storage"""
    
    # ✅ إنشاء اسم فريد للملف
    file_extension = os.path.splitext(file.name)[1]
    file_name = f"booking_{booking_id}_{uuid.uuid4().hex}{file_extension}"
    file_path = f"screenshots/{file_name}"
    
    # ✅ رفع الصورة
    response = supabase.storage.from_(settings.SUPABASE_BUCKET).upload(
        file_path,
        file.read(),
        {
            "content-type": file.content_type,
        }
    )
    
    if response.status_code == 200:
        # ✅ جلب الـ URL العام
        public_url = supabase.storage.from_(settings.SUPABASE_BUCKET).get_public_url(file_path)
        return public_url
    
    return None


def delete_screenshot_from_supabase(file_url):
    """حذف الصورة من Supabase Storage"""
    
    if not file_url:
        return False
    
    # ✅ استخراج مسار الملف من الـ URL
    # مثال: https://xxx.supabase.co/storage/v1/object/public/payment_screenshots/screenshots/booking_123_abc.png
    file_path = file_url.split('/public/payment_screenshots/')[-1] if '/public/' in file_url else None
    
    if file_path:
        response = supabase.storage.from_(settings.SUPABASE_BUCKET).remove([file_path])
        return response.status_code == 200
    
    return False