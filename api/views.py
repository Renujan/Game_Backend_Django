from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.db import models
from django.db.models import Q, F, Count, Case, When, IntegerField
from django.utils import timezone
from datetime import timedelta
import random
import requests
from .models import Profile, GameRecord, Puzzle
from .serializers import ProfileSerializer, GameRecordSerializer, PuzzleSerializer, LeaderboardSerializer, LoginSerializer, ProfileUpdateSerializer, RegisterSerializer
from .permissions import IsAdmin

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
                'coins': user.coins,
                'role': user.role
            }
        })
    return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

from django.core.cache import cache
from django.core.mail import send_mail
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
import random
from .models import Profile

@api_view(['POST'])
def login_step1(request):
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(username=username, password=password)

    if not user:
        return Response({'error': 'Invalid credentials'}, status=401)

    # ✅ Generate OTP
    otp = random.randint(100000, 999999)

    # ✅ Save OTP in cache for 5 minutes
    cache.set(f"otp_{user.email}", otp, timeout=300)

    # ✅ Send Email
    send_mail(
        subject="Your OTP Code",
        message=f"Your OTP is: {otp}",
        from_email="noreply@banana.com",
        recipient_list=[user.email],
    )

    return Response({
        "message": "OTP sent to registered email ✅",
        "otp_sent": True,
        "email": user.email
    }, status=200)

from rest_framework_simplejwt.tokens import RefreshToken

@api_view(['POST'])
def login_step2_verify_otp(request):
    email = request.data.get("email")
    otp = request.data.get("otp")

    if not email or not otp:
        return Response({"error": "Email & OTP required"}, status=400)

    saved_otp = cache.get(f"otp_{email}")

    if not saved_otp:
        return Response({"error": "OTP expired"}, status=400)

    if str(saved_otp) != str(otp):
        return Response({"error": "Invalid OTP"}, status=400)

    # ✅ OTP correct → Login
    user = Profile.objects.get(email=email)

    refresh = RefreshToken.for_user(user)

    # ✅ Clean OTP
    cache.delete(f"otp_{email}")

    return Response({
        "message": "Login successful ✅",
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "score": user.score,
            "coins": user.coins,
            "role": user.role
        }
    }, status=200)

# ---------------------------
# POWER-UP ENDPOINTS
# ---------------------------

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def freeze_timer(request):
    puzzle_id = request.data.get('puzzle_id')
    freeze_seconds = int(request.data.get('freeze_seconds', 5))

    # Validate freeze duration
    if freeze_seconds not in [5, 10]:
        return Response({'error': 'Invalid freeze duration. Use 5 or 10 seconds.'}, status=400)

    # Calculate cost
    cost = 20 if freeze_seconds == 5 else 35

    # Check user has enough coins
    if request.user.coins < cost:
        return Response({
            'error': f'Not enough coins. Need {cost} coins.',
            'current_coins': request.user.coins,
            'required_coins': cost
        }, status=400)

    if not puzzle_id:
        return Response({'error': 'puzzle_id is required'}, status=400)

    try:
        # Deduct coins atomically
        Profile.objects.filter(id=request.user.id).update(coins=F('coins') - cost)

        # Store freeze status in cache (temporary)
        freeze_key = f"timer_freeze_{request.user.id}"
        cache.set(freeze_key, True, timeout=freeze_seconds)

        # Refresh user coins
        request.user.refresh_from_db()

        return Response({
            'success': True,
            'freeze_seconds': freeze_seconds,
            'coins_spent': cost,
            'coins_left': request.user.coins,
            'active_until': timezone.now() + timedelta(seconds=freeze_seconds)
        })

    except Exception as e:
        return Response({'error': 'Failed to activate freeze timer'}, status=500)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def double_points(request):
    puzzle_id = request.data.get('puzzle_id')
    cost = 50

    # Check user has enough coins
    if request.user.coins < cost:
        return Response({
            'error': f'Not enough coins. Need {cost} coins.',
            'current_coins': request.user.coins,
            'required_coins': cost
        }, status=400)

    if not puzzle_id:
        return Response({'error': 'puzzle_id is required'}, status=400)

    try:
        # Deduct coins atomically
        Profile.objects.filter(id=request.user.id).update(coins=F('coins') - cost)

        # Store double points in cache for next puzzle
        double_key = f"double_points_{request.user.id}"
        cache.set(double_key, True, timeout=300)  # 5 minutes to use

        # Refresh user coins
        request.user.refresh_from_db()

        return Response({
            'success': True,
            'multiplier': 2.0,
            'coins_spent': cost,
            'coins_left': request.user.coins,
            'active_for_next': True
        })

    except Exception as e:
        return Response({'error': 'Failed to activate double points'}, status=500)




