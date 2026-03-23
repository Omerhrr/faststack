# 🚀 FastStack

**Async-first Python framework built on FastAPI with integrated templating, ORM, admin, and CLI.**

FastStack combines the developer experience of Django with the performance and modern features of FastAPI. It provides everything you need to build production-ready web applications quickly.

## ✨ Features

- **🚀 FastAPI Powered** - Modern, fast, async web framework with automatic OpenAPI docs
- **📊 SQLModel ORM** - Type-safe database models built on SQLAlchemy and Pydantic
- **🔐 Built-in Auth** - Secure authentication with password hashing and session management
- **🎛️ Admin Panel** - Auto-generated admin interface for your models (like Django admin)
- **📁 Modular Apps** - Organize code into reusable app modules
- **🔌 Auto-discovery** - Automatic loading of routes, models, and admin configurations
- **📝 Jinja2 Templates** - Server-side rendering with template inheritance
- **⚡ HTMX Ready** - Build dynamic UIs without complex JavaScript
- **🎨 Tailwind CSS** - Beautiful, responsive designs out of the box
- **🧩 FastUI Integration** - Optional bundled frontend (Alpine.js, ECharts, Flowbite)
- **🛠️ Powerful CLI** - Create projects, apps, run migrations with ease

## 📦 Installation

### Using uv (recommended)

```bash
# Install uv if you haven't
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create a new project
uv tool install faststack
faststack startproject myproject
cd myproject
uv sync
uv run faststack runserver
```

### Using pip

```bash
pip install faststack
faststack startproject myproject
cd myproject
pip install -e .
faststack runserver
```

## 🏃 Quick Start

```bash
# 1. Create a new project
faststack startproject myproject

# 2. Navigate to the project
cd myproject

# 3. Install dependencies
uv sync

# 4. Start the development server
uv run faststack runserver

# 5. Open http://localhost:8000
```

## 📁 Project Structure

```
myproject/
├── apps/                   # Application modules
│   └── example/           # Example app
│       ├── models.py      # Database models
│       ├── routes.py      # Web routes
│       ├── schemas.py     # Pydantic schemas
│       ├── services.py    # Business logic
│       └── admin.py       # Admin configuration
├── templates/             # Jinja2 templates
│   ├── base.html
│   ├── pages/
│   └── components/
├── static/                # Static files
│   ├── css/
│   ├── js/
│   └── img/
├── migrations/            # Alembic migrations
├── main.py               # Application entry point
├── manage.py             # Management script
├── pyproject.toml        # Project configuration
└── .env                  # Environment variables
```

## 🛠️ CLI Commands

```bash
# Create a new project
faststack startproject myproject

# Create a new app
faststack startapp blog

# Run development server
faststack runserver

# Create database migrations
faststack makemigrations -m "Add blog model"

# Apply migrations
faststack migrate

# Create admin user
faststack createsuperuser

# Open interactive shell
faststack shell

# Show version
faststack version
```

## 📝 Creating an App

```bash
# Create a new app
faststack startapp blog
```

This creates a new app with:

```python
# apps/blog/models.py
from sqlmodel import Field
from faststack.orm.base import TimestampedModel

class Post(TimestampedModel, table=True):
    title: str = Field(index=True)
    content: str
    published: bool = Field(default=False)
```

```python
# apps/blog/routes.py
from fastapi import APIRouter, Request
from faststack.app import get_templates

router = APIRouter(prefix="/blog", tags=["blog"])

@router.get("/")
async def blog_list(request: Request):
    templates = get_templates()
    return templates.TemplateResponse("blog/list.html", {"request": request})
```

```python
# apps/blog/admin.py
from faststack.admin import register_model
from apps.blog.models import Post

register_model(
    Post,
    list_display=["id", "title", "published", "created_at"],
    search_fields=["title", "content"],
    list_filter=["published"],
    icon="newspaper",
)
```

## 🔐 Authentication

FastStack comes with built-in authentication:

```python
from fastapi import Depends
from faststack.core.dependencies import CurrentUser, AdminUser
from faststack.auth.models import User

# Require authentication
@router.get("/profile")
async def profile(user: CurrentUser):
    return {"email": user.email}

# Require admin access
@router.get("/admin/settings")
async def admin_settings(user: AdminUser):
    return {"message": "Admin only"}
```

## 🎨 Templates

FastStack uses Jinja2 templates with Tailwind CSS:

