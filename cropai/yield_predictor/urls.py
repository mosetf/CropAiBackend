"""
yield_predictor/urls.py - All URL routing: function-based and DRF API
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'yield_predictor'

api_router = DefaultRouter()
api_router.register(r'predictions', views.YieldPredictionViewSet, basename='prediction')
api_router.register(r'crops', views.CropModelViewSet, basename='crop')

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('predict/', views.predict_yield, name='predict_yield'),
    path('dashboard/', views.dashboard, name='dashboard'),
]

# Combine router URLs with custom meta endpoints
api_urlpatterns = api_router.urls + [
    path('meta/locations/', views.get_locations, name='meta-locations'),
    path('meta/crops/', views.get_crops, name='meta-crops'),
]

