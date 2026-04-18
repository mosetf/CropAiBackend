"""
accounts/models.py - CustomUser, UserProfile, and UserSession models
"""
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator


class CustomUserManager(BaseUserManager):
    """Custom manager for CustomUser that uses email as USERNAME_FIELD"""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user."""
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    """
    Custom user model that uses email as the primary identifier.
    Removes the username field completely.
    """
    username = None
    email = models.EmailField(_('email address'), unique=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    objects = CustomUserManager()
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
    
    def __str__(self):
        return self.email


class UserProfile(models.Model):
    """
    Extended user profile with additional personal and farming information.
    Created automatically when user registers, updated by user later.
    """
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('prefer_not_to_say', 'Prefer not to say'),
    ]
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    
    # Personal Information
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Invalid phone number')],
        help_text='Phone number in international format (e.g., +1234567890)'
    )
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True)
    bio = models.TextField(blank=True, max_length=500, help_text='Tell us about yourself')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    
    # Location Information
    location = models.CharField(max_length=255, blank=True, help_text='City/Town')
    country = models.CharField(max_length=100, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Professional Information
    organization = models.CharField(max_length=255, blank=True, help_text='Company/Organization')
    
    # Farm Information (for CropAI app)
    farm_name = models.CharField(max_length=255, blank=True, help_text='Name of your farm')
    farm_size = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Farm size in hectares'
    )
    primary_crops = models.CharField(
        max_length=500,
        blank=True,
        help_text='Comma-separated list of primary crops grown'
    )
    
    # Status
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    profile_completed = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
    
    def __str__(self):
        return f"Profile of {self.user.email}"
    
    @property
    def full_name(self):
        """Return full name if available, else email"""
        if self.user.first_name and self.user.last_name:
            return f"{self.user.first_name} {self.user.last_name}"
        return self.user.email


class UserSession(models.Model):
    """
    Tracks active JWT refresh tokens per device.
    Enables the 'active sessions' dashboard and remote revocation.
    """
    user          = models.ForeignKey(CustomUser, on_delete=models.CASCADE,
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
        return f"{self.user.email} — {self.device_name} ({self.last_active:%Y-%m-%d})"

    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at
