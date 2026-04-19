from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from yield_predictor.urls import api_urlpatterns
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('', RedirectView.as_view(url='/api/schema/swagger-ui/', permanent=False)),
    path('admin/',    admin.site.urls),
    path('api/v1/auth/', include('accounts.urls')),
    path('api/v1/', include(api_urlpatterns)),

    # API Schema & Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
