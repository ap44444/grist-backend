# Grist Backend

A production-ready Django REST API for personalized nutrition planning, AI-powered meal generation, and dietitian consultation management.

## Overview

Grist is a health and nutrition platform that connects patients with dietitians. It features AI-generated meal plans tailored to user preferences, ingredient substitution with local Sri Lankan alternatives, grocery cart management, appointment scheduling, and comprehensive health metric tracking.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | Django 6.0.3, Django REST Framework 3.16.1 |
| Authentication | JWT (SimpleJWT), Google OAuth2 (django-allauth) |
| Database | PostgreSQL + pgvector (ingredient embeddings) |
| AI/ML | OpenAI ChatGPT, Serper API (recipe images) |
| Media Storage | Cloudinary |
| Deployment | Docker, Gunicorn, Railway |
| API Docs | drf-spectacular (Swagger/OpenAPI) |

## Features

- **AI Meal Planning** — GPT-generated weekly meal plans respecting allergies, dietary preferences, and calorie targets
- **Ingredient Intelligence** — Local Sri Lankan ingredient substitutions with cost-saving ratios and vector similarity search (pgvector)
- **Nutritional Calculations** — BMI, BMR (Mifflin-St Jeor), and TDEE with activity multipliers
- **Dietitian Portal** — Patient management, notes, appointment scheduling, consultation requests
- **Water & Meal Tracking** — Daily progress tracking with customizable water targets
- **Grocery Cart** — Separate from meal plans, supports custom items and purchase tracking
- **Review System** — Dual-metric ratings (overall + call quality) with tag-based feedback
- **Role-Based Access** — Separate patient and dietitian dashboards and permissions

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL with pgvector extension
- Docker (optional)

### Environment Variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your-django-secret-key
DATABASE_URL=postgresql://user:password@localhost:5432/grist
OPENAI_API_KEY=your-openai-key
SERPER_API_KEY=your-serper-key
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-cloudinary-api-key
CLOUDINARY_API_SECRET=your-cloudinary-api-secret
```

### Local Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Docker

```bash
docker build -t grist-backend .
docker run -p 8080:8080 --env-file .env grist-backend
```

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/register/` | Register (patient or dietitian) |
| POST | `/api/login/` | Login, returns JWT tokens |
| POST | `/api/logout/` | Logout |
| POST | `/api/token/refresh/` | Refresh access token |
| POST | `/api/auth/google/` | Google OAuth2 login |

### User Profile
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/profile/` | Get profile |
| PUT | `/api/profile/update/` | Update profile |
| POST | `/api/profile/calculate-targets/` | Calculate BMR/TDEE targets |
| POST | `/api/profile/upload-picture/` | Upload profile picture |

### Meal Planning
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/plan/today/` | Today's meal schedule |
| GET | `/api/meals/<id>/recipe/` | Recipe details for a meal slot |
| GET | `/api/recipe/request/` | Generate AI meal on demand |
| POST | `/api/meals/<id>/substitute/` | Request ingredient substitution |
| POST | `/api/recipe/<id>/favorite/` | Toggle favorite recipe |

### Daily Tracking
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/track/water/` | Log water intake |
| POST | `/api/track/water/remove/` | Remove water log |
| POST | `/api/track/meal/<id>/` | Mark meal as consumed |

### Dashboard & Stats
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/today/` | Patient dashboard |
| GET | `/api/stats/progress/` | Weekly progress metrics |
| GET | `/api/dietitian/dashboard/today/` | Dietitian dashboard |

### Grocery Cart
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/cart/` | Get cart |
| POST | `/api/cart/add/` | Add item |
| PUT | `/api/cart/item/<id>/update/` | Update item |
| DELETE | `/api/cart/item/<id>/delete/` | Remove item |

### Appointments
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/appointments/` | List or create appointments |
| GET | `/api/dietitian/appointments/` | Dietitian's appointments |
| GET | `/api/dietitian/clients/` | Dietitian's active clients |

### Reviews
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/patient/reviews/submit/` | Submit review |
| PUT | `/api/patient/reviews/<id>/update/` | Update review |
| DELETE | `/api/patient/reviews/<id>/delete/` | Delete review |
| GET | `/api/dietitians/<id>/reviews/` | Get dietitian's reviews |

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health/` | Health check |
| GET | `/api/docs/` | Swagger UI |
| GET | `/api/schema/` | OpenAPI schema |

## Project Structure

```
grist-backend/
├── core/
│   ├── models.py          # All data models
│   ├── serializers.py     # DRF serializers
│   ├── views.py           # API views
│   ├── urls.py            # URL routing
│   ├── ai_service.py      # OpenAI meal generation
│   ├── permissions.py     # Custom permission classes
│   └── migrations/        # Database migrations
├── grist/
│   ├── settings.py        # Django configuration
│   └── urls.py            # Root URL config
├── Dockerfile
├── Procfile               # Railway deployment
└── requirements.txt
```

## Key Models

- **CustomUser / UserProfile** — Extended user with health metrics, dietary preferences, goals, allergies
- **Ingredient** — Nutritional data, LKR pricing, pgvector embeddings for AI similarity
- **Recipe / RecipeIngredient** — AI-generated or manual recipes with macro breakdown
- **WeeklyPlan / DailyPlan / MealSlot** — Hierarchical meal planning structure
- **Appointment** — Patient ↔ Dietitian scheduling with video/in-person support
- **DietitianReview** — Dual-metric rating system with JSON tags
- **GroceryCart / GroceryCartItem** — Shopping management

## Deployment

The app is configured for Railway deployment via the `Procfile`:

```
web: python manage.py migrate && gunicorn grist.wsgi --bind 0.0.0.0:$PORT
```

CORS is configured to allow `grist-diet-app-production.up.railway.app` and localhost origins.

## Admin

Django admin is available at `/admin/`. Models support bulk CSV import/export via `django-import-export`.
