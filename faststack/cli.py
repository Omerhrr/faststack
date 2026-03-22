"""
FastStack CLI Module

Provides command-line interface for project management, similar to Django's manage.py.
"""

import os
import sys
from pathlib import Path
from typing import Optional

import typer
from typer import Argument, Option
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

app = typer.Typer(
    name="faststack",
    help="FastStack - Async-first Python framework built on FastAPI",
    add_completion=False,
)

console = Console()


def print_banner():
    """Print the FastStack banner."""
    banner = """
    ╔═══════════════════════════════════════════════════════╗
    ║                                                       ║
    ║   ███████╗███████╗██████╗ ███████╗ █████╗ ████████╗██╗║
    ║   ██╔════╝██╔════╝██╔══██╗██╔════╝██╔══██╗╚══██╔══╝██║║
    ║   ███████╗█████╗  ██████╔╝█████╗  ███████║   ██║   ██║║
    ║   ╚════██║██╔══╝  ██╔══██╗██╔══╝  ██╔══██║   ██║   ██║║
    ║   ███████║███████╗██║  ██║███████╗██║  ██║   ██║   ██║║
    ║   ╚══════╝╚══════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝   ╚═╝   ╚═╝║
    ║                                                       ║
    ║   Async-first Python Framework                       ║
    ╚═══════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold blue")


def copy_template(src: Path, dst: Path, context: dict):
    """Copy template file with variable substitution."""
    content = src.read_text()
    for key, value in context.items():
        content = content.replace(f"{{{{ {key} }}}}", value)
    dst.write_text(content)


@app.command()
def startproject(
    project_name: str = Argument(..., help="Name of the project to create"),
    directory: Optional[str] = Option(None, "--dir", "-d", help="Directory to create project in"),
):
    """
    Create a new FastStack project.

    This command creates a new project directory with the complete
    FastStack project structure, including configuration files,
    app directories, and templates.

    Example:
        faststack startproject myproject
        faststack startproject myproject --dir /path/to/projects
    """
    print_banner()

    # Determine target directory
    if directory:
        target_dir = Path(directory) / project_name
    else:
        target_dir = Path.cwd() / project_name

    if target_dir.exists():
        console.print(f"[red]Error: Directory '{target_dir}' already exists[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold green]Creating project:[/] {project_name}")
    console.print(f"[bold green]Location:[/] {target_dir}\n")

    # Create directory structure
    dirs = [
        "",
        "apps",
        "apps/example",
        "templates",
        "templates/pages",
        "templates/components",
        "static",
        "static/css",
        "static/js",
        "static/img",
        "migrations",
    ]

    for dir_path in dirs:
        (target_dir / dir_path).mkdir(parents=True, exist_ok=True)

    # Create pyproject.toml
    pyproject_content = f'''[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{project_name}"
version = "0.1.0"
dependencies = [
    "faststack",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "sqlmodel>=0.0.22",
    "jinja2>=3.1.4",
    "alembic>=1.14.0",
    "python-dotenv>=1.0.1",
]

[project.scripts]
{project_name} = "faststack.cli:app"

[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "I"]
'''
    (target_dir / "pyproject.toml").write_text(pyproject_content)

    # Create .env
    env_content = f'''# {project_name} Environment Configuration

APP_NAME={project_name.title()}
APP_ENV=development
DEBUG=true
SECRET_KEY=change-this-to-a-random-secret-key-in-production

DATABASE_URL=sqlite:///./{project_name}.db

HOST=127.0.0.1
PORT=8000
'''
    (target_dir / ".env").write_text(env_content)

    # Create .gitignore
    gitignore_content = '''__pycache__/
*.py[cod]
.env
*.db
*.sqlite
.venv/
venv/
.idea/
.vscode/
uv.lock
'''
    (target_dir / ".gitignore").write_text(gitignore_content)

    # Create manage.py
    manage_content = '''#!/usr/bin/env python
"""
Management script for the FastStack project.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from faststack.cli import app

if __name__ == "__main__":
    app()
