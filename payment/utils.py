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

def upload_screenshot_to_supabase(file, booking_id):
    """رفع الصورة إلى Supabase Storage باستخدام requests"""
    
    # ✅ بيانات Supabase
    url = settings.SUPABASE_URL
    key = settings.SUPABASE_KEY or settings.SUPABASE_ANON_KEY
    bucket = settings.SUPABASE_BUCKET or 'payment_screenshots'
    
    print(f"🔍 SUPABASE_URL: {url}")
    print(f"🔍 SUPABASE_KEY: {key[:20] if key else 'None'}...")
    print(f"🔍 SUPABASE_BUCKET: {bucket}")
    
    if not url or not key:
        print("❌ Supabase credentials missing!")
        return None
    
    try:
        # ✅ قراءة الملف
        file_content = file.read()
        
        print(f"📸 File read: {len(file_content)} bytes")
        
        # ✅ إنشاء اسم فريد
        import uuid
        file_extension = os.path.splitext(file.name)[1]
        file_name = f"booking_{booking_id}_{uuid.uuid4().hex}{file_extension}"
        file_path = f"{file_name}"
        
        # ✅ رفع الصورة
        upload_url = f"{url}/storage/v1/object/{bucket}/{file_path}"
        
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": file.content_type,
        }
        
        print(f"📤 Upload URL: {upload_url}")
        print(f"📤 Headers: {headers}")
        
        response = requests.post(
            upload_url,
            data=file_content,
            headers=headers,
        )
        
        print(f"📤 Response Status: {response.status_code}")
        print(f"📤 Response Text: {response.text}")
        
        if response.status_code in [200, 201]:
            # ✅ جلب الـ URL العام
            public_url = f"{url}/storage/v1/object/public/{bucket}/{file_path}"
            print(f"✅ Public URL: {public_url}")
            return public_url
        else:
            print(f"❌ Upload failed: {response.status_code} - {response.text}")
            return None
        
    except Exception as e:
        print(f"❌ Error uploading: {e}")
        import traceback
        traceback.print_exc()
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