from django.urls import path 
from . import views 
app_name = 'tournaments' 
urlpatterns = [ 
    path('', views.tournament_list, name='list'), 
    path('<int:tournament_id>/', views.tournament_detail, name='detail'), 
] 