@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def profile_view(request):
    # Ensure coins field exists and has default value for backward compatibility
    # Also update in database to fix permanently
    if request.user.coins is None or request.user.coins <= 0:
        request.user.coins = 100
        request.user.save()

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
    1. Call Banana API with difficulty parameter
    2. Store solution in cache
    3. Return image URL to frontend with selected difficulty
    """
    # Read and validate difficulty from query params
    difficulty = request.query_params.get('difficulty', 'medium')
    if difficulty not in ['easy', 'medium', 'hard']:
        difficulty = 'medium'  # Default if invalid

    try:
        # Include difficulty in Banana API request
        api_url = f"{BANANA_API_URL}?difficulty={difficulty}"
        response = requests.get(api_url, timeout=5)
        if response.status_code != 200:
            raise Exception("Banana API error")
        data = response.json()

        puzzle_id = f"{difficulty}_{random.randint(1000,9999)}"
        question = data.get("question")  # This is the image URL
        solution = str(data.get("solution"))
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
        # Fallback sample puzzle with selected difficulty
        puzzle_id = f"sample_{difficulty}_{random.randint(1000,9999)}"
        question = "https://via.placeholder.com/400?text=Sample+Puzzle"
        solution = "4"
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
    current_streak = int(request.data.get('current_streak', 0))

    if not puzzle_id or answer is None:
        return Response({'error': 'puzzle_id and answer are required'}, status=400)

    try:
        puzzle = Puzzle.objects.get(puzzle_id=puzzle_id)
        correct_solution = cache.get(f"puzzle_solution_{puzzle_id}")

        is_correct = str(answer).strip() == str(correct_solution).strip()

        # Calculate streak multiplier (1x, 1.5x, 2x, 2.5x for streaks 3,5,7+)
        if is_correct and current_streak >= 0:
            if current_streak >= 7:
                multiplier = 2.5
            elif current_streak >= 5:
                multiplier = 2.0
            elif current_streak >= 3:
                multiplier = 1.5
            else:
                multiplier = 1.0
        else:
            multiplier = 1.0

        # Speed bonus (faster answers get extra points)
        speed_bonus = 0
        time_limit = DIFFICULTY_TIME.get(puzzle.difficulty, 45)
        if is_correct and time_taken < time_limit * 0.3:  # Within 30% of time limit
            speed_bonus = puzzle.points_value * 0.2  # 20% bonus

        # Check for double points power-up
        double_key = f"double_points_{request.user.id}"
        double_points_active = cache.get(double_key) is not None
        if double_points_active:
            multiplier *= 2.0  # Apply double points multiplier
            cache.delete(double_key)  # Consume the power-up

        base_points = puzzle.points_value if is_correct else 0
        points_earned = int((base_points * multiplier) + speed_bonus)

        # Create game record
        game_record = GameRecord.objects.create(
            player=request.user,
            puzzle_id=puzzle_id,
            player_answer=answer,
            is_correct=is_correct,
            points_earned=points_earned,
            time_taken=time_taken
        )

        # Award coins for winning puzzle (10 coins per win)
        coins_earned = 10 if is_correct else 0

        # Update player stats using F expressions
        Profile.objects.filter(id=request.user.id).update(
            total_games_played=F('total_games_played') + 1,
            total_correct_answers=F('total_correct_answers') + int(is_correct),
            score=F('score') + points_earned,
            coins=F('coins') + coins_earned  # Award 10 coins for correct answers
        )

        # Refresh user from DB to get real numbers
        request.user.refresh_from_db()

        serializer = GameRecordSerializer(game_record)
        return Response({
            'result': serializer.data,
            'correct': is_correct,
            'points_earned': points_earned,
            'coins_earned': coins_earned,  # Add coins earned to response
            'time_taken': time_taken,  # Important: Include time_taken in response
            'multiplier': multiplier,
            'speed_bonus': int(speed_bonus),
            'total_score': request.user.score,
            'total_coins': request.user.coins  # Include updated coin total
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
def leaderboard_weekly(request):
    limit = int(request.GET.get('limit', 10))

    # Get players with games in the last 7 days
    week_ago = timezone.now() - timedelta(days=7)
    recent_players = Profile.objects.filter(
        game_records__attempted_at__gte=week_ago
    ).distinct().exclude(role='admin')

    # Calculate weekly stats for each player
    players_weekly = []
    for player in recent_players[:limit]:
        week_games = player.game_records.filter(attempted_at__gte=week_ago)
        week_correct = week_games.filter(is_correct=True).count()
        week_total = week_games.count()
        week_score = week_games.filter(is_correct=True).aggregate(
            total_points=models.Sum('points_earned')
        )['total_points'] or 0

        week_accuracy = (week_correct / week_total * 100) if week_total > 0 else 0

        players_weekly.append({
            'id': player.id,
            'username': player.username,
            'weekly_games': week_total,
            'weekly_correct': week_correct,
            'weekly_score': week_score,
            'weekly_accuracy': round(week_accuracy, 1),
            'total_score': player.score
        })

    # Sort by weekly score, then weekly accuracy
    players_weekly.sort(key=lambda x: (-x['weekly_score'], -x['weekly_accuracy']))
    return Response(players_weekly[:limit])

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
