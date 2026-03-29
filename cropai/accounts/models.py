"""
accounts/models.py - UserSession model for active session tracking
"""
from django.db import models
from django.contrib.auth.models import User


class UserSession(models.Model):
    """
    Tracks active JWT refresh tokens per device.
    Enables the 'active sessions' dashboard and remote revocation.
    """
    user          = models.ForeignKey(User, on_delete=models.CASCADE,
                                       related_name='sessions')
    jti           = models.CharField(max_length=255, unique=True, db_index=True)
    device_name   = models.CharField(max_length=200, blank=True)
    device_type   = models.CharField(max_length=50, blank=True)
    browser       = models.CharField(max_length=100, blank=True)
    os            = models.CharField(max_length=100, blank=True)
    ip_address    = models.GenericIPAddressField(null=True, blank=True)
    location_hint = models.CharField(max_length=100, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    last_active   = models.DateTimeField(auto_now=True)
    expires_at    = models.DateTimeField()
    is_current    = models.BooleanField(default=False)

    class Meta:
        ordering = ['-last_active']
        verbose_name = 'User Session'
        verbose_name_plural = 'User Sessions'

    def __str__(self):
        return f"{self.user.username} — {self.device_name} ({self.last_active:%Y-%m-%d})"

    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at
