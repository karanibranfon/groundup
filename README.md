# TeleMedVision

Django-based telemedicine platform for managing patients, studies, and medical imaging.

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
├── telemed/          # Main telemedicine app
├── chat/             # Chat functionality
├── accounts/         # User accounts
├── telemedvision/    # Django project settings
├── static/           # Static assets
├── media/            # User uploads
└── requirements.txt  # Python dependencies
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
   Ensure `settings_production.py` contains:
   ```python
   ALLOWED_HOSTS = ['kaparo.pythonanywhere.com', 'localhost', '127.0.0.1']
   ```

5. **Run migrations and collect static**
   ```bash
   python manage.py migrate
   python manage.py collectstatic --noinput
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

## Important Settings

| Setting | Value | Notes |
|---------|-------|-------|
| TIME_ZONE | Africa/Nairobi | Valid pytz format |
| ALLOWED_HOSTS | Must include kaparo.pythonanywhere.com | Required for deployment |
| MEDIA_ROOT | BASE_DIR / 'media' | User uploads |
| MEDIA_URL | /media/ | Media file URL |

## Adding New Dependencies

When adding a new package:
```bash
pip install <package>
pip freeze > requirements.txt
```

## Notes

- **WebSockets**: Not supported on PythonAnywhere free tier
- **Media files**: Stored in `/media/` directory
- **Database**: SQLite (db.sqlite3)

## Admin Access

Visit `/admin/` to access the Django admin panel.
