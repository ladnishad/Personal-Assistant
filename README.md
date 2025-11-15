# LifeOS - AI Personal Life Assistant

The ultimate AI-powered personal assistant that acts as your second brain, managing your entire digital and real-world life with intelligence, memory, and autonomy.

## 🎯 Vision

LifeOS is designed to:
- **Automatically ingest** emails, files, bills, receipts, and calendar events
- **Extract meaningful structure** like tasks, deadlines, appointments, and reminders
- **Maintain long-term memory** of preferences, patterns, and context
- **Be proactive** with alerts, planning, and predictions
- **Execute autonomously** through an intelligent LLM orchestrator
- **Replace 10+ apps** as your real-life executive assistant

## 🏗️ Architecture

### Tech Stack
- **Backend**: Python 3.11+ with FastAPI
- **Database**: MongoDB Atlas with Vector Search
- **Caching**: Redis (optional)
- **Task Queue**: APScheduler
- **LLM**: OpenAI GPT-4 with function calling
- **Auth**: JWT + OAuth (Google & Microsoft)
- **Integrations**: Gmail, Outlook, Google Calendar, Outlook Calendar

### Core Modules
- `auth` - User authentication and authorization
- `integrations` - Gmail, Outlook, Calendar sync
- `emails` - Email ingestion, parsing, entity extraction
- `calendar` - Calendar event management
- `tasks` - Task and reminder system
- `memory` - Long-term memory with vector search
- `agent` - LLM orchestrator with tool calling
- `workers` - Background jobs and scheduling

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose (for containerized deployment)
- **MongoDB running locally** (or MongoDB Atlas URI for production)
- OpenAI API key

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd Personal-Assistant
```

2. **Start MongoDB locally** (if not already running)
```bash
# MongoDB
brew services start mongodb-community  # Mac
# or: mongod  # Linux/Windows
```

3. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration:
# - Add your OpenAI API key
# - Add Google/Microsoft OAuth credentials
# - For production: Update MONGODB_URL to your Atlas/production URI
```

4. **Run with Docker Compose** (Recommended)
```bash
# Starts the API container and Redis container
# API connects to your host's MongoDB (localhost:27017)
docker-compose up --build
```

5. **Or run locally without Docker**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn app.main:app --reload
```

### Access
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Important Notes
- Docker setup:
  - **MongoDB**: Connects to your host's local MongoDB (not containerized)
  - **Redis**: Runs in a Docker container
- **Development**: Uses `mongodb://localhost:27017` from your `.env` file
- **Production**: Update `MONGODB_URL` in `.env` to your production URI (MongoDB Atlas, etc.)

## 📚 API Documentation

Once running, visit http://localhost:8000/docs for interactive API documentation.

### Key Endpoints
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/integrations/google/connect` - Connect Gmail/Calendar
- `POST /api/v1/integrations/microsoft/connect` - Connect Outlook/Calendar
- `POST /api/v1/agent/chat` - Chat with AI orchestrator
- `GET /api/v1/emails` - List emails
- `GET /api/v1/tasks` - List tasks
- `GET /api/v1/calendar/events` - List calendar events

## 🔧 Configuration

Key environment variables:

```env
# MongoDB
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=lifeos

# OpenAI
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4-turbo-preview

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret

# Microsoft OAuth
MICROSOFT_CLIENT_ID=your-client-id
MICROSOFT_CLIENT_SECRET=your-client-secret
```

## 🧪 Development

### Code Quality
```bash
# Format code
black app/

# Lint code
ruff check app/

# Run tests
pytest
```

### Pre-commit Hooks
```bash
pre-commit install
pre-commit run --all-files
```

## 📁 Project Structure

```
Personal-Assistant/
├── app/
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration management
│   ├── database.py             # MongoDB connection
│   ├── auth/                   # Authentication module
│   ├── integrations/           # External service integrations
│   ├── emails/                 # Email processing
│   ├── calendar/               # Calendar management
│   ├── tasks/                  # Task and reminder system
│   ├── memory/                 # Long-term memory & vector search
│   ├── agent/                  # LLM orchestrator
│   └── workers/                # Background jobs
├── tests/                      # Test suite
├── docker-compose.yml          # Docker orchestration
├── Dockerfile                  # Container definition
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 🛣️ MVP Roadmap

- [x] Project skeleton and configuration
- [ ] Authentication module (JWT + OAuth)
- [ ] Integrations (Gmail, Outlook, Calendar)
- [ ] Email ingestion and parsing
- [ ] Memory system with vector search
- [ ] Tasks and reminders
- [ ] Agent orchestrator with LLM
- [ ] Background workers
- [ ] Logging and monitoring

## 📄 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Contributions are welcome! Please read CONTRIBUTING.md for details.

## 📞 Support

For issues and questions, please open a GitHub issue.
