from django.db import models
from django.conf import settings


class Team(models.Model):
    SPORT_CHOICES = [
        ('FOOTBALL', 'Football'),
        ('CRICKET', 'Cricket'),
        ('BASKETBALL', 'Basketball'),
        ('TENNIS', 'Tennis'),
        ('PADEL', 'Padel'),
        ('BADMINTON', 'Badminton'),
        ('VOLLEYBALL', 'Volleyball'),
    ]
    
    name = models.CharField(max_length=200)
    captain = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='captained_teams')
    sport_type = models.CharField(max_length=20, choices=SPORT_CHOICES)
    city = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    looking_players = models.BooleanField(default=True)
    max_players = models.IntegerField(default=11)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name


class TeamMember(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='members')
    player = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, default='PLAYER')
    status = models.CharField(max_length=20, default='APPROVED')
    joined_at = models.DateTimeField(auto_now_add=True)


class PlayerPost(models.Model):
    SPORT_CHOICES = [
        ('FOOTBALL', 'Football'),
        ('PADEL', 'Padel'),
        ('TENNIS', 'Tennis'),
        ('BASKETBALL', 'Basketball'),
        ('CRICKET', 'Cricket'),
        ('BADMINTON', 'Badminton'),
        ('VOLLEYBALL', 'Volleyball'),
    ]
    
    player = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts')
    sport_type = models.CharField(max_length=20, choices=SPORT_CHOICES)
    players_needed = models.IntegerField(default=1)
    city = models.CharField(max_length=100)
    date = models.DateField()
    time = models.TimeField(null=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.player.email} - {self.sport_type}"


class PlayerRequest(models.Model):
    post = models.ForeignKey(PlayerPost, on_delete=models.CASCADE, related_name='requests')
    player = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, default='ACCEPTED')
    created_at = models.DateTimeField(auto_now_add=True)


class ChatMessage(models.Model):
    post = models.ForeignKey(PlayerPost, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)