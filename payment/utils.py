# payment/utils.py

import os
import uuid
from supabase import create_client
from django.conf import settings


def get_supabase_client():
    """إنشاء عميل Supabase"""
    url = settings.SUPABASE_URL
    key = settings.SUPABASE_KEY or settings.SUPABASE_ANON_KEY
    
    if not url or not key:
        print("❌ Supabase credentials missing!")
        return None
    
    try:
        return create_client(url, key)
    except Exception as e:
        print(f"❌ Error creating Supabase client: {e}")
        return None


def upload_screenshot_to_supabase(file, booking_id):
    """رفع الصورة إلى Supabase Storage"""
    
    client = get_supabase_client()
    if not client:
        print("❌ No Supabase client")
        return None
    
    try:
        # ✅ قراءة الملف
        file_content = file.read()
        
        # ✅ إنشاء اسم فريد
        file_extension = os.path.splitext(file.name)[1]
        file_name = f"booking_{booking_id}_{uuid.uuid4().hex}{file_extension}"
        file_path = f"screenshots/{file_name}"
        
        # ✅ رفع الصورة
        response = client.storage.from_('payment_screenshots').upload(
            file_path,
            file_content,
            {
                "content-type": file.content_type,
            }
        )
        
        print(f"📤 Upload response: {response}")
        
        # ✅ جلب الـ URL العام
        public_url = client.storage.from_('payment_screenshots').get_public_url(file_path)
        print(f"✅ Public URL: {public_url}")
        
        return public_url
        
    except Exception as e:
        print(f"❌ Error uploading: {e}")
        return None


def delete_screenshot_from_supabase(file_url):
    """حذف الصورة من Supabase Storage"""
    
    if not file_url:
        return False
    
    client = get_supabase_client()
    if not client:
        return False
    
    try:
        # ✅ استخراج مسار الملف من الـ URL
        if '/public/' in file_url:
            file_path = file_url.split('/public/payment_screenshots/')[-1]
        else:
            file_path = file_url
        
        response = client.storage.from_('payment_screenshots').remove([file_path])
        print(f"🗑️ Delete response: {response}")
        return True
        
    except Exception as e:
        print(f"❌ Error deleting screenshot: {e}")
        return False