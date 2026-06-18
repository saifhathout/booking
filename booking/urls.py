from django.urls import path
from . import views

app_name = 'booking'

urlpatterns = [
    path('', views.browse_fields, name='browse'),
    path('field/<int:field_id>/', views.field_detail, name='field_detail'),
    path('book/<str:slot_id>/', views.book_slot, name='book_slot'),
    path('history/', views.booking_history, name='history'),
    path('cancel/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    
]