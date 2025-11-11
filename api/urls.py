from django.urls import path
from .views import (
    RegisterView, login_view, profile_view, profile_update, get_puzzle, check_answer,
    leaderboard, game_history, admin_analytics, admin_create_puzzle, admin_players,
    admin_delete_player, admin_delete_puzzle,login_step1,login_step2_verify_otp
)

urlpatterns = [
    # Authentication
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', login_step1, name='login'),
    path("verify-otp/", login_step2_verify_otp, name="verify_otp"),
    path('profile/', profile_view, name='profile'),
    path('profile/update/', profile_update, name='profile_update'),

    # Game endpoints
    path('game/question/', get_puzzle, name='get_puzzle'),
    path('game/answer/', check_answer, name='check_answer'),
    path('game/history/', game_history, name='game_history'),
    path('leaderboard/', leaderboard, name='leaderboard'),

    # Admin endpoints
    path('admin/players/', admin_players, name='admin_players'),
    path('admin/players/<int:player_id>/delete/', admin_delete_player, name='admin_delete_player'),
    path('admin/stats/', admin_analytics, name='admin_stats'),
    path('admin/puzzles/', admin_create_puzzle, name='admin_create_puzzle'),
    path('admin/puzzles/<str:puzzle_id>/delete/', admin_delete_puzzle, name='admin_delete_puzzle'),
]
