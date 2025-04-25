from django.contrib import admin
from django.urls import include, path
from .views import predict_yield
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('admin/', admin.site.urls),
    path('predict/', views.predict_yield, name='predict_yield'),
    path('dashboard/', views.dashboard, name='dashboard'),
]