from django.shortcuts import render 
from django.contrib.auth.decorators import login_required 
 
@login_required 
def tournament_list(request): 
    return render(request, 'tournaments/tournament_list.html') 
 
@login_required 
def tournament_detail(request, tournament_id): 
    return render(request, 'tournaments/tournament_detail.html') 
