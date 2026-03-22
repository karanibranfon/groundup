# TeleMedVision

A comprehensive Django-based telemedicine platform for managing patients, medical imaging studies, and AI-powered analysis with end-to-end encryption.

## Overview

TeleMedVision is a full-featured medical imaging platform that combines:
- **Patient Management** - Complete patient records with unique IDs
- **Medical Imaging** - Upload, view, and manage DICOM and standard medical images
- **AI Analysis** - LLM-powered image analysis with multiple provider support
- **Secure Encryption** - DNA-Chaos encryption for medical image security
- **Real-time Chat** - WebSocket-based messaging system
- **User Accounts** - Quota-based tiered access (Free/Premium)

## Tech Stack

- **Backend**: Django 5.x with Django REST Framework
- **Database**: SQLite (development) / PostgreSQL (production ready)
- **Real-time**: Django Channels with Redis
- **AI**: LangChain with OpenAI, Anthropic, or Ollama support
- **Authentication**: JWT + Session authentication
- **Deployment**: PythonAnywhere compatible

## Features

### Syringly - Medical Q&A Platform

A Stack Overflow-style knowledge sharing platform designed specifically for medical professionals. Syringly enables healthcare workers to:

- **Ask Questions** - Post clinical questions to get expert answers from peers
- **Share Knowledge** - Answer questions and build collective medical expertise
- **Tag & Categorize** - Organize questions by medical specialty (Cardiology, Neurology, etc.)
- **Vote & Reputation** - Upvote helpful answers, build credibility through contributions
- **Accept Best Answers** - Mark the most helpful response as accepted

Access Syringly at `/syringly/` or via the navigation.

### Medical Imaging
- Support for DICOM (.dcm) and standard formats (JPG, PNG, TIFF)
- Study management (X-Ray, CT, MRI, Ultrasound, PET)
- Image viewer with basic tools (zoom, pan, measure)
- Image enhancement capabilities
- Processing logs and audit trail

### AI-Powered Analysis
- Multi-LLM support (OpenAI GPT-4, Anthropic Claude, Ollama)
- Study-type-specific prompts for radiology analysis
- Confidence scores, urgency assessment, recommendations
- JSON-structured results for integration

### Security & Encryption
- **DNA-Chaos Encryption** - Implements ITIEDC algorithm
- Chaotic map (PWLCM) for key generation
- DNA encoding with 8 possible rules
- One-Time Pad (OTP) encryption
- Arithmetic coding compression option
- SHA-256 integrity verification

### Chat System
- Real-time WebSocket messaging
- Direct messages and group chats
- Message attachments (images, video, audio, documents)
- Status updates (24hr expiry)
- Call logging (audio/video)
- Online presence and read receipts
- Message reactions and replies
- Starred messages and search

### Syringly - Q&A Platform
- **Questions & Answers** - Post clinical questions, receive expert answers
- **Voting System** - Upvote/downvote questions and answers
- **Accepted Answers** - Mark best answers as accepted
- **Reputation System** - Earn points through contributions
- **Tags** - Categorize by medical specialty
- **User Profiles** - Track activity, questions, and answers
- **Stack Overflow-style UI** - Familiar, professional interface

### User Management
- JWT-based authentication
- Session authentication fallback
- Profile management with avatars
- Daily quota system (10 images/day for free tier)
- Privacy settings (last seen, profile visibility)
- Two-step verification option

## Quick Start

