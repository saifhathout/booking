from django.shortcuts import render 
from django.contrib.auth.decorators import login_required 
 
@login_required 
def team_list(request): 
    return render(request, 'teams/team_list.html') 
 
@login_required 
def find_teams(request): 
    return render(request, 'teams/find_teams.html') 
