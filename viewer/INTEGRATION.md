# OHIF Viewer Integration Guide

## Overview

This directory contains OHIF Viewers v3.12.0 cloned from https://github.com/OHIF/Viewers

---

## Fresh Server Setup (First Time)

### Prerequisites

```bash
# 1. Install Bun (if not installed)
curl -fsSL https://bun.sh/install | bash

# 2. Add to PATH (add to ~/.bashrc for persistence)
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"
```

### Step 1: Install Dependencies

```bash
cd viewer
bun install
```

### Step 2: Development Mode (Fast with rsbuild)

```bash
cd viewer/platform/app
PUBLIC_URL=/ohif/ bun run dev:fast
# Runs on http://localhost:3000
```

### Step 3: Production Build

```bash
cd viewer
PUBLIC_URL=/ohif/ bun run build
# Output: viewer/platform/app/dist/
```

---

## Alternative: Using Yarn (if available)

```bash
# Install yarn globally first
npm install -g yarn

cd viewer
yarn install --frozen-lockfile

# Dev mode
yarn start

# Production build
PUBLIC_URL=/ohif/ yarn build
```

---

## Integration with Django (GroundUp)

### Option A: Standalone Service (Recommended)

Run OHIF on a separate port (e.g., 8080) and proxy through Django:

1. **Build OHIF**:
```bash
cd viewer
yarn build
```

2. **Update Django settings** (`telemedvision/settings.py`):
```python
import os

OHIF_STATIC_ROOT = os.path.join(BASE_DIR, 'viewer', 'platform', 'app', 'dist')
OHIF_DEV_URL = 'http://localhost:3000'
```

3. **Add URL route** (`telemedvision/urls.py`):
```python
from django.views.generic import RedirectView

urlpatterns = [
    # OHIF Viewer
    path('ohif/', RedirectView.as_view(url=settings.OHIF_DEV_URL, permanent=False), name='ohif_viewer'),
    # ... existing routes
]
```

### Option B: Serve Static Build from Django

1. **Build OHIF**:
```bash
cd viewer
yarn build
```

2. **Collect static files** or serve directly:
```python
# In settings.py
STATICFILES_DIRS = [
    # ... existing dirs
    os.path.join(BASE_DIR, 'viewer', 'platform', 'app', 'dist'),
]

# In urls.py
from django.conf import settings
from django.views.generic import TemplateView

urlpatterns = [
    path('viewer/', TemplateView.as_view(template_name='index.html'), name='ohif_viewer'),
    # Serve OHIF static files
    re_path(r'^ohif-static/(?P<path>.*)$', serve, {'document_root': settings.OHIF_STATIC_ROOT}),
]
```

3. **Configure OHIF for local data** (`viewer/platform/app/dist/config/local_static.js`):
```javascript
// Edit this file before building to point to your Django API
window.config = {
  // ... existing config ...
  dataSources: [
    {
      namespace: '@ohif/extension-default.dataSourcesModule.dicomweb',
      sourceName: 'dicomweb',
      configuration: {
        name: 'DCM4CHEE',
        wadoUriRoot: '/api/dicom/wado',  // Your Django DICOM endpoint
        qidoRoot: '/api/dicom/qido',
        wadoRoot: '/api/dicom/wado',
        // ...
      },
    },
  ],
};
```

### Option C: iframe Embedding

Embed OHIF in a Django template:

1. **Build OHIF**:
```bash
cd viewer && yarn build
```

2. **Create template** (`telemedvision/templates/telemed/ohif_embed.html`):
```html
{% extends "telemed/base.html" %}
{% load static %}

{% block content %}
<div class="ohif-container" style="height: 100vh; width: 100%;">
  <iframe 
    src="/static/dist/" 
    style="width: 100%; height: 100%; border: none;"
    allow="fullscreen"
  ></iframe>
</div>
{% endblock %}
```

