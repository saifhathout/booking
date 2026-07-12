from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('booking.urls')),  # ✅ الصفحة الرئيسية من booking
    path('accounts/', include('accounts.urls')),
    path('venues/', include('venues.urls')),
    path('teams/', include('teams.urls')),
    path('tournaments/', include('tournaments.urls')),
    path('notifications/', include('notifications.urls')),
    path('payment/', include('payment.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)