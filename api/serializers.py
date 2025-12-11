from rest_framework import serializers
from .models import Profile, GameRecord, Puzzle

from rest_framework import serializers
from .models import Profile

from rest_framework import serializers
from .models import Profile, GameRecord

# ✅ Your existing GameRecordSerializer
from rest_framework import serializers
from .models import Profile, GameRecord

from rest_framework import serializers
from .models import Profile

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = Profile
        fields = ['username', 'email', 'password']

    def create(self, validated_data):
        user = Profile(
            username=validated_data['username'],
            email=validated_data['email'],
            role='player'  # default role
        )
        user.set_password(validated_data['password'])  # 🔐 hash password
        user.save()
        return user


class GameRecordSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(source='attempted_at')

    class Meta:
        model = GameRecord
        fields = [
            'puzzle_id',
            'player_answer',
            'is_correct',
            'points_earned',
            'time_taken',
            'created_at'  # Map attempted_at to created_at for API consistency
        ]

class ProfileSerializer(serializers.ModelSerializer):
    # computed fields
    accuracy = serializers.SerializerMethodField()
    games_played = serializers.SerializerMethodField()
    recent_games = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ["id", "username", "email", "role", "score", "coins", "games_played", "accuracy", "recent_games"]

    def get_accuracy(self, obj):
        if obj.total_games_played > 0:
            return round((obj.total_correct_answers / obj.total_games_played) * 100, 1)
        return 0.0

    def get_games_played(self, obj):
        return obj.total_games_played

    def get_recent_games(self, obj):
        # Order by attempted_at descending (latest games first) - ensures newest are on top
        last_games = obj.game_records.order_by('-attempted_at')[:10]
        # Double-check ordering by sorting again in Python
        sorted_games = sorted(last_games, key=lambda x: x.attempted_at, reverse=True)[:10]
        return GameRecordSerializer(sorted_games, many=True).data


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
