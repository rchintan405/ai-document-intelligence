# 🤖 AI Document Intelligence API

<div align="center">

![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991?style=for-the-badge&logo=openai&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-5.4-37814A?style=for-the-badge&logo=celery&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-5%20Services-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![WebSocket](https://img.shields.io/badge/WebSocket-Realtime-010101?style=for-the-badge&logo=socket.io&logoColor=white)
![Pytest](https://img.shields.io/badge/Tests-Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

A **production-grade AI Document Intelligence API** that lets you upload PDF and DOCX files and receive GPT-4o-powered insights — summaries, Q&A pairs, sentiment analysis, named entity extraction, and document classification — all processed asynchronously via Celery with real-time WebSocket status updates.

[Features](#-features) • [Architecture](#-architecture) • [Tech Stack](#-tech-stack) • [Getting Started](#-getting-started) • [API Docs](#-api-documentation) • [Project Structure](#-project-structure) • [Tests](#-running-tests)

</div>

---

## ✨ Features

| Feature | Description |
|---|---|
| 📄 **Document Upload** | Upload PDF or DOCX files up to 10MB |
| 🤖 **AI Summarization** | GPT-4o-mini generates a 3-5 sentence professional summary |
| 🏷️ **Document Classification** | Auto-classifies as invoice, contract, resume, report, article, legal, or other |
| 💡 **Key Point Extraction** | Extracts 5-8 bullet-point key takeaways |
| 😊 **Sentiment Analysis** | Rates document tone as positive/neutral/negative with a -1.0 to 1.0 score |
| ❓ **Q&A Generation** | Generates 5 insightful question-answer pairs from the content |
| 🔍 **Entity Extraction** | Identifies people, organizations, dates, and locations |
| 💬 **Ask Anything (RAG-lite)** | Ask free-form questions answered from document context |
| ⚡ **Async Processing** | Celery + Redis job queue — no blocking, instant response on upload |
| 📡 **WebSocket Updates** | Real-time processing status streamed to the client |
| 🚦 **Rate Limiting** | Per-IP rate limiting via SlowAPI |
| 🔐 **JWT Auth** | Secure register/login — every user only sees their own documents |
| 🐳 **5-Service Docker** | API + Worker + DB + Redis + Flower dashboard |
| 🌸 **Flower Dashboard** | Monitor Celery tasks at http://localhost:5555 |

---

## 🏗 Architecture

```
┌─────────────┐     Upload      ┌─────────────────┐
│   Client    │ ─────────────▶  │   FastAPI API   │
│             │                 │   (Port 8000)   │
│             │ ◀─ WS Status ─  │                 │
└─────────────┘                 └────────┬────────┘
                                         │ Dispatch task
                                         ▼
                                ┌─────────────────┐
                                │      Redis      │ ◀─── Task Results
                                │  (Port 6379)    │
                                └────────┬────────┘
                                         │ Consume task
                                         ▼
                                ┌─────────────────┐
                                │  Celery Worker  │
                                │                 │
                                │  1. Parse Doc   │
                                │  2. Classify    │
                                │  3. Summarize   │
                                │  4. Key Points  │
                                │  5. Sentiment   │
                                │  6. Q&A Pairs   │
                                │  7. Entities    │
                                └────────┬────────┘
                                         │ Save results
                                         ▼
                                ┌─────────────────┐     ┌──────────────┐
                                │   PostgreSQL    │     │    Flower    │
                                │   (Port 5432)   │     │ (Port 5555)  │
                                └─────────────────┘     └──────────────┘
```

---

## 🛠 Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| API Framework | FastAPI 0.111 | Async REST API + WebSocket |
| AI / LLM | OpenAI GPT-4o-mini | Document intelligence |
| Job Queue | Celery 5.4 | Async AI processing pipeline |
| Message Broker | Redis 7 | Task queue + result backend |
| Database | PostgreSQL 16 | Document metadata + AI results |
| ORM | SQLAlchemy 2.0 | DB models |
| Migrations | Alembic | Schema versioning |
| Auth | JWT (python-jose) + bcrypt | Secure authentication |
| Rate Limiting | SlowAPI | Abuse prevention |
| PDF Parsing | pypdf | Text extraction |
| DOCX Parsing | python-docx | Text extraction |
| Monitoring | Flower | Celery task dashboard |
| Containerization | Docker Compose | 5-service orchestration |
| Testing | Pytest + unittest.mock | Full test suite |

---

## 🚀 Getting Started

### Prerequisites

- [Docker & Docker Compose](https://docs.docker.com/get-docker/)
- An [OpenAI API key](https://platform.openai.com/api-keys) (GPT-4o-mini is very affordable)

---

### ▶ Run with Docker (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/rchintan405/ai-document-intelligence.git
cd ai-document-intelligence

# 2. Set up environment variables
cp .env.example .env
# Open .env and set:
#   OPENAI_API_KEY=sk-your-key-here
#   SECRET_KEY=any-random-long-string

# 3. Start all 5 services
docker compose up --build

# Services running:
#   API        → http://localhost:8000
#   Docs       → http://localhost:8000/docs
#   Flower     → http://localhost:5555
```

---

### ▶ Run Locally

```bash
# 1. Clone and enter
git clone https://github.com/rchintan405/ai-document-intelligence.git
cd ai-document-intelligence

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Update DATABASE_URL, REDIS_URL, CELERY_BROKER_URL, OPENAI_API_KEY

# 5. Start API
uvicorn app.main:app --reload

# 6. In a separate terminal — start Celery worker
celery -A app.workers.celery_app worker --loglevel=info

# 7. Optional — Flower monitoring dashboard
celery -A app.workers.celery_app flower --port=5555
```

---

## 📖 API Documentation

| Interface | URL |
|---|---|
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Flower Dashboard | http://localhost:5555 |

---

### 🔑 Auth Endpoints

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | Register a new user | ❌ |
| `POST` | `/api/v1/auth/login` | Login and get JWT token | ❌ |
| `GET` | `/api/v1/auth/me` | Get current user profile | ✅ |

---

### 📄 Document Endpoints

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/api/v1/documents/upload` | Upload PDF/DOCX for processing | ✅ |
| `GET` | `/api/v1/documents/` | List all your documents | ✅ |
| `GET` | `/api/v1/documents/{id}/status` | Poll processing status | ✅ |
| `GET` | `/api/v1/documents/{id}/results` | Get full AI results | ✅ |
| `POST` | `/api/v1/documents/{id}/ask` | Ask a question about the doc | ✅ |
| `DELETE` | `/api/v1/documents/{id}` | Delete document + file | ✅ |

---

### 📡 WebSocket

```
ws://localhost:8000/api/v1/ws/documents/{id}/status
```

**Connection protocol:**
1. Connect to the WebSocket URL
2. Send your JWT access token as the first message
3. Receive real-time JSON frames every 2 seconds until complete

**Example frames:**

```json
// While processing
{"document_id": 1, "status": "processing", "message": "AI is analyzing your document...", "word_count": 1523}

// On completion
{"document_id": 1, "status": "completed", "document_type": "contract", "sentiment": "neutral", "ai_tokens_used": 2847}

// On failure
{"document_id": 1, "status": "failed", "error": "OpenAI API error: ..."}
```

---

### 🤖 Full AI Result Response

```json
{
  "id": 1,
  "original_filename": "contract.pdf",
  "file_type": "pdf",
  "word_count": 3241,
  "page_count": 8,
  "status": "completed",
  "document_type": "contract",
  "summary": "This service agreement outlines the terms between Acme Corp and TechCo for software development services, covering payment terms, deliverables, and IP ownership...",
  "key_points": [
    "Contract duration: 12 months commencing January 2025",
    "Payment: $15,000/month net 30",
    "IP ownership transfers to client upon full payment",
    "Either party may terminate with 30 days written notice"
  ],
  "sentiment": "neutral",
  "sentiment_score": 0.12,
  "qa_pairs": [
    {"question": "What is the contract duration?", "answer": "12 months from January 2025."},
    {"question": "Who owns the IP?", "answer": "IP transfers to the client upon full payment."}
  ],
  "extracted_entities": {
    "people": ["John Smith", "Jane Doe"],
    "organizations": ["Acme Corp", "TechCo"],
    "dates": ["January 1, 2025", "December 31, 2025"],
    "locations": ["San Francisco, CA"]
  },
  "ai_tokens_used": 2847,
  "processed_at": "2025-07-01T14:32:11Z"
}
```

---

## 📁 Project Structure

```
ai-document-intelligence/
├── app/
│   ├── main.py                        # FastAPI app, middleware, lifespan
│   ├── api/v1/
│   │   ├── router.py                  # Route aggregator
│   │   ├── dependencies.py            # JWT auth dependency
│   │   └── endpoints/
│   │       ├── auth.py                # Register, login, me
│   │       ├── documents.py           # Upload, list, status, results, ask, delete
│   │       └── websocket.py           # Real-time status WebSocket
│   ├── core/
│   │   ├── config.py                  # Pydantic settings (env vars)
│   │   ├── security.py                # JWT encode/decode, bcrypt
│   │   └── limiter.py                 # SlowAPI rate limiter
│   ├── db/
│   │   └── session.py                 # SQLAlchemy engine, session, Base
│   ├── models/
│   │   ├── user.py                    # User ORM model
│   │   └── document.py                # Document ORM model (status, AI results)
│   ├── schemas/
│   │   ├── user.py                    # Pydantic user schemas
│   │   └── document.py                # Pydantic document schemas
│   ├── services/
│   │   ├── document_parser.py         # PDF/DOCX text extraction
│   │   └── ai/
│   │       └── openai_service.py      # All GPT-4o-mini calls
│   ├── tasks/
│   │   └── document_tasks.py          # Celery 7-step AI pipeline task
│   └── workers/
│       └── celery_app.py              # Celery app config
├── tests/
│   ├── conftest.py                    # Fixtures (client, db, auth)
│   ├── test_auth.py                   # Auth endpoint tests
│   ├── test_documents.py              # Document upload/CRUD tests (mocked AI)
│   ├── test_ai_service.py             # AI function unit tests (mocked OpenAI)
│   └── test_document_parser.py        # Parser utility tests
├── alembic/                           # DB migration files
├── docker-compose.yml                 # 5-service orchestration
├── Dockerfile
├── requirements.txt
├── alembic.ini
└── .env.example
```

---

## 🧪 Running Tests

No OpenAI key needed — all AI calls are mocked:

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest

# With verbose output
pytest -v

# With coverage
pytest --cov=app --cov-report=term-missing

# Run specific suite
pytest tests/test_ai_service.py -v
```

---

## 🔒 Security & Production Notes

- All AI calls are mocked in tests — zero OpenAI costs during CI/CD
- Passwords hashed with bcrypt, JWTs expire in 30 minutes
- Rate limiting: 20 req/min globally, 10 req/min on `/ask`
- Each user is fully isolated — can only access their own documents
- Celery tasks retry up to 3 times on transient failures
- Task soft timeout: 120s, hard timeout: 150s
- `.env` is gitignored — use `.env.example` as a template

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Commit your changes: `git commit -m "feat: add your feature"`
4. Push: `git push origin feat/your-feature`
5. Open a Pull Request

> **Note:** Direct pushes to `main` and `develop` are branch-protected.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<div align="center">

Built with ❤️ by [Karan Prajapati](https://kretoss.com/portfolio)

[![Portfolio](https://img.shields.io/badge/Portfolio-kretoss.com-blue?style=flat-square)](https://kretoss.com/portfolio)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0077B5?style=flat-square&logo=linkedin)](https://linkedin.com/in/your-profile)
[![Upwork](https://img.shields.io/badge/Upwork-Hire%20Me-6FDA44?style=flat-square&logo=upwork&logoColor=white)](https://www.upwork.com/freelancers/your-profile)

</div>
