# CropAI Backend API Documentation

**Version:** 1.0.0  
**Base URL:** `http://localhost:8000` (dev) or your deployment URL  
**API Prefix:** `/api/v1/`  
**Swagger UI:** `http://localhost:8000/api/schema/swagger-ui/`  
**ReDoc:** `http://localhost:8000/api/schema/redoc/`

---

## Table of Contents

1. [Authentication](#authentication)
2. [Endpoints Overview](#endpoints-overview)
3. [Authentication Endpoints](#authentication-endpoints)
4. [Yield Prediction Endpoints](#yield-prediction-endpoints)
5. [Crop Models Endpoints](#crop-models-endpoints)
6. [Error Handling](#error-handling)
7. [Rate Limiting](#rate-limiting)
8. [Examples](#examples)

---

## Authentication

All API endpoints (except registration, login, and crop models list) require JWT authentication.

### Token Types

- **Access Token**: Short-lived (30 minutes), sent in response body for each request
- **Refresh Token**: Long-lived (1 day or 30 days with remember_me), stored in httpOnly cookie

### How to Authenticate

1. Obtain tokens via `/api/v1/auth/login/`
2. Use access token in `Authorization` header: `Authorization: Bearer <access_token>`
3. When access token expires, refresh it using `/api/v1/auth/refresh/`

### Security Features

- JWT tokens signed with Django SECRET_KEY
- Refresh tokens stored in httpOnly cookies (JavaScript cannot access)
- Token rotation on refresh (old token blacklisted)
- Device tracking: each session stores browser, OS, IP, device info
- Multi-device sessions: same user can be logged in on multiple devices simultaneously
- Session revocation: sign out specific devices or all other sessions

---

## Endpoints Overview

| Category | Method | Endpoint | Auth Required | Purpose |
|----------|--------|----------|----------------|---------|
| **Authentication** | POST | `/auth/register/` | No | User registration |
| | POST | `/auth/login/` | No | User login |
| | POST | `/auth/logout/` | Yes | User logout |
| | POST | `/auth/refresh/` | No | Refresh access token |
| | GET | `/auth/user/` | Yes | Get current user info |
| | GET/DELETE | `/auth/sessions/` | Yes | Manage user sessions |
| **Yield Prediction** | GET | `/predictions/` | Yes | List user's predictions |
| | POST | `/predictions/` | Yes | Create new prediction |
| | GET | `/predictions/{id}/` | Yes | Get specific prediction |
| | DELETE | `/predictions/{id}/` | Yes | Delete prediction |
| **Crop Models** | GET | `/crops/` | No | List available crop models |
| | GET | `/crops/{id}/` | No | Get crop model details |

---

## Authentication Endpoints

### 1. User Registration

**Endpoint:** `POST /api/v1/auth/register/`

**Description:** Register a new user account with email and password. Returns JWT tokens for immediate authentication.

**Request Body:**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "secure_password_123",
  "password_confirm": "secure_password_123",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| username | string | Yes | Username for login (150 chars max, unique) |
| email | string | Yes | Valid email address (unique) |
| password | string | Yes | Password (minimum 8 characters) |
| password_confirm | string | Yes | Must match password field |
| first_name | string | No | First name (optional) |
| last_name | string | No | Last name (optional) |

**Success Response (201 Created):**
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJleHAiOjE3MDUzMjM0MDB9...",
  "user": {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe"
  }
}
```

**Cookies Set:**
- `cropai_refresh`: Refresh token (httpOnly, secure)

**Error Responses:**
- **400 Bad Request**: Username/email already exists, passwords don't match, or validation error
  ```json
  {
    "username": ["Username already exists"],
    "email": ["Email already exists"],
    "password_confirm": ["Passwords do not match"]
  }
  ```

---

### 2. User Login

**Endpoint:** `POST /api/v1/auth/login/`

**Description:** Authenticate user with credentials and return JWT tokens.

**Request Body:**
```json
{
  "username": "john_doe",
  "password": "secure_password",
  "remember_me": false
}
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| username | string | Yes | Username for login |
| password | string | Yes | User password |
| remember_me | boolean | No | If true, refresh token expires in 30 days; otherwise 1 day |

**Success Response (200):**
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJleHAiOjE3MDUzMjM0MDB9...",
  "user": {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com"
  }
}
```

**Cookies Set:**
- `cropai_refresh`: Refresh token (httpOnly, secure)

**Error Responses:**
- **401 Unauthorized**: Invalid credentials
- **400 Bad Request**: Missing required fields

---

### 2. User Logout

**Endpoint:** `POST /api/v1/auth/logout/`

**Description:** Logout current user. Blacklists refresh token and deletes session record.

**Request Headers:**
```
Authorization: Bearer <access_token>
```

**Success Response (200):**
```json
{
  "detail": "Logged out successfully"
}
```

**Cookies Deleted:**
- `cropai_refresh`

**Error Responses:**
- **401 Unauthorized**: Not authenticated

---

### 3. Refresh Access Token

**Endpoint:** `POST /api/v1/auth/refresh/`

**Description:** Refresh expired access token using refresh token from cookie. Implements token rotation for security.

**Request:**
- No body required
- Refresh token must be in httpOnly cookie (`cropai_refresh`)

**Success Response (200):**
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJleHAiOjE3MDUzMjM0MDB9..."
}
```

**Cookies Updated:**
- `cropai_refresh`: New refresh token (old one blacklisted)

**Error Responses:**
- **401 Unauthorized**: Invalid or missing refresh token

---

### 4. Get Current User

**Endpoint:** `GET /api/v1/auth/user/`

**Description:** Retrieve current authenticated user information.

**Request Headers:**
```
Authorization: Bearer <access_token>
```

**Success Response (200):**
```json
{
  "id": 1,
  "username": "john_doe",
  "email": "john@example.com"
}
```

**Error Responses:**
- **401 Unauthorized**: Not authenticated

---

### 5. Manage User Sessions

**Endpoint:** `GET /api/v1/auth/sessions/` or `DELETE /api/v1/auth/sessions/`

**Description:** 
- GET: List all active sessions for current user
- DELETE: Revoke sessions (all others or specific by id)

**Request Headers:**
```
Authorization: Bearer <access_token>
```

#### GET - List Sessions

**Success Response (200):**
```json
[
  {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "device_name": "iPhone 14",
    "device_type": "smartphone",
    "browser": "Safari 16.0",
    "os": "iOS 16.1",
    "ip_address": "192.168.1.1",
    "last_active": "2024-01-15T10:30:00Z",
    "is_current": true
  },
  {
    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "device_name": "MacBook Pro",
    "device_type": "desktop",
    "browser": "Chrome 120.0",
    "os": "macOS 14.2",
    "ip_address": "192.168.1.2",
    "last_active": "2024-01-15T09:15:00Z",
    "is_current": false
  }
]
```

#### DELETE - Revoke Sessions

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | string | No | Session ID to revoke. If omitted, revokes all other sessions |

**Example:**
- `DELETE /api/v1/auth/sessions/` - Revoke all other sessions (keep current)
- `DELETE /api/v1/auth/sessions/?id=a1b2c3d4-e5f6-7890-abcd-ef1234567890` - Revoke specific session

**Success Response (200):**
```json
{
  "detail": "Session(s) revoked"
}
```

**Error Responses:**
- **401 Unauthorized**: Not authenticated
- **404 Not Found**: Session ID not found

---

## Yield Prediction Endpoints

### 1. List User Predictions

**Endpoint:** `GET /api/v1/predictions/`

**Description:** Get paginated list of user's yield predictions.

**Request Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| page | integer | Page number (default: 1) |
| limit | integer | Results per page (default: 10) |

**Success Response (200):**
```json
{
  "count": 45,
  "next": "http://localhost:8000/api/v1/predictions/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "crop": "maize",
      "location": "Nakuru",
      "region": "Rift Valley",
      "planting_date": "2024-01-10",
      "predicted_yield": 4.5,
      "yield_low": 3.8,
      "yield_high": 5.2,
      "net_profit": 125000,
      "rainfall": 450,
      "temperature": 23.5,
      "humidity": 65,
      "harvest_window": "May 15 - May 25",
      "risk_level": "low",
      "ai_recommendations": "Excellent conditions for maize...",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

**Error Responses:**
- **401 Unauthorized**: Not authenticated

---

### 2. Create New Prediction

**Endpoint:** `POST /api/v1/predictions/`

**Description:** Create new crop yield prediction with ML model and weather data.

**Request Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "crop": "maize",
  "location": "Nakuru",
  "soil_ph": 6.5,
  "soil_moisture": 45,
  "organic_carbon": 2.1,
  "fertilizer_kg_ha": 120,
  "planting_date": "2024-01-10"
}
```

**Parameters:**
| Parameter | Type | Required | Range | Description |
|-----------|------|----------|-------|-------------|
| crop | string | Yes | See Crops List | Crop type (maize, wheat, beans, etc) |
| location | string | Yes | See Crops List | Location (Nakuru, Mombasa, etc) |
| soil_ph | float | Yes | 4.5-8.5 | Soil pH level |
| soil_moisture | float | Yes | 0-100 | Soil moisture percentage |
| organic_carbon | float | Yes | 0-10 | Organic carbon (g/kg) |
| fertilizer_kg_ha | float | Yes | 0-500 | Fertilizer application (kg/ha) |
| planting_date | date | Yes | - | Planting date (YYYY-MM-DD) |

**Success Response (201):**
```json
{
  "id": 1,
  "crop": "maize",
  "location": "Nakuru",
  "region": "Rift Valley",
  "planting_date": "2024-01-10",
  "predicted_yield": 4.5,
  "yield_low": 3.8,
  "yield_high": 5.2,
  "net_profit": 125000,
  "rainfall": 450,
  "temperature": 23.5,
  "humidity": 65,
  "soil_ph": 6.5,
  "soil_moisture": 45,
  "organic_carbon": 2.1,
  "fertilizer_kg_ha": 120,
  "harvest_window": "May 15 - May 25",
  "risk_level": "low",
  "risk_reason": "Optimal conditions",
  "ai_recommendations": "Excellent conditions for maize cultivation. Ensure timely irrigation during flowering.",
  "model_version": "v1.0",
  "fallback_used": false,
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Error Responses:**
- **400 Bad Request**: Invalid crop, location, or soil data
- **401 Unauthorized**: Not authenticated
- **422 Unprocessable Entity**: Prediction service error

---

### 3. Get Specific Prediction

**Endpoint:** `GET /api/v1/predictions/{id}/`

**Description:** Retrieve details of a specific prediction.

**Request Headers:**
```
Authorization: Bearer <access_token>
```

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| id | integer | Prediction ID |

**Success Response (200):**
```json
{
  "id": 1,
  "crop": "maize",
  "location": "Nakuru",
  "region": "Rift Valley",
  "planting_date": "2024-01-10",
  "predicted_yield": 4.5,
  "yield_low": 3.8,
  "yield_high": 5.2,
  "net_profit": 125000,
  "rainfall": 450,
  "temperature": 23.5,
  "humidity": 65,
  "soil_ph": 6.5,
  "soil_moisture": 45,
  "organic_carbon": 2.1,
  "fertilizer_kg_ha": 120,
  "harvest_window": "May 15 - May 25",
  "risk_level": "low",
  "risk_reason": "Optimal conditions",
  "ai_recommendations": "Excellent conditions for maize cultivation...",
  "model_version": "v1.0",
  "fallback_used": false,
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Error Responses:**
- **401 Unauthorized**: Not authenticated
- **404 Not Found**: Prediction not found

---

### 4. Delete Prediction

**Endpoint:** `DELETE /api/v1/predictions/{id}/`

**Description:** Delete a specific prediction.

**Request Headers:**
```
Authorization: Bearer <access_token>
```

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| id | integer | Prediction ID |

**Success Response (204):**
- No content

**Error Responses:**
- **401 Unauthorized**: Not authenticated
- **404 Not Found**: Prediction not found

---

## Crop Models Endpoints

### 1. List Available Crop Models

**Endpoint:** `GET /api/v1/crops/`

**Description:** Get list of available crop models for prediction.

**Success Response (200):**
```json
{
  "count": 9,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Maize Prediction Model",
      "code": "maize",
      "description": "ML model for maize yield prediction in East Africa",
      "version": "1.0",
      "is_active": true
    },
    {
      "id": 2,
      "name": "Wheat Prediction Model",
      "code": "wheat",
      "description": "ML model for wheat yield prediction",
      "version": "1.0",
      "is_active": true
    }
  ]
}
```

**Error Responses:**
- None (publicly accessible)

---

### 2. Get Crop Model Details

**Endpoint:** `GET /api/v1/crops/{id}/`

**Description:** Retrieve details of a specific crop model.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| id | integer | Crop model ID |

**Success Response (200):**
```json
{
  "id": 1,
  "name": "Maize Prediction Model",
  "code": "maize",
  "description": "ML model for maize yield prediction in East Africa",
  "version": "1.0",
  "is_active": true
}
```

**Error Responses:**
- **404 Not Found**: Crop model not found

---

## Error Handling

All errors return a consistent JSON response with status code and error details.

### Error Response Format

```json
{
  "detail": "Error message description",
  "code": "error_code"
}
```

### Common HTTP Status Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | OK | Successful GET, POST, PATCH |
| 201 | Created | Successful POST (resource created) |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Invalid input data |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Authenticated but not authorized |
| 404 | Not Found | Resource doesn't exist |
| 422 | Unprocessable Entity | Valid syntax but semantic error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |

### Example Error Responses

**Invalid Credentials (401):**
```json
{
  "detail": "Invalid credentials"
}
```

**Missing Required Field (400):**
```json
{
  "crop": ["This field is required."],
  "soil_ph": ["This field is required."]
}
```

**Not Found (404):**
```json
{
  "detail": "Not found."
}
```

---

## Rate Limiting

API requests are rate-limited to prevent abuse:

| User Type | Limit | Window |
|-----------|-------|--------|
| Authenticated | 1000/hour | Per hour |
| Anonymous | 100/hour | Per hour |
| Login Endpoint | 15/minute | Per minute |

**Response Headers (when rate limit active):**
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1705324800
```

When limit exceeded: **429 Too Many Requests**

---

## Examples

### Example 1: Complete Login & Prediction Flow

```bash
# 1. Login
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "secure_password",
    "remember_me": false
  }' \
  -c cookies.txt

# Response:
# {
#   "access": "eyJhbGciOiJIUzI1NiIs...",
#   "user": {...}
# }

# 2. Create Prediction (using access token)
curl -X POST http://localhost:8000/api/v1/predictions/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -d '{
    "crop": "maize",
    "location": "Nakuru",
    "soil_ph": 6.5,
    "soil_moisture": 45,
    "organic_carbon": 2.1,
    "fertilizer_kg_ha": 120,
    "planting_date": "2024-01-10"
  }'

# 3. List Predictions
curl http://localhost:8000/api/v1/predictions/ \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."

# 4. Refresh Token (when access expires)
curl -X POST http://localhost:8000/api/v1/auth/refresh/ \
  -b cookies.txt

# 5. Logout
curl -X POST http://localhost:8000/api/v1/auth/logout/ \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -b cookies.txt
```

### Example 2: Session Management

```bash
# Get all sessions
curl http://localhost:8000/api/v1/auth/sessions/ \
  -H "Authorization: Bearer <access_token>"

# Revoke all other sessions (sign out everywhere else)
curl -X DELETE http://localhost:8000/api/v1/auth/sessions/ \
  -H "Authorization: Bearer <access_token>"

# Revoke specific session
curl -X DELETE "http://localhost:8000/api/v1/auth/sessions/?id=a1b2c3d4-..." \
  -H "Authorization: Bearer <access_token>"
```

### Example 3: JavaScript/Fetch

```javascript
// Login
const response = await fetch('http://localhost:8000/api/v1/auth/login/', {
  method: 'POST',
  credentials: 'include', // Include cookies
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'john_doe',
    password: 'secure_password',
    remember_me: false
  })
});

const { access, user } = await response.json();

// Make prediction
const predictionResponse = await fetch('http://localhost:8000/api/v1/predictions/', {
  method: 'POST',
  credentials: 'include',
  headers: {
    'Authorization': `Bearer ${access}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    crop: 'maize',
    location: 'Nakuru',
    soil_ph: 6.5,
    soil_moisture: 45,
    organic_carbon: 2.1,
    fertilizer_kg_ha: 120,
    planting_date: '2024-01-10'
  })
});

const prediction = await predictionResponse.json();
console.log('Predicted yield:', prediction.predicted_yield, 'tonnes/ha');

// Refresh token when needed
const refreshResponse = await fetch('http://localhost:8000/api/v1/auth/refresh/', {
  method: 'POST',
  credentials: 'include'
});

const { access: newAccessToken } = await refreshResponse.json();
// Use newAccessToken for subsequent requests
```

---

## Available Crop Types & Locations

### Supported Crops
- maize
- wheat
- beans
- rice
- sunflower
- sorghum
- cassava
- potato
- tomato

### Supported Locations
- Nakuru
- Mombasa
- Eldoret
- Embu
- Nyeri
- Uasin Gishu
- Kericho
- Kisumu
- And more...

(See `/api/v1/crops/` endpoint for complete list)

---

## Support & Documentation

- **Swagger UI**: http://localhost:8000/api/schema/swagger-ui/
- **ReDoc**: http://localhost:8000/api/schema/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/
- **Django Admin**: http://localhost:8000/admin/

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2024-01-15 | Initial release with authentication, predictions, and session management |

