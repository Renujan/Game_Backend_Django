from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.cache import cache
import uuid

class Profile(AbstractUser):
    ROLE_CHOICES = [
        ('player', 'Player'),
        ('admin', 'Admin'),
    ]

    score = models.IntegerField(default=0)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='player')
    total_games_played = models.IntegerField(default=0)
    total_correct_answers = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username

class GameRecord(models.Model):
    player = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='game_records')
    puzzle_id = models.CharField(max_length=100)
    player_answer = models.CharField(max_length=500)
    is_correct = models.BooleanField()
    points_earned = models.IntegerField(default=0)
    time_taken = models.IntegerField(default=0)  # in seconds
    attempted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.player.username} - {self.puzzle_id} - {'Correct' if self.is_correct else 'Incorrect'}"

class Puzzle(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]

    puzzle_id = models.CharField(max_length=100, unique=True)
    question = models.TextField()
    solution = models.CharField(max_length=500)  # Store hashed or encrypted
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='medium')
    points_value = models.IntegerField(default=20)
    time_limit = models.IntegerField(default=45)  # in seconds
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Store solution securely in cache instead of DB
        if self.solution:
            cache_key = f"puzzle_solution_{self.puzzle_id}"
            cache.set(cache_key, self.solution, timeout=None)  # Permanent cache
            self.solution = ''  # Don't store in DB
        super().save(*args, **kwargs)

    def get_solution(self):
        cache_key = f"puzzle_solution_{self.puzzle_id}"
        return cache.get(cache_key)

    def __str__(self):
        return f"Puzzle {self.puzzle_id} ({self.difficulty})"
