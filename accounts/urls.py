from django.urls import path 
from . import views 
app_name = 'accounts' 
urlpatterns = [ 
    path('login/', views.login_view, name='login'), 
    path('logout/', views.logout_view, name='logout'),
     
    path('register/player/', views.register_player, name='register_player'), 
    path('register/venue-owner/', views.register_venue_owner, name='register_venue_owner'), 
    path('profile/', views.profile_view, name='profile'), 
] 
