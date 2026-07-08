from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from .models import PlayerProfile, VenueOwnerProfile

User = get_user_model()


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    if request.method == 'POST':
        login_input = request.POST.get('username')
        password = request.POST.get('password')

        print("LOGIN INPUT:", login_input)

        from accounts.models import User
        user = None

        try:
            if '@' in login_input:
                user_obj = User.objects.get(email=login_input)
            else:
                user_obj = User.objects.get(username=login_input)

            print("FOUND USER:", user_obj.email)
            print("CHECK PASSWORD:", user_obj.check_password(password))

            user = authenticate(
                request,
                username=user_obj.email,
                password=password
            )

            print("AUTH RESULT:", user)

        except Exception as e:
            print("ERROR:", e)

        if user is not None:
            login(request, user)
            return redirect('dashboard:home')

        messages.error(request, "Invalid username/email or password.")

    return render(request, "accounts/login.html")

def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully.')
    return redirect('dashboard:home')


def register_player(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')
        full_name = request.POST.get('full_name', '')  # ✅ أو خليها اختيارية
        phone = request.POST.get('phone')
        city = request.POST.get('city')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken.')
        else:
            user = User.objects.create_user(
                email=email, 
                username=username,
                password=password, 
                role='PLAYER'
            )
            PlayerProfile.objects.create(
                user=user,
                full_name=full_name,
                phone=phone,
                city=city
            )
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('dashboard:player_dashboard')
    
    return render(request, 'accounts/register_player.html')

def register_venue_owner(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')
        full_name = request.POST.get('full_name')
        phone = request.POST.get('phone')
        business_name = request.POST.get('business_name')
        business_address = request.POST.get('business_address')
        business_city = request.POST.get('business_city')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken.')
        else:
            user = User.objects.create_user(
                email=email,
                username=username,
                password=password,
                role='VENUE_OWNER'
            )
            VenueOwnerProfile.objects.create(
                user=user,
                full_name=full_name,
                phone=phone,
                business_name=business_name,
                business_address=business_address,
                business_city=business_city
            )
            login(request, user)
            messages.success(request, 'Venue owner account created successfully!')
            return redirect('dashboard:owner_dashboard')
    
    return render(request, 'accounts/register_venue_owner.html')



@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html')