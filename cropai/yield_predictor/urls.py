from django.urls import path
from . import views

app_name = 'yield_predictor'

urlpatterns = [
    path('',          views.landing_page,  name='landing'),
    path('predict/',  views.predict_yield, name='predict_yield'),
    path('dashboard/',views.dashboard,     name='dashboard'),
]