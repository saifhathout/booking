from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, PlayerProfile, VenueOwnerProfile


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'role', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('email',)
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Role', {'fields': ('role',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'role'),
        }),
    )


@admin.register(PlayerProfile)
class PlayerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'city', 'phone', 'created_at')
    list_filter = ('city', 'created_at')
    search_fields = ('full_name', 'user__email', 'city')
    raw_id_fields = ('user',)


@admin.register(VenueOwnerProfile)
class VenueOwnerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'business_name', 'full_name', 'business_city', 'verified')
    list_filter = ('verified', 'business_city')
    search_fields = ('business_name', 'user__email', 'full_name')
    raw_id_fields = ('user',)