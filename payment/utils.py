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


# payment/utils.py

# payment/utils.py

from PIL import Image
import io

def upload_screenshot_to_supabase(file, booking_id):
    """رفع الصورة بعد تحويلها لـ JPEG"""
    
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        # ✅ فتح الصورة بـ PIL
        img = Image.open(file)
        
        # ✅ تحويل لـ RGB (لو PNG)
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        
        # ✅ حفظ في memory
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG', quality=85)
        file_content = img_byte_arr.getvalue()
        
        # ✅ رفع الصورة
        file_name = f"booking_{booking_id}_{uuid.uuid4().hex}.jpg"
        file_path = f"screenshots/{file_name}"
        
        response = client.storage.from_('payment_screenshots').upload(
            file_path,
            file_content,
            {
                "content-type": "image/jpeg",
            }
        )
        
        public_url = client.storage.from_('payment_screenshots').get_public_url(file_path)
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