from rest_framework import serializers
from .models import Profile, GameRecord, Puzzle

from rest_framework import serializers
from .models import Profile

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["username", "email", "password", "role"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = Profile(**validated_data)
        user.set_password(password)  # 🔑 Hash the password
        user.save()
        return user


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

from rest_framework import serializers
from .models import Puzzle

class PuzzleSerializer(serializers.ModelSerializer):
    time_limit = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()  # 🔹 Add image_url field

    class Meta:
        model = Puzzle
        fields = ['puzzle_id', 'question', 'difficulty', 'points_value', 'time_limit', 'created_at', 'image_url']

    def get_time_limit(self, obj):
        limits = {'easy': 60, 'medium': 45, 'hard': 30}
        return limits.get(obj.difficulty, 45)

    def get_image_url(self, obj):
        # In this case, the `question` field stores the image URL from Banana API
        return obj.question


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
