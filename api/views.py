from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.db.models import Q, F, Count, Case, When, IntegerField
from django.utils import timezone
from datetime import timedelta
import random
import requests
from .models import Profile, GameRecord, Puzzle
from .serializers import ProfileSerializer, GameRecordSerializer, PuzzleSerializer, LeaderboardSerializer, LoginSerializer, ProfileUpdateSerializer
from .permissions import IsAdmin

from rest_framework import generics
from .serializers import RegisterSerializer
from .models import Profile
from rest_framework import generics, status
from rest_framework.response import Response
from .models import Profile
from .serializers import RegisterSerializer, ProfileSerializer

class RegisterView(generics.CreateAPIView):
    queryset = Profile.objects.all()
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # return user profile data after register
        profile_data = ProfileSerializer(user).data
        return Response(profile_data, status=status.HTTP_201_CREATED)




from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

@api_view(['POST'])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(username=username, password=password)
    if user:
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'score': user.score,
                'role': user.role
            }
        })
    return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def profile_view(request):
    serializer = ProfileSerializer(request.user)
    return Response(serializer.data)

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import permissions, status
from django.core.cache import cache
from django.db.models import F
import requests, random
from .models import Puzzle, GameRecord
from .serializers import PuzzleSerializer, GameRecordSerializer

# ---------------------------
# GET PUZZLE (image-based)
# ---------------------------
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import permissions, status
from .models import Puzzle
from .serializers import PuzzleSerializer
import random
import requests

import random
import requests
from django.core.cache import cache
from django.db.models import F
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import Puzzle, GameRecord, Profile
from .serializers import PuzzleSerializer, GameRecordSerializer

# Difficulty settings
DIFFICULTY_TIME = {'easy': 60, 'medium': 45, 'hard': 30}
POINTS_MAP = {'easy': 10, 'medium': 20, 'hard': 30}

BANANA_API_URL = "https://marcconrad.com/uob/banana/api.php"

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_puzzle(request):
    """
    Fetch a puzzle for the user.
    1. Call Banana API
    2. Store solution in cache
    3. Return image URL to frontend
    """
    try:
        response = requests.get(BANANA_API_URL, timeout=5)
        if response.status_code != 200:
            raise Exception("Banana API error")
        data = response.json()

        puzzle_id = f"banana_{random.randint(1000,9999)}"
        question = data.get("question")  # This is the image URL
        solution = str(data.get("solution"))
        difficulty = random.choice(['easy', 'medium', 'hard'])
        points_value = POINTS_MAP[difficulty]
        time_limit = DIFFICULTY_TIME[difficulty]

        # Store solution in cache
        cache_key = f"puzzle_solution_{puzzle_id}"
        cache.set(cache_key, solution, timeout=None)  # Permanent cache

        # Save puzzle in DB without solution
        puzzle = Puzzle.objects.create(
            puzzle_id=puzzle_id,
            question=question,  # store image URL in question field
            solution='',        # solution is only in cache
            difficulty=difficulty,
            points_value=points_value,
            time_limit=time_limit
        )

        serializer = PuzzleSerializer(puzzle)
        # Add image_url field to send to frontend
        data_to_send = serializer.data
        data_to_send['image_url'] = question
        return Response(data_to_send)
    except Exception as e:
        # Fallback sample puzzle
        puzzle_id = f"sample_{random.randint(1000,9999)}"
        question = "https://via.placeholder.com/400?text=Sample+Puzzle"
        solution = "4"
        difficulty = "easy"
        points_value = POINTS_MAP[difficulty]
        time_limit = DIFFICULTY_TIME[difficulty]

        cache.set(f"puzzle_solution_{puzzle_id}", solution, timeout=None)

        puzzle = Puzzle.objects.create(
            puzzle_id=puzzle_id,
            question=question,
            solution='',
            difficulty=difficulty,
            points_value=points_value,
            time_limit=time_limit
        )
        serializer = PuzzleSerializer(puzzle)
        data_to_send = serializer.data
        data_to_send['image_url'] = question
        return Response(data_to_send)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def check_answer(request):
    puzzle_id = request.data.get('puzzle_id')
    answer = request.data.get('answer')
    time_taken = request.data.get('time_taken', 0)

    if not puzzle_id or answer is None:
        return Response({'error': 'puzzle_id and answer are required'}, status=400)

    try:
        puzzle = Puzzle.objects.get(puzzle_id=puzzle_id)
        correct_solution = cache.get(f"puzzle_solution_{puzzle_id}")

        is_correct = str(answer).strip() == str(correct_solution).strip()
        points_earned = puzzle.points_value if is_correct else 0

        # Create game record
        game_record = GameRecord.objects.create(
            player=request.user,
            puzzle_id=puzzle_id,
            player_answer=answer,
            is_correct=is_correct,
            points_earned=points_earned,
            time_taken=time_taken
        )

        # Update player stats using F expressions
        Profile.objects.filter(id=request.user.id).update(
            total_games_played=F('total_games_played') + 1,
            total_correct_answers=F('total_correct_answers') + int(is_correct),
            score=F('score') + points_earned
        )

        # Refresh user from DB to get real numbers
        request.user.refresh_from_db()

        serializer = GameRecordSerializer(game_record)
        return Response({
            'result': serializer.data,
            'correct': is_correct,
            'points_earned': points_earned,
            'total_score': request.user.score
        })

    except Puzzle.DoesNotExist:
        return Response({'error': 'Puzzle not found'}, status=404)




