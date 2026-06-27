# teams/models.py

from django.db import models
from django.conf import settings  # ✅ استخدم settings


class GameRoom(models.Model):
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('FULL', 'Full'),
        ('STARTED', 'Started'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    SPORT_CHOICES = [
        ('FOOTBALL', 'Football'),
        ('PADEL', 'Padel'),
        ('BASKETBALL', 'Basketball'),
        ('TENNIS', 'Tennis'),
    ]
    
    title = models.CharField(max_length=100)
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hosted_rooms'
    )
    sport_type = models.CharField(max_length=20, choices=SPORT_CHOICES)
    max_players = models.IntegerField(default=4)
    date = models.DateField()
    time = models.TimeField()
    city = models.CharField(max_length=100, default='Cairo', blank=True)
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} - {self.host.username}"
    
    def players_joined(self):
        return RoomPlayer.objects.filter(room=self, status='JOINED').count()
    
    def spots_left(self):
        return self.max_players - self.players_joined()
    
    def update_status(self):
        if self.status == 'CANCELLED':
            return
        if self.players_joined() >= self.max_players:
            self.status = 'FULL'
        else:
            self.status = 'OPEN'
        self.save()


class RoomPlayer(models.Model):
    STATUS_CHOICES = [
        ('JOINED', 'Joined'),
        ('LEFT', 'Left'),
    ]
    
    room = models.ForeignKey(GameRoom, on_delete=models.CASCADE, related_name='players')
    player = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='room_players'
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='JOINED')
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['room', 'player']
    
    def __str__(self):
        return f"{self.player.username} in {self.room.title}"


class RoomChat(models.Model):
    room = models.ForeignKey(GameRoom, on_delete=models.CASCADE, related_name='chats')
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='room_chats'
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.sender.username}: {self.message[:30]}"