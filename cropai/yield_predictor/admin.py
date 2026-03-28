from django.contrib import admin
from .models import YieldPrediction, CropModel

@admin.register(YieldPrediction)
class YieldPredictionAdmin(admin.ModelAdmin):
    list_display = ['user', 'crop', 'location', 'predicted_yield', 'risk_level', 'created_at']
    list_filter = ['crop', 'risk_level', 'season', 'fallback_used', 'created_at']
    search_fields = ['user__username', 'location', 'crop']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('user', 'crop', 'location', 'region', 'planting_date', 'season')
        }),
        ('Prediction Results', {
            'fields': ('predicted_yield', 'yield_low', 'yield_high', 'harvest_window', 'net_profit')
        }),
        ('Input Conditions', {
            'fields': ('rainfall', 'temperature', 'humidity', 'soil_ph', 'soil_moisture', 'organic_carbon', 'fertilizer_kg_ha')
        }),
        ('AI Advisory', {
            'fields': ('ai_recommendations', 'risk_level', 'risk_reason')
        }),
        ('Meta', {
            'fields': ('fallback_used', 'model_version', 'created_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(CropModel)
class CropModelAdmin(admin.ModelAdmin):
    list_display = ['crop', 'r2_score', 'mae', 'is_active', 'trained_at']
    list_filter = ['is_active', 'crop', 'trained_at']
    search_fields = ['crop']
    readonly_fields = ['trained_at']
