"""
accounts/urls.py - Authentication API routes
"""
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('refresh/', views.refresh_view, name='refresh'),
    path('user/', views.current_user_view, name='user'),
    path('sessions/', views.sessions_view, name='sessions'),
]
