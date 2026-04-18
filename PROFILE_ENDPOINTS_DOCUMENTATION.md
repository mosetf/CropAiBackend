# UserProfile Endpoints Documentation

## Overview

The CropAI backend now includes comprehensive user profile management endpoints that allow users to:
- View their complete profile and user details
- Update personal information (name, phone, bio)
- Update location and farm information
- Track profile completion status

All profile endpoints require **Bearer token authentication**.

---

## Endpoints

### 1. Get User Profile
**GET** `/api/v1/auth/profile/`

Returns complete user profile with personal details and farm information for UI display.

**Authentication:** Required (Bearer Token)

**Request:**
```bash
curl -H "Authorization: Bearer {access_token}" \
  https://api.cropai.com/api/v1/auth/profile/
```

**Response (200 OK):**
```json
{
  "id": 1,
  "email": "farmer@cropai.com",
  "first_name": "John",
  "last_name": "Kariuki",
  "is_active": true,
  "date_joined": "2024-01-15T10:30:00Z",
  "profile": {
    "id": 1,
    "phone_number": "+254712345678",
    "date_of_birth": "1990-05-20",
    "gender": "M",
    "bio": "Coffee farmer in the highlands",
    "avatar": "/media/avatars/farmer1.jpg",
    "location": "Nyeri, Kenya",
    "country": "Kenya",
    "latitude": "-0.4218",
    "longitude": "36.9529",
    "organization": "Nyeri Farmers Cooperative",
    "farm_name": "Highland Coffee Estate",
    "farm_size": "15.5",
    "primary_crops": "Coffee, Avocado, Maize",
    "email_verified": false,
    "phone_verified": false,
    "profile_completed": true,
    "user_name": "John Kariuki",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-16T14:22:00Z"
  }
}
```

---

### 2. Update User Profile (Extended)
**PATCH** `/api/v1/auth/profile/` or **PUT** `/api/v1/auth/profile/`

Update user profile information including personal details, location, and farm information.

**Authentication:** Required (Bearer Token)

**Request Body (all fields optional):**
```json
{
  "phone_number": "+254712345678",
  "date_of_birth": "1990-05-20",
  "gender": "M",
  "bio": "Innovative farmer using modern techniques",
  "location": "Nyeri, Kenya",
  "country": "Kenya",
  "latitude": "-0.4218",
  "longitude": "36.9529",
  "organization": "Nyeri Farmers Cooperative",
  "farm_name": "Highland Coffee Estate",
  "farm_size": "15.5",
  "primary_crops": "Coffee, Avocado, Maize"
}
```

**Request Example:**
```bash
curl -X PATCH \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+254712345678",
    "farm_name": "Green Valley Farm",
    "primary_crops": "Coffee, Avocado"
  }' \
  https://api.cropai.com/api/v1/auth/profile/
```

**Response (200 OK):**
```json
{
  "id": 1,
  "phone_number": "+254712345678",
  "date_of_birth": "1990-05-20",
  "gender": "M",
  "bio": "Innovative farmer using modern techniques",
  "avatar": null,
  "location": "Nyeri, Kenya",
  "country": "Kenya",
  "latitude": "-0.4218",
  "longitude": "36.9529",
  "organization": "Nyeri Farmers Cooperative",
  "farm_name": "Green Valley Farm",
  "farm_size": "15.5",
  "primary_crops": "Coffee, Avocado",
  "email_verified": false,
  "phone_verified": false,
  "profile_completed": false,
  "user_name": "John Kariuki",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-16T14:22:00Z"
}
```

**Error Response (400 Bad Request):**
```json
{
  "field_name": ["Error message"]
}
```

---

### 3. Update User Basic Info
**PATCH** `/api/v1/auth/user/basic/`

Update user's first name and last name.

**Authentication:** Required (Bearer Token)

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Kariuki"
}
```

**Request Example:**
```bash
curl -X PATCH \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Kariuki"
  }' \
  https://api.cropai.com/api/v1/auth/user/basic/
```

**Response (200 OK):**
```json
{
  "id": 1,
  "email": "farmer@cropai.com",
  "first_name": "John",
  "last_name": "Kariuki"
}
```

---

## UserProfile Fields Reference

| Field | Type | Description | Editable |
|-------|------|-------------|----------|
| id | Integer | Profile unique identifier | ❌ No |
| user | Foreign Key | Reference to CustomUser | ❌ No |
| phone_number | String (20) | User's phone number | ✅ Yes |
| date_of_birth | Date | User's date of birth | ✅ Yes |
| gender | Choice | Gender (M/F/O) | ✅ Yes |
| bio | Text | User biography | ✅ Yes |
| avatar | File | User's profile picture | ✅ Yes |
| location | String (255) | City/region location | ✅ Yes |
| country | String (100) | Country name | ✅ Yes |
| latitude | Decimal | Geographic latitude | ✅ Yes |
| longitude | Decimal | Geographic longitude | ✅ Yes |
| organization | String (255) | Organization/cooperative name | ✅ Yes |
| farm_name | String (255) | Primary farm name | ✅ Yes |
| farm_size | Decimal | Farm size in acres/hectares | ✅ Yes |
| primary_crops | Text | Main crops grown (comma-separated) | ✅ Yes |
| email_verified | Boolean | Email verification status | ❌ No (system only) |
| phone_verified | Boolean | Phone verification status | ❌ No (system only) |
| profile_completed | Boolean | Profile completion flag | ❌ No (auto-calculated) |
| created_at | DateTime | Profile creation timestamp | ❌ No |
| updated_at | DateTime | Last profile update timestamp | ❌ No |

---

## User-Profile Relationship

Each authenticated user has exactly one associated UserProfile, automatically created when the user registers. 

**Key Points:**
- UserProfile is created via Django signal (post_save) immediately after user creation
- No additional API call needed to create the profile
- Profile persists for the lifetime of the user account
- Deleting a user cascades to delete the profile

---

## Common Use Cases

### 1. Complete Profile After Registration
```bash
# 1. Register user
curl -X POST https://api.cropai.com/api/v1/auth/register/ \
  -d '{"email":"farmer@cropai.com", "password":"secure123", "password_confirm":"secure123"}'