@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def leaderboard(request):
    limit = int(request.GET.get('limit', 10))

    # Calculate accuracy and get top players, excluding admins
    players = Profile.objects.exclude(role='admin').annotate(
        accuracy=Case(
            When(total_games_played=0, then=0),
            default=F('total_correct_answers') * 100.0 / F('total_games_played'),
            output_field=IntegerField()
        )
    ).order_by('-score', '-accuracy')[:limit]

    serializer = LeaderboardSerializer(players, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def player_stats(request):
    user = request.user
    recent_games = GameRecord.objects.filter(player=user).order_by('-attempted_at')[:10]
    recent_serializer = GameRecordSerializer(recent_games, many=True)

    stats = {
        'total_games': user.total_games_played,
        'total_correct': user.total_correct_answers,
        'total_score': user.score,
        'accuracy': (user.total_correct_answers / user.total_games_played * 100) if user.total_games_played > 0 else 0,
        'recent_games': recent_serializer.data
    }

    return Response(stats)

# Admin endpoints
@api_view(['GET'])
@permission_classes([IsAdmin])
def admin_analytics(request):

    total_players = Profile.objects.count()
    total_games = GameRecord.objects.count()
    total_correct = GameRecord.objects.filter(is_correct=True).count()
    overall_accuracy = (total_correct / total_games * 100) if total_games > 0 else 0

    # Daily stats for last 7 days
    seven_days_ago = timezone.now() - timedelta(days=7)
    daily_stats = []
    for i in range(7):
        day = seven_days_ago + timedelta(days=i)
        next_day = day + timedelta(days=1)
        day_games = GameRecord.objects.filter(attempted_at__range=(day, next_day)).count()
        day_correct = GameRecord.objects.filter(attempted_at__range=(day, next_day), is_correct=True).count()
        daily_stats.append({
            'date': day.date(),
            'games': day_games,
            'correct': day_correct,
            'accuracy': (day_correct / day_games * 100) if day_games > 0 else 0
        })

    analytics = {
        'total_players': total_players,
        'total_games': total_games,
        'total_correct_answers': total_correct,
        'overall_accuracy': overall_accuracy,
        'daily_stats': daily_stats
    }

    return Response(analytics)

@api_view(['POST'])
@permission_classes([IsAdmin])
def admin_create_puzzle(request):

    puzzle_id = request.data.get('puzzle_id')
    question = request.data.get('question')
    solution = request.data.get('solution')
    difficulty = request.data.get('difficulty', 'medium')
    points_value = request.data.get('points_value', 10)

    if not all([puzzle_id, question, solution]):
        return Response({'error': 'puzzle_id, question, and solution are required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        puzzle = Puzzle.objects.create(
            puzzle_id=puzzle_id,
            question=question,
            solution=solution,
            difficulty=difficulty,
            points_value=points_value
        )
        serializer = PuzzleSerializer(puzzle)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    except:
        return Response({'error': 'Puzzle with this ID already exists'}, status=status.HTTP_400_BAD_REQUEST)

# Additional endpoints based on feedback

@api_view(['PUT', 'PATCH'])
@permission_classes([permissions.IsAuthenticated])
def profile_update(request):
    serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def game_history(request):
    user = request.user
    game_records = GameRecord.objects.filter(player=user).order_by('-attempted_at')

    # Add pagination or limit
    limit = int(request.GET.get('limit', 50))
    game_records = game_records[:limit]

    serializer = GameRecordSerializer(game_records, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAdmin])
def admin_players(request):
    players = Profile.objects.exclude(role='admin').order_by('-date_joined')
    serializer = ProfileSerializer(players, many=True)
    return Response(serializer.data)

@api_view(['DELETE'])
@permission_classes([IsAdmin])
def admin_delete_player(request, player_id):
    try:
        player = Profile.objects.get(id=player_id)
        if player.role == 'admin':
            return Response({'error': 'Cannot delete admin users'}, status=status.HTTP_400_BAD_REQUEST)
        player.delete()
        return Response({'message': 'Player deleted successfully'})
    except Profile.DoesNotExist:
        return Response({'error': 'Player not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['DELETE'])
@permission_classes([IsAdmin])
def admin_delete_puzzle(request, puzzle_id):
    try:
        puzzle = Puzzle.objects.get(puzzle_id=puzzle_id)
        # Also remove from cache
        from django.core.cache import cache
        cache_key = f"puzzle_solution_{puzzle_id}"
        cache.delete(cache_key)

        puzzle.delete()
        return Response({'message': 'Puzzle deleted successfully'})
    except Puzzle.DoesNotExist:
        return Response({'error': 'Puzzle not found'}, status=status.HTTP_404_NOT_FOUND)