```html
<!-- templates/blog/list.html -->
{% extends "base.html" %}

{% block title %}Blog Posts{% endblock %}

{% block content %}
<div class="container mx-auto py-8">
    <h1 class="text-3xl font-bold mb-6">Blog Posts</h1>

    <div class="space-y-4">
        {% for post in posts %}
        <div class="bg-white rounded-lg shadow p-6">
            <h2 class="text-xl font-semibold">{{ post.title }}</h2>
            <p class="text-gray-600 mt-2">{{ post.content|truncate(200) }}</p>
            <a href="/blog/{{ post.id }}" class="text-indigo-600 hover:underline mt-4 inline-block">
                Read more →
            </a>
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
```

## ⚡ HTMX Integration

Build dynamic UIs with HTMX:

```html
<!-- Delete with confirmation -->
<button hx-delete="/api/posts/{{ post.id }}"
        hx-confirm="Are you sure?"
        hx-target="closest .post-card"
        hx-swap="outerHTML">
    Delete
</button>

<!-- Load content dynamically -->
<div hx-get="/api/posts/recent"
     hx-trigger="load"
     hx-swap="innerHTML">
    Loading...
</div>
```

## 📊 Admin Panel

Access the auto-generated admin panel at `/admin/`:

1. Create a superuser: `faststack createsuperuser`
2. Login at `/auth/login`
3. Manage your models at `/admin/`

## 🔧 Configuration

Environment variables in `.env`:

```bash
# Application
APP_NAME=My App
APP_ENV=development
DEBUG=true
SECRET_KEY=your-secret-key

# Database
DATABASE_URL=sqlite:///./app.db
# DATABASE_URL=postgresql://user:pass@localhost/db

# Server
HOST=127.0.0.1
PORT=8000

# Frontend (see below)
FRONTEND_MODE=fastui
```

## 🎨 Frontend Configuration

FastStack supports two frontend modes:

### FastUI Mode (Default)

Single CDN bundle with everything included:

```bash
FRONTEND_MODE=fastui
```

Includes:
- **Tailwind CSS** - Utility-first CSS
- **HTMX 2.0** - AJAX without JavaScript
- **Alpine.js 3.x** - Lightweight reactivity
- **ECharts 6.x** - Beautiful charts
- **Flowbite 4.x** - UI components

**Custom Alpine.js Directives:**
- `x-chart` - Declarative ECharts integration
- `x-lazy` - Lazy loading with IntersectionObserver
- `x-flow` - Flowbite component helpers

```html
<!-- Chart example -->
<div x-chart='{
    "title": { "text": "Sales Data" },
    "xAxis": { "type": "category", "data": ["Mon", "Tue", "Wed"] },
    "yAxis": { "type": "value" },
    "series": [{ "type": "bar", "data": [120, 200, 150] }]
}' style="height: 300px;"></div>
```

### Default Mode (Individual Libraries)

Load libraries separately for more control:

```bash
FRONTEND_MODE=default
```

Configure individual CDNs:
```bash
HTMX_CDN_URL=https://cdn.jsdelivr.net/npm/htmx.org@2.0.8/dist/htmx.min.js
ALPINE_CDN_URL=https://cdn.jsdelivr.net/npm/alpinejs@3.15.8/dist/cdn.min.js
ECHARTS_CDN_URL=https://cdn.jsdelivr.net/npm/echarts@6.0.0/dist/echarts.min.js
TAILWIND_CDN_URL=https://cdn.tailwindcss.com
```

Feature toggles:
```bash
FRONTEND_ENABLE_ECHARTS=true
FRONTEND_ENABLE_FLOWBITE=true
```

### Template Access

Access frontend settings in any template:

```html
<div class="badge {% if frontend.mode == 'fastui' %}bg-indigo-100{% else %}bg-green-100{% endif %}">
    {{ frontend.mode|upper }} Mode
</div>

{% if frontend.mode == 'fastui' %}
    <div x-chart='{ ... }'></div>
{% else %}
    <div id="chart"></div>
    <script>echarts.init(document.getElementById('chart')).setOption({...});</script>
{% endif %}
```

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=faststack
```

## 📚 Documentation

- [FastStack Documentation](https://faststack.dev/docs)
- [FastUI Documentation](https://github.com/Omerhrr/fastui)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [SQLModel Documentation](https://sqlmodel.tiangolo.com)
- [Tailwind CSS](https://tailwindcss.com)
- [HTMX](https://htmx.org)
- [Alpine.js](https://alpinejs.dev)
- [ECharts](https://echarts.apache.org)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

Built with ❤️ by the FastStack Team
