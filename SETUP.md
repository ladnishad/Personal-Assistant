# LifeOS Backend Setup Guide

This guide will help you set up and run the LifeOS backend locally.

## Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose
- MongoDB Atlas account (or local MongoDB instance)
- OpenAI API key
- Google Cloud Console project (for Gmail/Calendar integration)
- Microsoft Azure AD app (for Outlook/Calendar integration)

## Setup Steps

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Personal-Assistant
```

### 2. Environment Configuration

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` and configure the following:

#### Required Settings

```env
# Secret Key (generate a strong random key)
SECRET_KEY=your-secret-key-here

# MongoDB
MONGODB_URL=mongodb://localhost:27017  # or MongoDB Atlas connection string
MONGODB_DB_NAME=lifeos

# OpenAI
OPENAI_API_KEY=your-openai-api-key
```

#### Optional Settings for Integrations

##### Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Gmail API and Google Calendar API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URI: `http://localhost:8000/api/v1/integrations/google/callback`
6. Copy credentials to `.env`:

```env
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

##### Microsoft OAuth Setup

1. Go to [Azure Portal](https://portal.azure.com/)
2. Register a new application in Azure AD
3. Add Microsoft Graph API permissions:
   - Mail.Read
   - Mail.ReadWrite
   - Calendars.Read
   - Calendars.ReadWrite
   - User.Read
4. Add redirect URI: `http://localhost:8000/api/v1/integrations/microsoft/callback`
5. Copy credentials to `.env`:

```env
MICROSOFT_CLIENT_ID=your-microsoft-client-id
MICROSOFT_CLIENT_SECRET=your-microsoft-client-secret
```

### 3. MongoDB Atlas Vector Search Setup

If using MongoDB Atlas for vector search:

1. Create a MongoDB Atlas cluster (M10 or higher)
2. Create a database named `lifeos`
3. Create a vector search index named `memory_vector_index` on the `memories` collection:

```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 1536,
      "similarity": "cosine"
    }
  ]
}
```

### 4. Running with Docker Compose (Recommended)

```bash
# Build and start all services
docker-compose up --build

# Run in detached mode
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

The API will be available at:
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- MongoDB: localhost:27017
- Redis: localhost:6379

### 5. Running Locally (Without Docker)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Testing the API

### 1. Check Health

```bash
curl http://localhost:8000/health
```

### 2. Register a User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123",
    "full_name": "John Doe"
  }'
```

### 3. Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }'
```

Save the `access_token` from the response.

### 4. Access Protected Endpoints

```bash
# Get current user info
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Create a task
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Review project proposal",
    "priority": "high",
    "due_date": "2024-12-31T17:00:00"
  }'

# Chat with AI agent
curl -X POST http://localhost:8000/api/v1/agent/chat \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What tasks do I have pending?"
  }'
```

## Interactive API Documentation

Visit http://localhost:8000/docs for Swagger UI interactive documentation where you can:
- View all available endpoints
- Test API calls directly from the browser
- See request/response schemas
- Authenticate and test protected endpoints

## Development

### Code Formatting

```bash
# Format code with black
black app/

# Lint with ruff
ruff check app/
```

### Running Tests

```bash
pytest
```

### Pre-commit Hooks

```bash
pre-commit install
pre-commit run --all-files
```

## Background Jobs

The following background jobs run automatically when scheduler is enabled:

- **Email Sync**: Every 15 minutes (configurable)
- **Calendar Sync**: Every 30 minutes (configurable)
- **Reminder Check**: Every 5 minutes (configurable)
- **Token Refresh**: Every 24 hours

Configure intervals in `.env`:

```env
EMAIL_SYNC_INTERVAL_MINUTES=15
CALENDAR_SYNC_INTERVAL_MINUTES=30
REMINDER_CHECK_INTERVAL_MINUTES=5
```

## Troubleshooting

### MongoDB Connection Issues

- Ensure MongoDB is running: `docker-compose ps`
- Check connection string in `.env`
- For Atlas, ensure IP whitelist includes your IP

### OAuth Integration Issues

- Verify redirect URIs match exactly
- Check OAuth consent screen configuration
- Ensure required APIs/permissions are enabled

### OpenAI API Issues

- Verify API key is correct
- Check OpenAI account has credits
- Ensure model names are correct in `.env`

## Next Steps

1. Connect your email account via `/integrations/google/connect` or `/integrations/microsoft/connect`
2. Sync your emails using `/emails/sync`
3. Chat with the AI agent to manage your tasks and get insights
4. Build a frontend application to interact with the API

## Support

For issues and questions, please open a GitHub issue.