```bash
# Clone and setup
git clone <repo-url>
cd groundup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run migrations and start
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Project Structure

```
groundup/
├── syringly/                 # Medical Q&A platform (Stack Overflow for medics)
│   ├── models.py             # Question, Answer, Tag, Vote, UserProfile models
│   ├── views.py              # Q&A views, voting, user profiles
│   ├── urls.py               # URL routing
│   └── templates/            # Q&A templates
├── telemed/                  # Main telemedicine app
│   ├── models.py             # Patient, Study, Image, EncryptionKey models
│   ├── services/
│   │   ├── dna_chaos_encryption.py  # DNA-Chaos encryption implementation
│   │   └── ai_analyzer.py            # LLM-based medical image analysis
│   ├── forms.py              # Django forms
│   ├── urls.py               # URL routing
│   └── migrations/           # Database migrations
├── chat/                     # Chat/messaging app
│   ├── models.py             # Message, Conversation, Profile models
│   ├── consumers.py          # WebSocket consumers
│   ├── views.py              # Chat views
│   └── urls.py               # Chat URL routing
├── accounts/                 # User account management
├── telemedvision/            # Django project settings
│   ├── settings.py           # Base settings
│   ├── settings_production.py  # Production overrides
│   ├── settings_local.py     # Local development
│   ├── asgi.py               # ASGI config for channels
│   └── wsgi.py               # WSGI config for deployment
├── static/                   # Static assets
├── media/                    # User uploads
├── logs/                     # Application logs
└── requirements.txt          # Python dependencies
```

## Configuration

### Environment Variables

Create a `.env` file from `.env.example`:

```bash
# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (optional - defaults to SQLite)
DATABASE_URL=postgresql://user:pass@localhost/dbname

# Redis (for channels)
REDIS_URL=redis://localhost:6379

# AI Providers (at least one required)
OPENAI_API_KEY=sk-...
# or
ANTHROPIC_API_KEY=sk-ant-...
# or use local Ollama (no API key needed)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
```

### Key Settings

| Setting | Default | Description |
|---------|---------|-------------|
| TIME_ZONE | Africa/Nairobi | Server timezone |
| DAILY_IMAGE_QUOTA | 10 | Free tier daily limit |
| MAX_UPLOAD_SIZE | 50MB | Maximum file upload |
| ALLOWED_EXTENSIONS | dcm, jpg, png, tiff | Supported formats |

## DNA-Chaos Encryption

The encryption module (`telemed/services/dna_chaos_encryption.py`) implements:

1. **PWLCM Chaotic Map** - Generates pseudo-random sequences
2. **DNA Encoding** - Converts bytes to DNA bases (A, T, G, C) using 8 rules
3. **DNA XOR** - Secure combination of encoded data with OTP
4. **Arithmetic Coding** - Optional lossless compression

### Usage

```python
from telemed.services.dna_chaos_encryption import DNACryptoService

service = DNACryptoService(master_key=b'secret-key')
encrypted, params = service.encrypt_image(image_bytes, width, height)
decrypted = service.decrypt_image(encrypted, params)
```

## AI Analysis

Configure LLM provider in settings:

```python
# Use OpenAI (default)
LLM_PROVIDER = 'openai'
OPENAI_API_KEY = 'sk-...'

# Or Anthropic
LLM_PROVIDER = 'anthropic'
ANTHROPIC_API_KEY = 'sk-ant-...'

# Or local Ollama
LLM_PROVIDER = 'ollama'
OLLAMA_BASE_URL = 'http://localhost:11434'
```

## Deployment on PythonAnywhere

1. **Clone repo**
   ```bash
   git clone <repo-url>
   cd groundup
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure WSGI**
   Edit `wsgi.py` to use production settings:
   ```python
   os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'telemedvision.settings_production')
   ```

4. **Set ALLOWED_HOSTS**
   Update `settings_production.py` with your domain.

5. **Run migrations and collect static**
   ```bash
   python manage.py migrate
   python manage.py collectstatic --noinput
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

## Adding New Dependencies

When adding a new package:
```bash
pip install <package>
pip freeze > requirements.txt
```

## Important Notes

- **WebSockets**: Require Redis (not available on PythonAnywhere free tier)
- **Media files**: Stored in `/media/` directory
- **Database**: SQLite (db.sqlite3) for development
- **Timezone**: Defaults to Africa/Nairobi - adjust for your location
- **Security**: Change SECRET_KEY in production, use strong master key for encryption

## Admin Access

Visit `/admin/` to access the Django admin panel after creating a superuser.

## License

This project is provided as-is for educational and demonstration purposes.