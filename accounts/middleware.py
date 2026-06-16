from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings

class RoleBasedRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            # Prevent cross-role access
            current_path = request.path
            
            # Define role-specific URL patterns
            player_urls = ['/booking/', '/teams/', '/tournaments/', '/dashboard/player/']
            owner_urls = ['/venues/', '/dashboard/owner/']
            
            if request.user.is_player:
                # Check if trying to access owner URLs
                if any(current_path.startswith(url) for url in owner_urls):
                    return redirect('dashboard:player_dashboard')
            
            elif request.user.is_venue_owner:
                # Check if trying to access player URLs
                if any(current_path.startswith(url) for url in player_urls):
                    return redirect('dashboard:owner_dashboard')
        
        response = self.get_response(request)
        return response