'''
    (target_dir / "manage.py").write_text(manage_content)

    # Create main.py (entry point)
    main_content = '''"""
Main application entry point.
"""
from faststack import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
'''
    (target_dir / "main.py").write_text(main_content)

    # Create base template
    base_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}''' + project_name.title() + '''{% endblock %}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
</head>
<body class="bg-gray-100 min-h-screen">
    <nav class="bg-white shadow">
        <div class="max-w-7xl mx-auto px-4 py-4">
            <a href="/" class="text-xl font-bold text-indigo-600">''' + project_name.title() + '''</a>
        </div>
    </nav>
    <main class="max-w-7xl mx-auto py-6 px-4">
        {% block content %}{% endblock %}
    </main>
</body>
</html>
'''
    (target_dir / "templates" / "base.html").write_text(base_template)

    # Create home page template
    home_template = '''{% extends "base.html" %}

{% block title %}Welcome - ''' + project_name.title() + '''{% endblock %}

{% block content %}
<div class="text-center py-12">
    <h1 class="text-4xl font-bold text-gray-900 mb-4">Welcome to ''' + project_name.title() + '''</h1>
    <p class="text-gray-600 text-lg mb-8">Your FastStack project is ready!</p>
    <div class="space-x-4">
        <a href="/admin/" class="inline-block px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">
            Admin Panel
        </a>
        <a href="/docs" class="inline-block px-6 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300">
            API Docs
        </a>
    </div>
</div>
{% endblock %}
'''
    (target_dir / "templates" / "pages" / "home.html").write_text(home_template)

    # Create example app
    (target_dir / "apps" / "__init__.py").write_text("")
    (target_dir / "apps" / "example" / "__init__.py").write_text("")

    example_models = '''"""
Example app models.
"""
from sqlmodel import Field
from faststack.orm.base import TimestampedModel


class Item(TimestampedModel, table=True):
    """Example Item model."""
    name: str = Field(index=True)
    description: str | None = Field(default=None)
    is_active: bool = Field(default=True)
'''
    (target_dir / "apps" / "example" / "models.py").write_text(example_models)

    example_routes = '''"""
Example app routes.
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from faststack.app import get_templates

router = APIRouter(prefix="/example", tags=["example"])


@router.get("/", response_class=HTMLResponse)
async def example_page(request: Request):
    """Example page."""
    templates = get_templates()
    return templates.TemplateResponse(
        "pages/home.html",
        {"request": request, "title": "Example"},
    )
'''
    (target_dir / "apps" / "example" / "routes.py").write_text(example_routes)

    example_admin = '''"""
Example app admin configuration.
"""
from faststack.admin import register_model
from faststack.apps.example.models import Item


# Register the Item model with admin
register_model(
    Item,
    list_display=["id", "name", "description", "is_active", "created_at"],
    search_fields=["name", "description"],
    list_filter=["is_active"],
    icon="box",
)
'''
    (target_dir / "apps" / "example" / "admin.py").write_text(example_admin)

    # Create alembic.ini
    alembic_content = '''# Alembic configuration

[alembic]
script_location = migrations
prepend_sys_path = .
version_path_separator = os

sqlalchemy.url = sqlite:///./app.db

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
'''
    (target_dir / "alembic.ini").write_text(alembic_content)

    # Create migrations env.py
    (target_dir / "migrations" / "__init__.py").write_text("")

    env_content = '''"""Alembic environment configuration."""
from logging.config import fileConfig
from sqlmodel import SQLModel
from alembic import context
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    from faststack.database import engine

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''
    (target_dir / "migrations" / "env.py").write_text(env_content)

    # Create README
    readme_content = f'''# {project_name}

A FastStack application.

## Quick Start

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Run the development server:
   ```bash
   uv run faststack runserver
   ```

3. Open http://localhost:8000 in your browser.

## Project Structure

```
{project_name}/
├── apps/           # Application modules
├── templates/      # Jinja2 templates
├── static/         # Static files (CSS, JS, images)
├── migrations/     # Database migrations
├── main.py         # Application entry point
├── manage.py       # Management script
└── pyproject.toml  # Project configuration
```

## Commands

- `faststack runserver` - Start development server
- `faststack startapp <name>` - Create a new app
- `faststack makemigrations` - Generate migrations
- `faststack migrate` - Apply migrations
- `faststack createsuperuser` - Create admin user

## Documentation

