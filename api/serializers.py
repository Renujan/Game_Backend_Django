from rest_framework import serializers
from .models import Profile, GameRecord, Puzzle

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['id', 'username', 'email', 'password', 'score', 'role', 'total_games_played', 'total_correct_answers', 'created_at', 'date_joined']
        extra_kwargs = {
            'password': {'write_only': True},
            'score': {'read_only': True},
            'total_games_played': {'read_only': True},
            'total_correct_answers': {'read_only': True},
            'created_at': {'read_only': True},
            'date_joined': {'read_only': True},
        }

class GameRecordSerializer(serializers.ModelSerializer):
    player_username = serializers.CharField(source='player.username', read_only=True)

    class Meta:
        model = GameRecord
        fields = ['id', 'player', 'player_username', 'puzzle_id', 'player_answer', 'is_correct', 'points_earned', 'time_taken', 'attempted_at']
        extra_kwargs = {
            'player': {'read_only': True},
            'is_correct': {'read_only': True},
            'points_earned': {'read_only': True},
            'attempted_at': {'read_only': True},
        }

class PuzzleSerializer(serializers.ModelSerializer):
    time_limit = serializers.SerializerMethodField()

    class Meta:
        model = Puzzle
        fields = ['puzzle_id', 'question', 'difficulty', 'points_value', 'time_limit', 'created_at']
        extra_kwargs = {
            'puzzle_id': {'read_only': True},
            'created_at': {'read_only': True},
        }

    def get_time_limit(self, obj):
        # Return time limit based on difficulty
        limits = {'easy': 60, 'medium': 45, 'hard': 30}
        return limits.get(obj.difficulty, 45)

class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['email', 'first_name', 'last_name']
        extra_kwargs = {
            'email': {'required': False},
            'first_name': {'required': False},
            'last_name': {'required': False},
        }

class LeaderboardSerializer(serializers.Serializer):
    username = serializers.CharField()
    score = serializers.IntegerField()
    total_games_played = serializers.IntegerField()
    total_correct_answers = serializers.IntegerField()
    accuracy = serializers.FloatField()

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
