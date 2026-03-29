"""
accounts/admin.py - Django admin configuration for accounts
"""
from django.contrib import admin
from .models import UserSession


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'device_name', 'browser', 'os', 'created_at', 'last_active')
    list_filter = ('created_at', 'last_active', 'device_type')
    search_fields = ('user__username', 'device_name', 'browser')
    readonly_fields = ('jti', 'created_at', 'last_active')
