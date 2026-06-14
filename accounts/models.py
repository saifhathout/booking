from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'ADMIN')
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('PLAYER', 'Player'),
        ('VENUE_OWNER', 'Venue Owner'),
        ('ADMIN', 'Admin'),
    ]
    
    email = models.EmailField(unique=True, db_index=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='PLAYER')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta:
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
        ]
    
    def __str__(self):
        return self.email
    
    @property
    def is_player(self):
        return self.role == 'PLAYER'
    
    @property
    def is_venue_owner(self):
        return self.role == 'VENUE_OWNER'
    
    def get_dashboard_url(self):
        if self.role == 'PLAYER':
            return 'dashboard:player_dashboard'
        elif self.role == 'VENUE_OWNER':
            return 'dashboard:owner_dashboard'
        return 'admin:index'


class PlayerProfile(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='player_profile'
    )
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=15)
    city = models.CharField(max_length=100, db_index=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['city']),
        ]
    
    def __str__(self):
        return self.full_name


class VenueOwnerProfile(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='venue_owner_profile'
    )
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=15)
    business_name = models.CharField(max_length=200)
    business_address = models.TextField()
    business_city = models.CharField(max_length=100, db_index=True)
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['business_city']),
        ]
    
    def __str__(self):
        return f"{self.business_name} - {self.full_name}"