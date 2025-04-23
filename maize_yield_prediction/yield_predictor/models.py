from django.db import models
from django.contrib.auth.models import User

class YieldPrediction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    location = models.CharField(max_length=100)
    planting_date = models.DateField()
    predicted_yield = models.FloatField()
    harvest_window = models.CharField(max_length=100)
    net_profit = models.FloatField()
    rainfall = models.FloatField()
    temperature = models.FloatField()
    humidity = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.location} ({self.planting_date})"
