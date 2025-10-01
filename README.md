# CropAI Kenya - Agricultural Yield Prediction Platform

**An advanced machine learning platform for crop yield prediction and harvest optimization specifically designed for Kenyan farmers, featuring multi-crop support, real-time weather integration, and comprehensive farming analytics.**

---

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Installation & Setup](#installation--setup)
- [Configuration](#configuration)
- [Usage Guide](#usage-guide)
- [API Documentation](#api-documentation)
- [Model Information](#model-information)
- [Database Schema](#database-schema)
- [Frontend Architecture](#frontend-architecture)
- [Deployment](#deployment)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

CropAI Kenya is a comprehensive agricultural technology platform that leverages machine learning algorithms and real-time weather data to provide accurate crop yield predictions for Kenyan farmers. The platform currently supports maize prediction with plans to expand to other major Kenyan crops including beans, coffee, tea, wheat, and sorghum.

### Key Objectives
- Provide accurate yield predictions based on local soil conditions, weather patterns, and farming practices
- Optimize harvest scheduling using real-time weather forecasting
- Deliver actionable insights through an intuitive web interface
- Support data-driven decision making for smallholder and commercial farmers
- Integrate with Kenya-specific agricultural data and weather patterns

### Target Users
- Smallholder farmers seeking yield optimization
- Commercial agricultural operations
- Agricultural extension officers
- Agricultural research institutions
- Government agricultural departments

---

## Features

### Core Functionality
- **Machine Learning Yield Prediction**: Random Forest algorithm trained on Kenyan agricultural data
- **Real-time Weather Integration**: OpenWeather API integration with location-specific data
- **Multi-crop Support**: Expandable framework for different crop types
- **Harvest Optimization**: Intelligent scheduling based on weather forecasts
- **Profit Calculation**: Net profit estimation based on yield predictions and market prices

### User Interface
- **Responsive Dashboard**: Multi-crop selection interface with intuitive navigation
- **Detailed Analytics**: Comprehensive prediction history with visual metrics
- **User Authentication**: Secure account management with Django Allauth
- **Mobile-Friendly Design**: Bootstrap 5 responsive framework
- **Farmer-Themed UI**: Agricultural-focused design with green color scheme

### Technical Features
- **Fallback Weather Data**: Robust system with backup weather sources
- **Data Quality Indicators**: Visual feedback on prediction accuracy
- **Chart Visualization**: Chart.js integration for data representation
- **Scalable Architecture**: Django-based modular design
- **Database Optimization**: Efficient data storage and retrieval

---

## Technology Stack

### Backend
- **Django 5.2.6**: Web framework and API backend
- **Python 3.11+**: Core programming language
- **Scikit-learn 1.5.2**: Machine learning algorithms
- **Pandas 2.3.3**: Data manipulation and analysis
- **NumPy 2.3.3**: Numerical computing

### Frontend
- **Bootstrap 5**: Responsive CSS framework
- **Chart.js**: Data visualization library
- **Font Awesome**: Icon library
- **Django Templates**: Server-side rendering
- **Custom CSS**: Farmer-themed styling

### Database & Storage
- **SQLite**: Development database
- **PostgreSQL**: Production database (recommended)
- **Django ORM**: Object-relational mapping

### APIs & Services
- **OpenWeather API**: Real-time weather data
- **Django REST Framework**: API development
- **Django Allauth**: Authentication system

### Development Tools
- **pip-tools**: Dependency management
- **Django Debug Toolbar**: Development debugging
- **Python Logging**: Application monitoring

---

## Project Structure

```
CropYieldPrediction/
│
├── data/                           # Data storage and processing
│   ├── raw/                        # Original datasets
│   │   ├── maize_yield_dataset_5000_locations.csv
│   │   └── yield_df.csv
│   ├── processed/                  # Cleaned and preprocessed data
│   │   ├── maize_yield_dataset_500_enhanced.csv
│   │   └── maize_yield_kenya_processed.csv
│   └── external/                   # External API data cache
│
├── models/                         # Trained ML models
│   └── rf_yield_model.pkl          # Random Forest yield prediction model
│
├── notebooks/                      # Jupyter notebooks for development
│   ├── 01_data_simulation.ipynb    # Data exploration and simulation
│   └── actual_vs_predicted_yield.png
│
├── maize_yield_prediction/         # Django project root
│   ├── manage.py                   # Django management script
│   ├── db.sqlite3                  # Development database
│   │
│   ├── maize_yield_prediction/     # Project configuration
│   │   ├── __init__.py
│   │   ├── settings.py             # Django settings
│   │   ├── urls.py                 # URL routing
│   │   ├── wsgi.py                 # WSGI configuration
│   │   └── asgi.py                 # ASGI configuration
│   │
│   ├── yield_predictor/            # Main application
│   │   ├── models.py               # Database models
│   │   ├── views.py                # View logic and API endpoints
│   │   ├── urls.py                 # App URL patterns
│   │   ├── admin.py                # Django admin configuration
│   │   ├── apps.py                 # App configuration
│   │   │
│   │   ├── templates/              # HTML templates
│   │   │   ├── base.html           # Base template
│   │   │   ├── account/            # Authentication templates
│   │   │   └── yield_predictor/    # App-specific templates
│   │   │       ├── dashboard.html  # Main dashboard
│   │   │       ├── landing.html    # Landing page
│   │   │       └── predict.html    # Prediction form
│   │   │
│   │   ├── static/                 # Static files
│   │   │   ├── css/                # Stylesheets
│   │   │   │   ├── dashboard.css   # Dashboard styling
│   │   │   │   ├── landing.css     # Landing page styling
│   │   │   │   └── predict.css     # Prediction form styling
│   │   │   └── js/                 # JavaScript files
│   │   │       └── dashboard.js    # Dashboard functionality
│   │   │
│   │   ├── utils/                  # Utility modules
│   │   │   └── weather_utils.py    # Weather API integration
│   │   │
│   │   ├── migrations/             # Database migrations
│   │   └── templatetags/           # Custom template tags
│   │
│   ├── staticfiles/                # Collected static files
│   └── logs/                       # Application logs
│       └── weather.log
│
├── requirements.txt                # Python dependencies
├── retrain_model.py               # Model retraining script
├── test_model.py                  # Model testing utilities
├── test_dashboard.html            # Development testing file
└── README.md                      # Project documentation
```

---

## Installation & Setup

### Prerequisites
- Python 3.11 or higher
- pip package manager
- Git version control
- OpenWeather API key (free tier available)

### Step 1: Clone Repository
```bash
git clone https://github.com/mosetf/CropYieldPrediction.git
cd CropYieldPrediction
```

### Step 2: Create Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Environment Configuration
Create a `.env` file in the project root:
```env
API_KEY=your_openweather_api_key_here
BASE_URL=http://api.openweathermap.org/data/2.5/weather?
OPENWEATHER_FORECAST_URL=http://api.openweathermap.org/data/2.5/forecast?
SECRET_KEY=your_django_secret_key_here
DEBUG=True
```

### Step 5: Database Setup
```bash
cd maize_yield_prediction
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput
```

### Step 6: Create Superuser (Optional)
```bash
python manage.py createsuperuser
```

### Step 7: Run Development Server
```bash
python manage.py runserver
```

The application will be available at `http://127.0.0.1:8000/`

---

## Configuration

### Environment Variables
| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `API_KEY` | OpenWeather API key | Yes | None |
| `BASE_URL` | OpenWeather base URL | Yes | http://api.openweathermap.org/data/2.5/weather? |
| `OPENWEATHER_FORECAST_URL` | OpenWeather forecast URL | Yes | http://api.openweathermap.org/data/2.5/forecast? |
| `SECRET_KEY` | Django secret key | Yes | None |
| `DEBUG` | Django debug mode | No | False |

### Django Settings
Key configuration options in `settings.py`:

```python
# Authentication
LOGIN_REDIRECT_URL = '/dashboard/'
ACCOUNT_EMAIL_VERIFICATION = "mandatory"

# Static Files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    # ... detailed logging configuration
}
```

---

## Usage Guide

### Accessing the Platform
1. **Landing Page**: Visit `http://127.0.0.1:8000/` for the welcome page
2. **Registration**: Create an account via the sign-up form
3. **Dashboard**: Access `http://127.0.0.1:8000/dashboard/` after login

### Making Predictions
1. Click on the "Maize" card in the dashboard
2. Fill out the prediction form with:
   - Location (select from Kenyan locations)
   - Planting date
   - Soil conditions (pH, moisture, organic carbon)
   - Fertilizer usage
3. Submit for AI-powered yield prediction
4. View results including:
   - Predicted yield (tons/hectare)
   - Harvest window
   - Net profit estimation
   - Weather conditions used

### Dashboard Features
- **Summary Analytics**: Overview of all your predictions
- **Detailed History**: Complete prediction records with metrics
- **Weather Integration**: Real-time weather data display
- **Data Quality Indicators**: Visual feedback on prediction accuracy

---

## API Documentation

### Authentication
The API uses Django's session-based authentication. Users must be logged in to access prediction endpoints.

### Endpoints

#### POST /predict/
Create a new yield prediction.

**Request Parameters:**
```json
{
    "location": "Eldoret",
    "planting_date": "2025-10-15",
    "soil_moisture": 25.0,
    "soil_ph": 6.5,
    "organic_carbon": 1.8,
    "fertilizer": 120.0
}
```

**Response:**
```json
{
    "success": true,
    "prediction": {
        "predicted_yield": 4.25,
        "harvest_window": "2026-02-15 to 2026-03-01",
        "net_profit": 125000.0,
        "weather_conditions": {
            "rainfall": 15.2,
            "temperature": 22.5,
            "humidity": 78
        },
        "fallback_used": false
    }
}
```

#### GET /dashboard/
Retrieve user dashboard with prediction history.

**Response:**
```json
{
    "predictions": [...],
    "chart_data": {...},
    "forecast": {...}
}
```

---

## Model Information

### Algorithm
- **Type**: Random Forest Regression
- **Framework**: Scikit-learn 1.5.2
- **Features**: 6 input features (location coordinates, weather, soil conditions)
- **Target**: Maize yield in tons per hectare

### Training Data
- **Dataset Size**: 5000 synthetic records based on Kenyan agricultural patterns
- **Geographic Coverage**: 20 major agricultural regions in Kenya
- **Weather Integration**: Historical and real-time OpenWeather data
- **Soil Parameters**: pH, moisture content, organic carbon levels

### Model Performance
- **Cross-validation Score**: R² > 0.85
- **Mean Absolute Error**: < 0.5 tons/hectare
- **Geographic Accuracy**: Optimized for Kenyan growing conditions

### Feature Importance
1. Rainfall patterns (30%)
2. Soil pH levels (25%)
3. Temperature variations (20%)
4. Fertilizer application (15%)
5. Soil moisture (10%)

---

## Database Schema

### YieldPrediction Model
```python
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
    fallback_used = models.BooleanField(default=False)
```

### Relationships
- **User to Predictions**: One-to-Many (User can have multiple predictions)
- **Location Mapping**: Predefined coordinates for 20 Kenyan locations

---

## Frontend Architecture

### Template Structure
- **Base Template**: `base.html` - Common layout and navigation
- **Dashboard**: `dashboard.html` - Main user interface
- **Landing Page**: `landing.html` - Public welcome page
- **Prediction Form**: `predict.html` - Input form for predictions

### Styling Framework
- **Bootstrap 5**: Responsive grid system and components
- **Custom CSS**: Farmer-themed green color palette
- **Font Awesome**: Agricultural and interface icons

### JavaScript Integration
- **Chart.js**: Data visualization for prediction trends
- **Bootstrap JS**: Interactive components
- **Custom Scripts**: Dashboard functionality and form validation

---

## Deployment

### Production Checklist
1. Set `DEBUG = False` in settings
2. Configure proper `SECRET_KEY`
3. Set up PostgreSQL database
4. Configure static file serving
5. Set up SSL certificates
6. Configure environment variables

### Heroku Deployment
```bash
# Install Heroku CLI
heroku login
heroku create cropaai-kenya

# Configure environment variables
heroku config:set API_KEY=your_api_key
heroku config:set SECRET_KEY=your_secret_key

# Deploy
git push heroku main
heroku run python manage.py migrate
```

### Docker Deployment
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

### AWS EC2 Deployment
1. Launch EC2 instance (Ubuntu 20.04+)
2. Install Python, pip, and dependencies
3. Configure Nginx reverse proxy
4. Set up SSL with Let's Encrypt
5. Configure systemd service for Django

---

## Development

### Code Style
- Follow PEP 8 Python style guidelines
- Use Django best practices
- Maintain consistent naming conventions
- Document all functions and classes

### Testing
```bash
# Run Django tests
python manage.py test

# Test specific app
python manage.py test yield_predictor

# Test model functionality
python test_model.py
```

### Adding New Crops
1. Update crop selection in `dashboard.html`
2. Create crop-specific prediction logic in `views.py`
3. Train new ML models for additional crops
4. Update database schema if needed

### Model Retraining
```bash
# Retrain existing model
python retrain_model.py

# Update model file in models/ directory
# Restart Django server to load new model
```

---

## Contributing

### How to Contribute
1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Commit your changes: `git commit -m 'Add feature'`
5. Push to the branch: `git push origin feature-name`
6. Submit a pull request

### Development Setup
1. Follow installation instructions
2. Install development dependencies: `pip install -r requirements-dev.txt`
3. Set up pre-commit hooks
4. Run tests before submitting PR

### Code Review Process
- All changes require code review
- Tests must pass
- Documentation must be updated
- Follow existing code style

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Contact & Support

- **Developer**: Moses Abwova
- **GitHub**: [mosetf](https://github.com/mosetf)
- **Project Repository**: [CropYieldPrediction](https://github.com/mosetf/CropYieldPrediction)

For technical support, please open an issue on GitHub or contact the development team.

---

**Last Updated**: October 2025  
**Version**: 1.0.0  
**Django Version**: 5.2.6  
**Python Version**: 3.11+