# 2. Login
curl -X POST https://api.cropai.com/api/v1/auth/login/ \
  -d '{"email":"farmer@cropai.com", "password":"secure123"}'

# 3. Update profile with farm details
curl -X PATCH https://api.cropai.com/api/v1/auth/profile/ \
  -H "Authorization: Bearer {access_token}" \
  -d '{
    "first_name": "John",
    "phone_number": "+254712345678",
    "farm_name": "Highland Farm",
    "primary_crops": "Coffee"
  }'
```

### 2. Display User Profile in UI
```javascript
// Fetch user profile
const response = await fetch('/api/v1/auth/profile/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const userData = await response.json();

// Display user details
console.log(`Welcome ${userData.first_name} ${userData.last_name}!`);
console.log(`Farm: ${userData.profile.farm_name}`);
console.log(`Location: ${userData.profile.location}`);
```

### 3. Update Farm Information
```bash
curl -X PATCH https://api.cropai.com/api/v1/auth/profile/ \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "farm_size": "25.5",
    "primary_crops": "Maize, Beans, Potatoes",
    "location": "Nakuru, Kenya",
    "country": "Kenya"
  }'
```

---

## Error Codes

| Status | Code | Description |
|--------|------|-------------|
| 200 | OK | Request successful |
| 400 | Bad Request | Invalid input data |
| 401 | Unauthorized | Missing or invalid authentication token |
| 403 | Forbidden | User not authorized to access this resource |
| 404 | Not Found | Endpoint or resource not found |
| 405 | Method Not Allowed | HTTP method not supported for this endpoint |
| 500 | Internal Server Error | Server error occurred |

---

## Authentication

All profile endpoints use **Bearer Token Authentication** with JWT tokens.

**Token Format:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Token Lifespan:**
- Access token: 1 hour
- Refresh token: 7 days
- Auto-refresh enabled

---

## Implementation Notes

### Auto-Profile Creation
When a user registers, a UserProfile is automatically created via Django signals:
```python
# Automatically triggered on user creation
@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
```

### Nested Profile Data
The GET /profile/ endpoint returns both user data and nested profile data for convenience in UI rendering without multiple API calls.

### Field Validation
- Phone number: 20 character limit, any format accepted
- Farm size: Stored as decimal, interpret as acres or hectares as needed
- Coordinates: Stored as decimal (-90 to 90 for latitude, -180 to 180 for longitude)
- Text fields: No length limit, but practical UI limits recommended

### Profile Completion
The `profile_completed` field is calculated based on which profile fields are filled:
- Incomplete: Only minimal fields set
- Complete: Farm name, location, crops, and phone number set

---

## Swagger/OpenAPI

All profile endpoints are automatically documented in the Swagger UI:
```
GET /api/schema/swagger-ui/
```

Profile endpoints appear under the **User Profile** tag in the API documentation.

---

## Example: React Component

```jsx
import { useEffect, useState } from 'react';

export function UserProfile() {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchProfile = async () => {
      const token = localStorage.getItem('access_token');
      const res = await fetch('/api/v1/auth/profile/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      setProfile(data);
      setLoading(false);
    };
    fetchProfile();
  }, []);

  const handleUpdate = async (updates) => {
    const token = localStorage.getItem('access_token');
    const res = await fetch('/api/v1/auth/profile/', {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(updates)
    });
    const updated = await res.json();
    setProfile(prev => ({ ...prev, profile: updated }));
  };

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      <h1>{profile.first_name} {profile.last_name}</h1>
      <p>Farm: {profile.profile.farm_name}</p>
      <p>Location: {profile.profile.location}</p>
      <button onClick={() => handleUpdate({ farm_name: 'New Farm' })}>
        Update Farm
      </button>
    </div>
  );
}
```

---

## Integration with Frontend

### Setup
1. Ensure JWT token is stored securely (httpOnly cookie or secure localStorage)
2. Include token in all authenticated requests
3. Handle 401 responses by refreshing token or redirecting to login

### Recommended Flow
1. User registers → Profile auto-created
2. User completes profile → Update via PATCH /profile/
3. User views profile → Fetch via GET /profile/
4. User edits details → Update via PATCH /profile/ or PATCH /user/basic/

---

## Future Enhancements

Potential additions to profile system:
- Email verification endpoint
- Phone verification endpoint
- Profile avatar upload with image processing
- Profile completion percentage calculation
- User preferences (notifications, privacy settings)
- Multiple farm profiles per user
- Farm history/rotation tracking
