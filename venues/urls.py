# venues/urls.py

from django.urls import path
from . import views

app_name = 'venues'

urlpatterns = [
    # ✅ الروابط 
        path('', views.venue_list, name='list'),  # ✅ أضف هذا

    path('', views.venue_list, name='venue_list'),  # ✅ بدلاً من 'list'
    path('create/', views.venue_create, name='venue_create'),  # ✅ بدلاً من 'create'
    path('<int:venue_id>/', views.venue_detail, name='venue_detail'),
    path('<int:venue_id>/field/create/', views.field_create, name='field_create'),
    path('field/<int:field_id>/schedule/', views.field_schedule_view, name='field_schedule'),
    path('field/<int:field_id>/edit/', views.field_edit, name='field_edit'),
    path('bookings/', views.booking_requests, name='booking_requests'),
    path('booking/<int:booking_id>/', views.booking_details, name='booking_details'),
    path('dashboard/', views.owner_dashboard, name='owner_dashboard'),
    
    # ✅ Block/Unblock
    path('field/<int:field_id>/block/<str:date>/<int:hour>/', views.block_slot, name='block_slot'),
    path('field/<int:field_id>/unblock/<str:date>/<int:hour>/', views.unblock_slot, name='unblock_slot'),
]