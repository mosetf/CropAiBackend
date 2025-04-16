from django.contrib import admin
from django.urls import include, path
from .views import predict_yield, optimization_view
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('admin/', admin.site.urls),
    path('predict/', predict_yield, name='predict_yield'),
    path('optimize/', optimization_view, name='optimize'),
    # path('signup/', views.signup, name='signup'), 
]