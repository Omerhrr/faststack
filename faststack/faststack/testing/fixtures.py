"""
Test Fixtures

Loading and creating test fixtures.
"""

import json
from pathlib import Path
from typing import Any


def load_fixture(fixture_path: str, session: Any | None = None) -> list[Any]:
    """
    Load a fixture file into the database.
    
    Fixtures are JSON files containing model data.
    
    Args:
        fixture_path: Path to fixture file (relative to fixtures dir)
        session: Database session
    
    Returns:
        List of created objects
    
    Example:
        # fixtures/users.json
        [
            {
                "model": "auth.User",
                "pk": 1,
                "fields": {
                    "email": "test@example.com",
                    "name": "Test User"
                }
            }
        ]
        
        # In test
        load_fixture('users.json')
    """
    # Find fixture file
    fixture_file = _find_fixture(fixture_path)
    if not fixture_file:
        raise FileNotFoundError(f"Fixture not found: {fixture_path}")
    
    # Load JSON
    with open(fixture_file, 'r') as f:
        data = json.load(f)
    
    # Get session
    if session is None:
        from faststack.database import Session
        session = Session()
    
    created_objects = []
    
    for item in data:
        model_name = item.get('model')
        pk = item.get('pk')
        fields = item.get('fields', {})
        
        # Get model class
        model_class = _get_model(model_name)
        if model_class is None:
            raise ValueError(f"Unknown model: {model_name}")
        
        # Create object
        obj = model_class(**fields)
        if pk:
            obj.id = pk
        
        session.add(obj)
        created_objects.append(obj)
    
    session.commit()
    
    # Refresh objects
    for obj in created_objects:
        session.refresh(obj)
    
    return created_objects


async def load_fixtures(fixtures: list[str], session: Any | None = None) -> list[Any]:
    """
    Load multiple fixtures.
    
    Args:
        fixtures: List of fixture file paths
        session: Database session
    
    Returns:
        List of created objects
    """
    all_objects = []
    
    for fixture in fixtures:
        objects = load_fixture(fixture, session)
        all_objects.extend(objects)
    
    return all_objects


def create_fixture(model: str, data: dict[str, Any], session: Any | None = None) -> Any:
    """
    Create a single fixture object.
    
    Args:
        model: Model name (e.g., 'auth.User')
        data: Field data
        session: Database session
    
    Returns:
        Created object
    """
    if session is None:
        from faststack.database import Session
        session = Session()
    
    model_class = _get_model(model)
    if model_class is None:
        raise ValueError(f"Unknown model: {model}")
    
    obj = model_class(**data)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    
    return obj


def _find_fixture(fixture_path: str) -> Path | None:
    """Find a fixture file in known locations."""
    from faststack.config import settings
    
    # Search paths
    search_paths = [
        Path.cwd() / 'fixtures',
        Path.cwd() / 'tests' / 'fixtures',
        getattr(settings, 'FIXTURES_DIR', None),
    ]
    
    for search_path in search_paths:
        if search_path is None:
            continue
        
        search_path = Path(search_path)
        full_path = search_path / fixture_path
        
        if full_path.exists():
            return full_path
    
    return None


def _get_model(model_name: str) -> type | None:
    """Get a model class by name."""
    # Map of model names to classes
    model_map = {
        'auth.User': 'faststack.auth.models:User',
        'auth.Group': 'faststack.auth.models:Group',
        'auth.Permission': 'faststack.auth.models:Permission',
        'auth.ApiToken': 'faststack.auth.models:ApiToken',
        'auth.PasswordResetToken': 'faststack.auth.models:PasswordResetToken',
    }
    
    if model_name in model_map:
        import importlib
        module_path, class_name = model_map[model_name].rsplit(':', 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name, None)
    
    # Try to import from apps
    if '.' in model_name:
        app, model = model_name.split('.', 1)
        try:
            import importlib
            module = importlib.import_module(f'apps.{app}.models')
            return getattr(module, model, None)
        except ImportError:
            pass
    
    return None


# Built-in test fixtures

def create_test_user(
    email: str = 'test@example.com',
    password: str = 'password123',
    name: str = 'Test User',
    **kwargs,
) -> Any:
    """
    Create a test user.
    
    Args:
        email: User email
        password: User password
        name: User name
        **kwargs: Additional fields
    
    Returns:
        User instance
    """
    from faststack.database import Session
    from faststack.auth.models import User
    from faststack.auth.utils import hash_password
    
    session = Session()
    
    user = User(
        email=email,
        password_hash=hash_password(password),
        name=name,
        is_active=True,
        **kwargs,
    )
    
    session.add(user)
    session.commit()
    session.refresh(user)
    
    return user


def create_test_admin(
    email: str = 'admin@example.com',
    password: str = 'admin123',
    **kwargs,
) -> Any:
    """
    Create a test admin user.
    
    Args:
        email: Admin email
        password: Admin password
        **kwargs: Additional fields
    
    Returns:
        User instance
    """
    return create_test_user(
        email=email,
        password=password,
        name='Admin User',
        is_admin=True,
        is_staff=True,
        **kwargs,
    )


def create_test_group(name: str = 'Test Group', **kwargs) -> Any:
    """
    Create a test group.
    
    Args:
        name: Group name
        **kwargs: Additional fields
    
    Returns:
        Group instance
    """
    from faststack.database import Session
    from faststack.auth.models import Group
    
    session = Session()
    
    group = Group(name=name, **kwargs)
    session.add(group)
    session.commit()
    session.refresh(group)
    
    return group


# Fixture decorators

def with_fixtures(*fixture_paths: str):
    """
    Decorator to load fixtures for a test.
    
    Example:
        @with_fixtures('users.json', 'posts.json')
        async def test_something(self):
            # fixtures are loaded
            pass
    """
    def decorator(func):
        async def wrapper(self, *args, **kwargs):
            await load_fixtures(list(fixture_paths))
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator


def with_user(**user_kwargs):
    """
    Decorator to create a test user.
    
    Example:
        @with_user(email='test@test.com')
        async def test_authenticated(self, user):
            # user is created and passed to test
            pass
    """
    def decorator(func):
        async def wrapper(self, *args, **kwargs):
            user = create_test_user(**user_kwargs)
            return await func(self, user, *args, **kwargs)
        return wrapper
    return decorator


def with_admin(**admin_kwargs):
    """
    Decorator to create a test admin.
    
    Example:
        @with_admin()
        async def test_admin_access(self, admin):
            # admin user is available
            pass
    """
    def decorator(func):
        async def wrapper(self, *args, **kwargs):
            admin = create_test_admin(**admin_kwargs)
            return await func(self, admin, *args, **kwargs)
        return wrapper
    return decorator
