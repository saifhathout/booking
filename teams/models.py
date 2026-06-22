from django.db import models
from django.conf import settings


class GameRoom(models.Model):
    SPORT_CHOICES = [
        ('FOOTBALL VOLTA', 'Football volta'),
        ('PADEL', 'Padel'),
        ('Padoal', 'Padoal'),
    ]
    
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hosted_rooms')
    sport_type = models.CharField(max_length=20, choices=SPORT_CHOICES)
    title = models.CharField(max_length=200)
    max_players = models.IntegerField(default=4)
    date = models.DateField()
    time = models.TimeField(null=True, blank=True)
    city = models.CharField(max_length=100, default='Cairo')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def players_joined(self):
        return self.players.filter(status='JOINED').count()
    
    def spots_left(self):
        return self.max_players - self.players_joined()
    
    def __str__(self):
        return f"{self.host.username}'s Room - {self.sport_type}"


class RoomPlayer(models.Model):
    STATUS_CHOICES = [
        ('JOINED', 'Joined'),
        ('LEFT', 'Left'),
    ]
    
    room = models.ForeignKey(GameRoom, on_delete=models.CASCADE, related_name='players')
    player = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='JOINED')
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['room', 'player']
    
    def __str__(self):
        return f"{self.player.username} in {self.room.title}"


class RoomChat(models.Model):
    room = models.ForeignKey(GameRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']