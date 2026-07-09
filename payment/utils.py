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

# payment/utils.py

import os
import uuid
import requests
from django.conf import settings


# payment/utils.py

# payment/utils.py

import cloudinary.uploader

def upload_screenshot_to_cloudinary(file, booking_id):
    """رفع الصورة إلى Cloudinary"""
    try:
        result = cloudinary.uploader.upload(
            file,
            folder=f"bookings/{booking_id}",
            public_id=f"payment_{booking_id}",
        )
        return result.get('secure_url')
    except Exception as e:
        print(f"❌ Error uploading to Cloudinary: {e}")
        return None

def delete_screenshot_from_supabase(file_url):
    """حذف الصورة من Supabase Storage"""
    
    if not file_url:
        return False
    
    url = settings.SUPABASE_URL
    key = settings.SUPABASE_KEY or settings.SUPABASE_ANON_KEY
    bucket = settings.SUPABASE_BUCKET or 'payment_screenshots'
    
    if not url or not key:
        return False
    
    try:
        # ✅ استخراج اسم الملف من الـ URL
        file_name = file_url.split(f'/public/{bucket}/')[-1]
        
        # ✅ حذف الملف
        delete_url = f"{url}/storage/v1/object/{bucket}/{file_name}"
        headers = {
            "Authorization": f"Bearer {key}",
        }
        
        response = requests.delete(delete_url, headers=headers)
        print(f"🗑️ Delete status: {response.status_code}")
        
        return response.status_code in [200, 204]
        
    except Exception as e:
        print(f"❌ Error deleting: {e}")
        return False