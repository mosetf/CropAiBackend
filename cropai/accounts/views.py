"""
accounts/views.py - JWT authentication views with session tracking and remember me
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from user_agents import parse
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from .models import UserSession
from .serializers import UserSerializer, UserSessionSerializer, LoginSerializer, RegisterSerializer


def get_device_info(request):
    """Extract device info from User-Agent header"""
    user_agent_string = request.META.get('HTTP_USER_AGENT', '')
    user_agent = parse(user_agent_string)
    
    return {
        'device_name': f"{user_agent.device.brand} {user_agent.device.model}".strip() or "Unknown Device",
        'device_type': user_agent.device.family or 'unknown',
        'browser': f"{user_agent.browser.family} {user_agent.browser.version_string}".strip(),
        'os': f"{user_agent.os.family} {user_agent.os.version_string}".strip(),
        'ip_address': get_client_ip(request),
    }


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@extend_schema(
    tags=['Authentication'],
    summary='User Registration',
    description='Register a new user account and return JWT tokens. Access token in response body, refresh token in httpOnly cookie.',
    request=RegisterSerializer,
    responses={
        201: RegisterSerializer,
        400: OpenApiResponse(description='Validation errors (duplicate username/email, password mismatch, etc)')
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """
    POST /api/v1/auth/register/
    
    Register a new user with email and password.
    Returns:
      - access token (in response body, in-memory only)
      - refresh token (in httpOnly cookie)
      - new user info
    """
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    # Create new user
    user = User.objects.create_user(
        username=serializer.validated_data['username'],
        email=serializer.validated_data['email'],
        password=serializer.validated_data['password'],
        first_name=serializer.validated_data.get('first_name', ''),
        last_name=serializer.validated_data.get('last_name', ''),
    )
    
    # Generate tokens
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)
    
    lifetime = timedelta(days=1)
    expires_at = timezone.now() + lifetime
    
    device_info = get_device_info(request)
    jti = str(refresh['jti'])
    
    UserSession.objects.create(
        user=user,
        jti=jti,
        expires_at=expires_at,
        **device_info,
    )
    
    response = Response({
        'access': access_token,
        'user': UserSerializer(user).data,
    }, status=status.HTTP_201_CREATED)
    
    response.set_cookie(
        key='cropai_refresh',
        value=refresh_token,
        max_age=int(lifetime.total_seconds()),
        httponly=True,
        secure=False,
        samesite='Lax',
    )
    
    return response


@extend_schema(
    tags=['Authentication'],
    summary='User Login',
    description='Authenticate user with credentials and return JWT tokens. Access token in response body, refresh token in httpOnly cookie.',
    request=LoginSerializer,
    responses={200: UserSerializer}
)
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    POST /api/v1/auth/login/
    
    Login endpoint with JWT and device tracking.
    Returns:
      - access token (in response body, in-memory only)
      - refresh token (in httpOnly cookie)
      - current user info
    """
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    username = serializer.validated_data.get('username')
    password = serializer.validated_data.get('password')
    remember_me = serializer.validated_data.get('remember_me', False)
    
    user = authenticate(username=username, password=password)
    if not user:
        return Response(
            {'detail': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Generate tokens
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)
    
    # Token lifetime based on remember_me
    if remember_me:
        lifetime = timedelta(days=30)
    else:
        lifetime = timedelta(days=1)
    
    # Refresh token expires at
    expires_at = timezone.now() + lifetime
    
    # Get device info and create session
    device_info = get_device_info(request)
    jti = str(refresh['jti'])
    
    UserSession.objects.create(
        user=user,
        jti=jti,
        expires_at=expires_at,
        **device_info,
    )
    
    response = Response({
        'access': access_token,
        'user': UserSerializer(user).data,
    })
    
    # Set refresh token in httpOnly cookie
    response.set_cookie(
        key='cropai_refresh',
        value=refresh_token,
        max_age=int(lifetime.total_seconds()),
        httponly=True,
        secure=False,  # Set True in production with HTTPS
        samesite='Lax',
    )
    
    return response


@extend_schema(
    tags=['Authentication'],
    summary='User Logout',
    description='Logout current user. Blacklists refresh token and deletes session record.',
    responses=OpenApiTypes.OBJECT
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    POST /api/v1/auth/logout/
    
    Logout endpoint. Blacklists refresh token and deletes session.
    """
    refresh_token = request.COOKIES.get('cropai_refresh')
    
    if refresh_token:
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            # Delete session record
            jti = str(token['jti'])
            UserSession.objects.filter(jti=jti).delete()
        except (TokenError, InvalidToken):
            pass
    
    response = Response({'detail': 'Logged out successfully'})
    response.delete_cookie('cropai_refresh')
    return response


@extend_schema(
    tags=['Authentication'],
    summary='Refresh Access Token',
    description='Refresh expired access token using refresh token from cookie. Rotates tokens for security.',
    responses=OpenApiTypes.OBJECT
)
@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_view(request):
    """
    POST /api/v1/auth/refresh/
    
    Token refresh endpoint. Reads refresh token from cookie, validates it,
    and rotates tokens (blacklists old, issues new).
    """
    refresh_token = request.COOKIES.get('cropai_refresh')
    
    if not refresh_token:
        return Response(
            {'detail': 'No refresh token provided'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    try:
        refresh = RefreshToken(refresh_token)
        
        # Get session and update last_active
        jti = str(refresh['jti'])
        session = UserSession.objects.get(jti=jti)
        session.last_active = timezone.now()
        session.save(update_fields=['last_active'])
        
        # Rotate tokens: blacklist old, issue new
        access_token = str(refresh.access_token)
        new_refresh = RefreshToken.for_user(session.user)
        new_refresh_token = str(new_refresh)
        
        # Blacklist old refresh token
        refresh.blacklist()
        
        # Create new session record with new JTI
        new_jti = str(new_refresh['jti'])
        old_session = session
        old_session.delete()
        
        device_info = get_device_info(request)
        expires_at = timezone.now() + timedelta(days=30 if old_session.expires_at > (timezone.now() + timedelta(days=7)) else 1)
        
        UserSession.objects.create(
            user=session.user,
            jti=new_jti,
            expires_at=expires_at,
            **device_info,
        )
        
        response = Response({'access': access_token})
        response.set_cookie(
            key='cropai_refresh',
            value=new_refresh_token,
            max_age=int((expires_at - timezone.now()).total_seconds()),
            httponly=True,
            secure=False,
            samesite='Lax',
        )
        
        return response
    except (TokenError, InvalidToken):
        return Response(
            {'detail': 'Invalid refresh token'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    except UserSession.DoesNotExist:
        return Response(
            {'detail': 'Session not found'},
            status=status.HTTP_401_UNAUTHORIZED
        )


@extend_schema(
    tags=['Authentication'],
    summary='Get Current User',
    description='Retrieve current authenticated user information.',
    responses={
        200: UserSerializer,
        401: OpenApiResponse(description='Not authenticated')
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user_view(request):
    """
    GET /api/v1/auth/user/
    
    Get current authenticated user info.
    """
    return Response(UserSerializer(request.user).data)


@extend_schema(
    tags=['Authentication'],
    summary='Manage User Sessions',
    description='GET: List all active sessions for current user. DELETE: Revoke sessions (all others or specific by id).',
    responses=OpenApiTypes.OBJECT
)
@api_view(['GET', 'DELETE'])
@permission_classes([IsAuthenticated])
def sessions_view(request):
    """
    GET /api/v1/auth/sessions/
    Lists all active sessions for current user.
    
    DELETE /api/v1/auth/sessions/
    Revokes all other sessions (keeps current session active).
    
    DELETE /api/v1/auth/sessions/{id}/
    Revokes a specific session by ID.
    """
    if request.method == 'GET':
        sessions = UserSession.objects.filter(user=request.user)
        serializer = UserSessionSerializer(
            sessions,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)
    
    if request.method == 'DELETE':
        session_id = request.query_params.get('id')
        
        if session_id:
            # Revoke specific session
            session = UserSession.objects.filter(
                user=request.user,
                id=session_id
            ).first()
            if not session:
                return Response(
                    {'detail': 'Session not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            session.delete()
        else:
            # Revoke all other sessions
            refresh_token = request.COOKIES.get('cropai_refresh')
            current_jti = None
            
            if refresh_token:
                try:
                    current_jti = str(RefreshToken(refresh_token)['jti'])
                except:
                    pass
            
            UserSession.objects.filter(user=request.user).exclude(
                jti=current_jti
            ).delete()
        
        return Response({'detail': 'Session(s) revoked'})
