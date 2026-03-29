from django.contrib import admin
from django.urls import path, include
from yield_predictor.urls import api_urlpatterns

urlpatterns = [
    path('admin/',    admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('api/v1/auth/', include('accounts.urls')),
    path('api/v1/', include(api_urlpatterns)),
    path('',          include('yield_predictor.urls', namespace='yield_predictor')),
]
