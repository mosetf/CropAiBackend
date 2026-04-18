from django.db import models
from django.conf import settings

CROP_CHOICES = [
    ('maize',    'Maize'),
    ('beans',    'Beans'),
    ('wheat',    'Wheat'),
    ('sorghum',  'Sorghum'),
    ('coffee',   'Coffee'),
    ('tea',      'Tea'),
    ('potatoes', 'Potatoes'),
    ('cassava',  'Cassava'),
    ('rice',     'Rice'),
]

SEASON_CHOICES = [
    ('long_rains',  'Long Rains (Mar–Jul)'),
    ('short_rains', 'Short Rains (Oct–Feb)'),
]

RISK_CHOICES = [('low', 'Low'), ('medium', 'Medium'), ('high', 'High')]


class CropModel(models.Model):
    """Tracks which ML model files are available and their metadata."""
    crop        = models.CharField(max_length=50, choices=CROP_CHOICES, unique=True)
    file_path   = models.CharField(max_length=255)
    r2_score    = models.FloatField(null=True)
    mae         = models.FloatField(null=True)
    trained_at  = models.DateTimeField(null=True)
    is_active   = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.crop} model (R²={self.r2_score})"


class YieldPrediction(models.Model):
    """One prediction record per form submission."""
    user             = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                         related_name='predictions')
    # What was predicted
    crop             = models.CharField(max_length=50, choices=CROP_CHOICES, default='maize')
    location         = models.CharField(max_length=100)
    region           = models.CharField(max_length=100, blank=True)
    planting_date    = models.DateField()
    season           = models.CharField(max_length=20, choices=SEASON_CHOICES, blank=True)

    # Model outputs
    predicted_yield  = models.FloatField()       # t/ha
    yield_low        = models.FloatField(null=True)   # confidence lower bound
    yield_high       = models.FloatField(null=True)   # confidence upper bound
    harvest_window   = models.CharField(max_length=100)
    net_profit       = models.FloatField()             # KES

    # Weather inputs used
    rainfall         = models.FloatField()
    temperature      = models.FloatField()
    humidity         = models.FloatField()

    # Soil inputs used
    soil_ph          = models.FloatField(null=True)
    soil_moisture    = models.FloatField(null=True)
    organic_carbon   = models.FloatField(null=True)
    fertilizer_kg_ha = models.FloatField(null=True)

    # AI advisory output
    ai_recommendations = models.JSONField(default=list)
    risk_level         = models.CharField(max_length=10, choices=RISK_CHOICES,
                                           default='medium')
    risk_reason        = models.TextField(blank=True)

    # Meta
    fallback_used    = models.BooleanField(default=False)
    model_version    = models.CharField(max_length=50, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} — {self.crop} @ {self.location} ({self.created_at:%Y-%m-%d})"