3. **Pass study data via URL params**:
```javascript
// In your Django view
const ohifUrl = `/static/dist/?StudyInstanceUIDs=${studyUid}`;

// Or use postMessage for communication
```

---

## API Integration

### For DICOM Web Compatible API

Add DICOM Web endpoints to Django:

```python
# telemed/urls.py
from .api_views import DICOMQIDOView, DICOMWADOView

urlpatterns = [
    # DICOM Web endpoints
    path('api/dicom/qido/<path:query>', DICOMQIDOView.as_view(), name='dicom_qido'),
    path('api/dicom/wado/<path:query>', DICOMWADOView.as_view(), name='dicom_wado'),
]
```

### For JSON Data Source (Simpler)

Create an API that returns study data in OHIF's JSON format:

```javascript
{
  "studies": [{
    "StudyInstanceUID": "1.2.3.4.5",
    "StudyDescription": "Knee MRI",
    "PatientName": "John Doe",
    "series": [{
      "SeriesInstanceUID": "1.2.3.4.5.1",
      "SeriesDescription": "T1",
      "instances": [{
        "metadata": {
          "Columns": 512,
          "Rows": 512,
          // ... required DICOM tags
        },
        "url": "/api/images/123/file"
      }]
    }]
  }]
}
```

Use URL: `/viewer/?StudyInstanceUIDs=<uid>`

---

## Configuration Files

| File | Purpose |
|------|---------|
| `config/default.js` | Default configuration |
| `config/local_static.js` | Local static file data source |
| `config/demo.js` | Demo with sample data |
| `config/dicomweb.js` | DICOM Web server config |

---

## Development Workflow

```bash
# Export bun path
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"

# 1. Make changes to OHIF
cd viewer/platform/app

# 2. Run in dev mode (fast with rsbuild)
PUBLIC_URL=/ohif/ bun run dev:fast

# 3. Test at http://localhost:3000

# 4. Build for production
cd viewer
PUBLIC_URL=/ohif/ bun run build

# 5. Copy dist/ to Django static files
cp -r platform/app/dist/* ../telemedvision/static/ohif/
```

---

## Key Paths

- **Source**: `viewer/platform/app/src/`
- **Config**: `viewer/platform/app/public/config/`
- **Build output**: `viewer/platform/app/dist/`
- **Main entry**: `viewer/platform/app/src/index.js`

---

## Docker Deployment

```bash
cd viewer
docker build -t ohif-viewer .
docker run -p 8080:80 ohif-viewer
```

Or use the included recipe:
```bash
cd viewer/platform/app
docker compose -f .recipes/Nginx-Orthanc/docker-compose.yml up
```

---

## Troubleshooting

### yarn not found
OHIF requires yarn but it's not installed. Use bun instead:
```bash
# Install bun
curl -fsSL https://bun.sh/install | bash
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"

# Use bun instead of yarn
bun install
bun run dev:fast
bun run build
```

### Build timeout
First build can take 15-30 minutes due to large bundle. Subsequent builds with rsbuild (dev:fast) are faster.

### CORS Issues
Enable CORS on your Django API:
```python
# pip install django-cors-headers
INSTALLED_APPS = ['corsheaders', ...]
MIDDLEWARE = ['corsheaders.middleware.CorsMiddleware', ...]
CORS_ALLOW_ALL_ORIGINS = True
```

### Authentication
OHIF supports OIDC. Configure in your config file:
```javascript
window.config = {
  oidc: [{
    // OIDC provider config
    authority: 'https://your-idp.com',
    client_id: 'your-client-id',
    redirect_uri: '/callback',
    // ...
  }]
};
```

### routerBasename Mismatch
`routerBasename` in config MUST match the URL path where OHIF is served. If served at `/ohif/`, config must have `routerBasename: '/ohif/'`.

### iframe sandbox restrictions
Do NOT add `sandbox` attribute to iframe - OHIF requires full browser capabilities.
