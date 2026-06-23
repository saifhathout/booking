# payment/urls.py

from django.urls import path
from . import views

app_name = 'payment'

urlpatterns = [
    path('initiate/<int:booking_id>/', views.initiate_instapay_payment, name='initiate_instapay'),
    path('upload/<int:payment_id>/', views.upload_screenshot, name='upload_screenshot'),
    path('pending/<int:payment_id>/', views.payment_pending, name='payment_pending'),  # ✅ أضفناها
    path('verify/<int:payment_id>/', views.verify_payment, name='verify_payment'),
]