- [FastStack Docs](https://faststack.dev/docs)
- [FastAPI Docs](https://fastapi.tiangolo.com)
'''
    (target_dir / "README.md").write_text(readme_content)

    # Print success message
    console.print(Panel(
        f"[green]✓[/green] Project '{project_name}' created successfully!\n\n"
        f"[bold]Next steps:[/bold]\n"
        f"  cd {project_name}\n"
        f"  uv sync\n"
        f"  uv run faststack runserver",
        title="[bold green]Success[/bold green]",
        border_style="green",
    ))


@app.command()
def startapp(
    app_name: str = Argument(..., help="Name of the app to create"),
):
    """
    Create a new FastStack app.

    This command creates a new app module in the apps/ directory
    with models, routes, schemas, services, and admin files.

    Example:
        faststack startapp blog
    """
    apps_dir = Path.cwd() / "apps"

    if not apps_dir.exists():
        console.print("[red]Error: No 'apps' directory found. Are you in a FastStack project?[/red]")
        raise typer.Exit(1)

    app_dir = apps_dir / app_name

    if app_dir.exists():
        console.print(f"[red]Error: App '{app_name}' already exists[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold green]Creating app:[/] {app_name}\n")

    # Create app directory
    app_dir.mkdir(parents=True, exist_ok=True)

    # Create __init__.py
    (app_dir / "__init__.py").write_text(f'"""{app_name.title()} app."""\n')

    # Create models.py
    models_content = f'''"""
{app_name.title()} app models.
"""
from sqlmodel import Field
from faststack.orm.base import TimestampedModel


class {app_name.title()}(TimestampedModel, table=True):
    """Example model for {app_name} app."""
    name: str = Field(index=True)
'''
    (app_dir / "models.py").write_text(models_content)

    # Create routes.py
    routes_content = f'''"""
{app_name.title()} app routes.
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from faststack.app import get_templates

router = APIRouter(prefix="/{app_name}", tags=["{app_name}"])


@router.get("/", response_class=HTMLResponse)
async def {app_name}_page(request: Request):
    """{app_name.title()} page."""
    templates = get_templates()
    return templates.TemplateResponse(
        "pages/home.html",
        {{"request": request, "title": "{app_name.title()}"}},
    )
'''
    (app_dir / "routes.py").write_text(routes_content)

    # Create schemas.py
    schemas_content = f'''"""
{app_name.title()} app schemas.
"""
from pydantic import BaseModel


class {app_name.title()}Create(BaseModel):
    """Schema for creating {app_name}."""
    name: str


class {app_name.title()}Update(BaseModel):
    """Schema for updating {app_name}."""
    name: str | None = None


class {app_name.title()}Read(BaseModel):
    """Schema for reading {app_name}."""
    id: int
    name: str

    class Config:
        from_attributes = True
'''
    (app_dir / "schemas.py").write_text(schemas_content)

    # Create services.py
    services_content = f'''"""
{app_name.title()} app services.
"""
from sqlmodel import Session, select
from faststack.apps.{app_name}.models import {app_name.title()}


class {app_name.title()}Service:
    """Service for {app_name} operations."""

    @staticmethod
    def get_all(session: Session) -> list[{app_name.title()}]:
        """Get all {app_name}s."""
        return list(session.exec(select({app_name.title()})).all())

    @staticmethod
    def get_by_id(session: Session, id: int) -> {app_name.title()} | None:
        """Get {app_name} by ID."""
        return session.get({app_name.title()}, id)
'''
    (app_dir / "services.py").write_text(services_content)

    # Create admin.py
    admin_content = f'''"""
{app_name.title()} app admin configuration.
"""
from faststack.admin import register_model
from faststack.apps.{app_name}.models import {app_name.title()}


# Register model with admin
register_model(
    {app_name.title()},
    list_display=["id", "name", "created_at"],
    search_fields=["name"],
    icon="box",
)
'''
    (app_dir / "admin.py").write_text(admin_content)

    console.print(Panel(
        f"[green]✓[/green] App '{app_name}' created successfully!\n\n"
        f"[bold]Files created:[/bold]\n"
        f"  apps/{app_name}/__init__.py\n"
        f"  apps/{app_name}/models.py\n"
        f"  apps/{app_name}/routes.py\n"
        f"  apps/{app_name}/schemas.py\n"
        f"  apps/{app_name}/services.py\n"
        f"  apps/{app_name}/admin.py",
        title="[bold green]Success[/bold green]",
        border_style="green",
    ))


@app.command()
def runserver(
    host: str = Option("127.0.0.1", "--host", "-h", help="Host to bind to"),
    port: int = Option(8000, "--port", "-p", help="Port to bind to"),
    reload: bool = Option(True, "--reload/--no-reload", help="Enable auto-reload"),
):
    """
    Start the development server.

    This command starts a Uvicorn server with the FastStack application.

    Example:
        faststack runserver
        faststack runserver --port 3000
    """
    import subprocess

    console.print(f"\n[bold green]Starting development server...[/]")
    console.print(f"[dim]Host: {host}[/]")
    console.print(f"[dim]Port: {port}[/]")
    console.print(f"[dim]Reload: {reload}[/]\n")

    # Try to find the app
    app_path = "main:app"
    if not Path("main.py").exists():
        app_path = "faststack.app:app"

    cmd = ["uvicorn", app_path, "--host", host, "--port", str(port)]
    if reload:
        cmd.append("--reload")

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped[/]")


@app.command()
def makemigrations(
    message: str = Option("auto", "--message", "-m", help="Migration message"),
):
    """
    Generate new database migrations.

    This command wraps Alembic's revision --autogenerate command.

    Example:
        faststack makemigrations
        faststack makemigrations -m "Add user table"
    """
    import subprocess

    console.print("\n[bold green]Generating migrations...[/]\n")

    try:
        subprocess.run(["alembic", "revision", "--autogenerate", "-m", message])
    except FileNotFoundError:
        console.print("[yellow]Alembic not found. Creating initial migration structure...[/]")
        subprocess.run(["alembic", "init", "migrations"])


@app.command()
def migrate():
    """
    Apply pending database migrations.

    This command wraps Alembic's upgrade head command.

    Example:
        faststack migrate
    """
    import subprocess

    console.print("\n[bold green]Applying migrations...[/]\n")

    try:
        subprocess.run(["alembic", "upgrade", "head"])
    except FileNotFoundError:
        console.print("[red]Alembic not found. Please install alembic.[/]")
        raise typer.Exit(1)


@app.command()
def createsuperuser(
    email: str = Option(..., "--email", "-e", prompt=True, help="Admin email"),
    password: str = Option(..., "--password", "-p", prompt=True, hide_input=True, help="Admin password"),
):
    """
    Create a superuser (admin) account.

    Example:
        faststack createsuperuser
    """
    console.print(f"\n[bold green]Creating superuser...[/]\n")

    try:
        from faststack.database import Session, init_db
        from faststack.auth.models import User
        from faststack.auth.utils import hash_password

        # Initialize database
        init_db()

        # Create superuser
        with Session() as session:
            # Check if user exists
            from sqlmodel import select
            existing = session.exec(select(User).where(User.email == email)).first()

            if existing:
                console.print(f"[red]User with email '{email}' already exists[/]")
                raise typer.Exit(1)

            user = User(
                email=email,
                password_hash=hash_password(password),
                is_admin=True,
                is_active=True,
            )
            session.add(user)
            session.commit()

            console.print(Panel(
                f"[green]✓[/green] Superuser created successfully!\n\n"
                f"[bold]Email:[/bold] {email}\n"
                f"[bold]Admin:[/bold] Yes",
                title="[bold green]Success[/bold green]",
                border_style="green",
            ))

    except ImportError:
        console.print("[red]Error: Could not import FastStack modules.[/]")
        console.print("[yellow]Make sure you're in a FastStack project directory.[/]")
        raise typer.Exit(1)


@app.command()
def version():
    """Show FastStack version."""
    from faststack import __version__
    console.print(f"\n[bold]FastStack[/] version [green]{__version__}[/]\n")


@app.command()
def shell():
    """
    Start an interactive Python shell with FastStack context.

    Example:
        faststack shell
    """
    console.print("\n[bold green]Starting FastStack shell...[/]")
    console.print("[dim]Type 'exit()' to exit[/]\n")

    import code
    from faststack import settings, get_session, init_db

    # Initialize database
    init_db()

    # Create context
    context = {
        "settings": settings,
        "get_session": get_session,
        "init_db": init_db,
    }

    # Try to import models
    try:
        from faststack.loader import app_loader
        app_loader.load_all_apps()
        context["models"] = app_loader.get_all_models()
    except Exception:
        pass

    # Start shell
    shell = code.InteractiveConsole(context)
    shell.interact(banner="FastStack Shell\n")


if __name__ == "__main__":
    app()
