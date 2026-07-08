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
        return None
    
    try:
        file_extension = os.path.splitext(file.name)[1]
        file_name = f"booking_{booking_id}_{uuid.uuid4().hex}{file_extension}"
        file_path = f"screenshots/{file_name}"
        
        response = client.storage.from_('payment_screenshots').upload(
            file_path,
            file.read(),
            {
                "content-type": file.content_type,
            }
        )
        
        if response and hasattr(response, 'status_code') and response.status_code == 200:
            public_url = client.storage.from_('payment_screenshots').get_public_url(file_path)
            return public_url
        
        print(f"❌ Upload failed: {response}")
        return None
        
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
        if '/public/' in file_url:
            file_path = file_url.split('/public/payment_screenshots/')[-1]
        else:
            return False
        
        response = client.storage.from_('payment_screenshots').remove([file_path])
        return True
        
    except Exception as e:
        print(f"❌ Error deleting screenshot: {e}")
        return False