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
        login_input = request.POST.get('username')  # username or email
        password = request.POST.get('password')

        from accounts.models import User
        user = None

        if '@' in login_input:
            try:
                user_obj = User.objects.get(email=login_input)
                user = authenticate(request, username=user_obj.email, password=password)
            except User.DoesNotExist:
                pass
        else:
            try:
                user_obj = User.objects.get(username=login_input)
                user = authenticate(request, username=user_obj.email, password=password)
            except User.DoesNotExist:
                pass

        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username or user.email}!')
            return redirect('dashboard:home')
        else:
            messages.error(request, 'Invalid username/email or password.')

    return render(request, 'accounts/login.html')


def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully.')
    return redirect('dashboard:home')


def register_player(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        username = request.POST.get('username', '').strip()

        # ✅ الفورم الحالية بتبعت password1/password2 (تأكيد كلمة السر)
        # مش password لوحدها - لازم نقرا الاسم الصح
        password = request.POST.get('password1') or request.POST.get('password')
        password_confirm = request.POST.get('password2')

        # ✅ حقول اختيارية دلوقتي - لو الفورم مفيهاش الحقول دي، نملاها تلقائيًا
        full_name = request.POST.get('full_name', '').strip() or username
        phone = request.POST.get('phone', '').strip() or 'N/A'
        city = request.POST.get('city', '').strip() or 'N/A'

        # --- Validation ---
        if not email or not username or not password:
            messages.error(request, 'يرجى ملء جميع الحقول المطلوبة.')
            return render(request, 'accounts/register_player.html')

        if password_confirm is not None and password != password_confirm:
            messages.error(request, 'كلمتا المرور غير متطابقتين.')
            return render(request, 'accounts/register_player.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return render(request, 'accounts/register_player.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken.')
            return render(request, 'accounts/register_player.html')

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
        email = request.POST.get('email', '').strip()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password1') or request.POST.get('password')
        password_confirm = request.POST.get('password2')

        full_name = request.POST.get('full_name', '').strip() or username
        phone = request.POST.get('phone', '').strip() or 'N/A'
        business_name = request.POST.get('business_name', '').strip() or f"{username}'s Venue"
        business_address = request.POST.get('business_address', '').strip() or 'N/A'
        business_city = request.POST.get('business_city', '').strip() or 'N/A'

        if not email or not username or not password:
            messages.error(request, 'يرجى ملء جميع الحقول المطلوبة.')
            return render(request, 'accounts/register_venue_owner.html')

        if password_confirm is not None and password != password_confirm:
            messages.error(request, 'كلمتا المرور غير متطابقتين.')
            return render(request, 'accounts/register_venue_owner.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return render(request, 'accounts/register_venue_owner.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken.')
            return render(request, 'accounts/register_venue_owner.html')

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