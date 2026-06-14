from django.urls import path 
from . import views 
app_name = 'teams' 
urlpatterns = [ 
    path('', views.team_list, name='list'), 
    path('find/', views.find_teams, name='find'), 
] 
