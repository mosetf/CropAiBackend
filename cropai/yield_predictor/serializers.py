"""
yield_predictor/serializers.py - Both form-based and DRF serializers
"""
from django import forms
from rest_framework import serializers
from datetime import date, timedelta
from .models import YieldPrediction, CropModel, CROP_CHOICES
from .services.prediction_service import LOCATION_COORDS


# FORM-BASED SERIALIZERS (for HTML forms)


CROP_LIST = [(k, v) for k, v in CROP_CHOICES]
LOCATION_CHOICES = [(loc, loc) for loc in sorted(LOCATION_COORDS.keys())]


class PredictionInputForm(forms.Form):
    """
    Validates and cleans all user inputs before they reach prediction_service.
    The view passes request.POST directly to this form, then reads .cleaned_data.
    """

    crop = forms.ChoiceField(
        choices=CROP_LIST,
        initial='maize',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    location = forms.ChoiceField(
        choices=LOCATION_CHOICES,
        initial='Nakuru',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    planting_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        help_text='Date you plan to plant (or already planted).',
    )

    soil_ph = forms.FloatField(
        min_value=3.0,
        max_value=10.0,
        initial=6.0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'step': '0.1',
            'placeholder': '6.0',
        }),
        help_text='Soil pH (3–10). Optimal for most crops: 5.5–7.0.',
    )

    soil_moisture = forms.FloatField(
        min_value=0.0,
        max_value=100.0,
        initial=25.0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'step': '0.5',
            'placeholder': '25.0',
        }),
        help_text='Soil moisture percentage (0–100).',
    )

    organic_carbon = forms.FloatField(
        min_value=0.0,
        max_value=20.0,
        initial=1.5,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'step': '0.1',
            'placeholder': '1.5',
        }),
        help_text='Soil organic carbon (%). Target: >2% for good fertility.',
    )

    fertilizer = forms.FloatField(
        min_value=0.0,
        max_value=600.0,
        initial=100.0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'step': '5',
            'placeholder': '100',
        }),
        help_text='Total fertilizer applied (kg/ha).',
    )

    market_price = forms.FloatField(
        min_value=0.0,
        required=False,
        initial=None,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'step': '500',
            'placeholder': 'Leave blank for default',
        }),
        help_text='Expected farm-gate price (KES/tonne). Leave blank for current defaults.',
    )

    labour_cost = forms.FloatField(
        min_value=0.0,
        required=False,
        initial=None,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'step': '1000',
            'placeholder': 'Optional - for profit analysis',
        }),
        help_text='Labour cost (KES/ha). Optional—used for profit calculations.',
    )

    def clean_planting_date(self):
        d = self.cleaned_data['planting_date']
        today = date.today()
        if d < today - timedelta(days=60):
            raise forms.ValidationError(
                'Planting date is too far in the past (max 60 days ago).'
            )
        if d > today + timedelta(days=180):
            raise forms.ValidationError(
                'Planting date cannot be more than 180 days in the future.'
            )
        return d

    def clean(self):
        cleaned = super().clean()
        crop = cleaned.get('crop')
        location = cleaned.get('location')

        NON_ASAL_CROPS = {'tea', 'coffee'}
        ASAL_LOCATIONS = {
            'Turkana', 'Marsabit', 'Mandera', 'Wajir', 'Garissa',
            'Isiolo', 'Tana River', 'Lamu',
        }
        if crop in NON_ASAL_CROPS and location in ASAL_LOCATIONS:
            self.add_error(
                'crop',
                f'{crop.title()} is not typically viable in {location} '
                f'(arid/semi-arid region). Consider sorghum or cassava.'
            )

        return cleaned

    def to_service_dict(self) -> dict:
        """Converts cleaned form data into kwargs for prediction_service.run_prediction()."""
        d = self.cleaned_data
        return {
            'crop':          d['crop'],
            'location':      d['location'],
            'planting_date': d['planting_date'],
            'fertilizer':    d['fertilizer'],
            'soil_data': {
                'soil_ph':        d['soil_ph'],
                'soil_moisture':  d['soil_moisture'],
                'organic_carbon': d['organic_carbon'],
            },
            'market_price_override': d.get('market_price'),
            'labour_cost_override': d.get('labour_cost'),
        }

# DRF SERIALIZERS (for REST API)

class CropModelSerializer(serializers.ModelSerializer):
    """Serializer for crop model metadata"""
    class Meta:
        model = CropModel
        fields = ('id', 'crop', 'r2_score', 'mae', 'trained_at', 'is_active')
        read_only_fields = ('id', 'trained_at')


class YieldPredictionSerializer(serializers.ModelSerializer):
    """Serializer for yield predictions.

    Writable input fields (provided by the client):
        crop, location, planting_date, soil_ph, soil_moisture,
        organic_carbon, fertilizer_kg_ha

    All other fields are server-computed outputs and are read-only.
    """
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = YieldPrediction
        fields = (
            'id', 'user_email',
            # --- client-supplied inputs ---
            'crop', 'location', 'planting_date',
            'soil_ph', 'soil_moisture', 'organic_carbon', 'fertilizer_kg_ha',
            # --- server-computed outputs ---
            'region', 'season',
            'predicted_yield', 'yield_low', 'yield_high',
            'harvest_window', 'net_profit',
            'rainfall', 'temperature', 'humidity',
            'ai_recommendations', 'risk_level', 'risk_reason',
            'fallback_used', 'created_at',
        )
        read_only_fields = (
            'id', 'user_email',
            'region', 'season',
            'predicted_yield', 'yield_low', 'yield_high',
            'harvest_window', 'net_profit',
            'rainfall', 'temperature', 'humidity',
            'ai_recommendations', 'risk_level', 'risk_reason',
            'fallback_used', 'created_at',
        )
