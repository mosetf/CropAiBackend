"""
yield_predictor/urls.py - URL routing for REST API endpoints
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'yield_predictor'

api_router = DefaultRouter()
api_router.register(r'predictions', views.YieldPredictionViewSet, basename='prediction')
api_router.register(r'crops', views.CropModelViewSet, basename='crop')

urlpatterns = []

# Combine router URLs with custom meta endpoints
api_urlpatterns = api_router.urls + [
    path('meta/locations/', views.get_locations, name='meta-locations'),
    path('meta/crops/', views.get_crops, name='meta-crops'),
    path('weather/current/', views.get_current_weather, name='weather-current'),
]

