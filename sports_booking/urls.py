from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('accounts/', include('accounts.urls')),
    path('venues/', include('venues.urls')),
    path('booking/', include('booking.urls')),
    path('teams/', include('teams.urls')),
    path('tournaments/', include('tournaments.urls')),
    path('notifications/', include('notifications.urls')),
    # ✅ Service Worker on root
    path('sw.js', TemplateView.as_view(
        template_name='sw.js',
        content_type='application/javascript'
    )),
    path('manifest.json', TemplateView.as_view(
        template_name='manifest.json',
        content_type='application/json'
    )),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)