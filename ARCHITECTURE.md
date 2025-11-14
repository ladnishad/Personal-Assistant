# LifeOS Backend Architecture

## Overview

LifeOS is an AI-powered personal life assistant backend built with FastAPI, MongoDB, and OpenAI. It provides a comprehensive API for managing emails, calendars, tasks, and long-term memory with an intelligent AI agent orchestrator.

## Technology Stack

- **Framework**: FastAPI (Python 3.11+)
- **Database**: MongoDB with Beanie ODM
- **Vector Search**: MongoDB Atlas Vector Search
- **Caching**: Redis (optional)
- **Task Queue**: APScheduler
- **LLM**: OpenAI GPT-4 with function calling
- **Authentication**: JWT + OAuth 2.0
- **Container**: Docker + Docker Compose

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Applications                     │
│              (iOS, Web, Browser Extension)                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐  │
│  │   Auth   │  Email   │ Calendar │  Tasks   │  Memory  │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Agent Orchestrator (LLM)                 │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Integrations (Gmail, Outlook, etc.)           │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │ MongoDB │    │  Redis  │    │ OpenAI  │
    │ + Vector│    │ (Cache) │    │   API   │
    └─────────┘    └─────────┘    └─────────┘
```

## Module Architecture

### 1. Auth Module (`app/auth/`)

**Purpose**: User authentication and authorization

**Components**:
- `models.py`: User document model
- `schemas.py`: Request/response schemas
- `utils.py`: JWT generation, password hashing
- `dependencies.py`: Auth middleware
- `service.py`: Business logic
- `router.py`: API endpoints

**Features**:
- Email/password registration
- JWT access + refresh tokens
- Password change
- Protected route dependencies

### 2. Integrations Module (`app/integrations/`)

**Purpose**: OAuth connections to external services

**Components**:
- `models.py`: Integration document model
- `schemas.py`: Request/response schemas
- `google_service.py`: Google OAuth & API
- `microsoft_service.py`: Microsoft OAuth & API
- `router.py`: API endpoints

**Features**:
- Google OAuth (Gmail, Calendar)
- Microsoft OAuth (Outlook, Calendar)
- Token management and refresh
- Automatic token refresh before expiry

### 3. Email Module (`app/emails/`)

**Purpose**: Email ingestion, storage, and retrieval

**Components**:
- `models.py`: Email document model
- `schemas.py`: Request/response schemas
- `gmail_service.py`: Gmail API integration
- `service.py`: Email sync logic
- `router.py`: API endpoints

**Features**:
- Email sync from Gmail/Outlook
- Email search and filtering
- Read/unread, star/unstar
- Attachment tracking
- Entity extraction (planned)

### 4. Calendar Module (`app/calendar/`)

**Purpose**: Calendar event sync and management

**Components**:
- `models.py`: Calendar event model
- `schemas.py`: Request/response schemas
- `service.py`: Calendar sync logic
- `router.py`: API endpoints

**Features**:
- Calendar event sync
- Event filtering by date
- Recurring event support
- Meeting link tracking

### 5. Tasks Module (`app/tasks/`)

**Purpose**: Task and reminder management

**Components**:
- `models.py`: Task document model
- `schemas.py`: Request/response schemas
- `service.py`: Task CRUD operations
- `router.py`: API endpoints

**Features**:
- Task creation, update, delete
- Priority and status management
- Due dates and reminders
- Task categorization and tagging
- Source tracking (from email, calendar, etc.)

### 6. Memory Module (`app/memory/`)

**Purpose**: Long-term memory with semantic search

**Components**:
- `models.py`: Memory document model
- `schemas.py`: Request/response schemas
- `service.py`: Memory operations + embeddings
- `router.py`: API endpoints

**Features**:
- Store facts, preferences, routines
- Vector embeddings (OpenAI text-embedding-3-small)
- Semantic search with MongoDB Atlas Vector Search
- Memory types: fact, preference, routine, relationship, context
- Confidence scoring and importance weighting

### 7. Agent Module (`app/agent/`)

**Purpose**: AI orchestrator with LLM and tool calling

**Components**:
- `schemas.py`: Request/response schemas
- `tools.py`: Tool definitions for function calling
- `service.py`: Agent orchestration logic
- `router.py`: API endpoints

**Features**:
- OpenAI GPT-4 with function calling
- Tools: search emails, create tasks, search memory
- Context retrieval from long-term memory
- Multi-turn conversations with tool execution
- Automatic action generation

**Tool Functions**:
1. `search_emails`: Search user emails
2. `create_task`: Create tasks/reminders
3. `get_tasks`: Retrieve tasks
4. `search_memory`: Semantic memory search

### 8. Workers Module (`app/workers/`)

**Purpose**: Background job scheduling

**Components**:
- `scheduler.py`: APScheduler configuration
- `tasks.py`: Background job implementations

**Jobs**:
- Email sync (every 15 min)
- Calendar sync (every 30 min)
- Reminder checks (every 5 min)
- OAuth token refresh (daily)

## Data Models

### User
- Email, password hash
- Profile information
- Timezone, preferences
- Timestamps

### Integration
- User reference
- Integration type (Google, Microsoft)
- OAuth tokens
- Sync state
- Token expiry

### Email
- User and integration references
- Email content and metadata
- Attachments
- Labels and status
- Entity extraction results
- Vector embeddings

### Calendar Event
- User and integration references
- Event details
- Time and timezone
- Attendees
- Recurrence rules
- Vector embeddings

### Task
- User reference
- Title, description
- Status, priority
- Due date, reminders
- Source tracking
- Tags and category
- Vector embeddings

### Memory
- User reference
- Content and type
- Confidence and importance
- Source tracking
- Validity period
- Vector embeddings
- Access tracking

## Security

### Authentication
- JWT access tokens (30 min expiry)
- JWT refresh tokens (7 day expiry)
- Bcrypt password hashing
- OAuth 2.0 for integrations

### Authorization
- User-scoped data access
- Protected route dependencies
- Token validation middleware

## Performance Optimizations

### Database
- Indexed queries on user_id, timestamps
- Compound indexes for common queries
- Connection pooling

### Caching
- Redis for session data (optional)
- In-memory caching for frequent queries

### Vector Search
- MongoDB Atlas Vector Search
- Cosine similarity for embeddings
- 1536-dimension embeddings (OpenAI)

### Background Jobs
- Async execution with APScheduler
- Configurable intervals
- Error handling and retry logic

## Scalability Considerations

### Horizontal Scaling
- Stateless API design
- MongoDB sharding support
- Redis for distributed caching

### Vertical Scaling
- Connection pooling
- Async I/O with FastAPI
- Batched operations

## Monitoring & Logging

- Structured logging with levels
- Request/response logging
- Error tracking with stack traces
- Job execution logging

## Future Enhancements

1. **Multi-Agent System**
   - Travel agent
   - Finance agent
   - Shopping agent
   - Health agent

2. **Advanced Features**
   - Real-time notifications (WebSocket)
   - Email sending capabilities
   - Calendar event creation
   - Voice interface
   - Mobile push notifications

3. **Integrations**
   - Slack, Telegram
   - Notion, Todoist
   - Banking APIs
   - Travel booking APIs

4. **ML Enhancements**
   - Fine-tuned models for entity extraction
   - Personalized agent behavior
   - Predictive task creation
   - Smart scheduling

## Development Workflow

1. Feature branches from main
2. Pre-commit hooks for code quality
3. Unit and integration tests
4. Code review process
5. CI/CD pipeline
6. Staged deployments

## API Versioning

- Current: `/api/v1/`
- Version in URL path
- Backward compatibility maintained
- Deprecation notices

## Error Handling

- Standardized error responses
- HTTP status codes
- Detailed error messages in development
- Generic messages in production
- Retry logic for external APIs

## Documentation

- OpenAPI/Swagger at `/docs`
- ReDoc at `/redoc`
- Architecture docs (this file)
- Setup guide (SETUP.md)
- API examples

---

For implementation details, see the code in each module.
For setup instructions, see SETUP.md.
For API usage, visit /docs when running the application.
