"""
FastStack Checks Framework - System validation.

Example:
    from faststack.core.checks import check, Warning, Error, Critical

    @check
    def check_database(app_configs, **kwargs):
        errors = []
        if not database.is_connected():
            errors.append(Critical(
                'Database connection failed',
                id='myapp.E001',
                hint='Check DATABASE_URL environment variable'
            ))
        return errors

    # Run checks
    from faststack.core.checks import run_checks
    errors = run_checks()
"""

from typing import Any, Callable, Dict, List, Optional, Type
from dataclasses import dataclass, field
from enum import Enum
import asyncio


class CheckLevel(Enum):
    """Severity level for check messages."""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


@dataclass
class CheckMessage:
    """
    Base class for check messages.

    Attributes:
        level: Severity level
        msg: Message text
        id: Unique identifier (e.g., 'myapp.E001')
        hint: Optional hint for fixing
        obj: Object this message relates to
    """

    level: CheckLevel
    msg: str
    id: str = ''
    hint: str = ''
    obj: Any = None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.id or self.msg}>"

    def __str__(self) -> str:
        parts = [f"{self.level.name}: {self.msg}"]

        if self.hint:
            parts.append(f"    HINT: {self.hint}")

        if self.id:
            parts.append(f"    ID: {self.id}")

        return '\n'.join(parts)

    def is_serious(self) -> bool:
        """Check if this is a serious error (Error or Critical)."""
        return self.level.value >= CheckLevel.ERROR.value


class Debug(CheckMessage):
    """Debug-level message."""
    def __init__(self, msg: str, **kwargs):
        super().__init__(CheckLevel.DEBUG, msg, **kwargs)


class Info(CheckMessage):
    """Info-level message."""
    def __init__(self, msg: str, **kwargs):
        super().__init__(CheckLevel.INFO, msg, **kwargs)


class Warning(CheckMessage):
    """Warning-level message."""
    def __init__(self, msg: str, **kwargs):
        super().__init__(CheckLevel.WARNING, msg, **kwargs)


class Error(CheckMessage):
    """Error-level message."""
    def __init__(self, msg: str, **kwargs):
        super().__init__(CheckLevel.ERROR, msg, **kwargs)


class Critical(CheckMessage):
    """Critical-level message."""
    def __init__(self, msg: str, **kwargs):
        super().__init__(CheckLevel.CRITICAL, msg, **kwargs)


# Registry of check functions
_check_registry: List[Callable] = []


def check(func: Callable = None, *, tag: str = None):
    """
    Decorator to register a check function.

    Args:
        func: Check function
        tag: Tag for grouping checks

    Returns:
        Decorated function

    Example:
        @check(tag='database')
        def check_database_connection(**kwargs):
            errors = []
            if not db.is_connected():
                errors.append(Error('Database not connected'))
            return errors
    """
    def decorator(f):
        f._check_tag = tag
        _check_registry.append(f)
        return f

    if func is not None:
        return decorator(func)
    return decorator


def register_check(func: Callable, tag: str = None):
    """Register a check function without decorator."""
    func._check_tag = tag
    _check_registry.append(func)


def unregister_check(func: Callable):
    """Unregister a check function."""
    if func in _check_registry:
        _check_registry.remove(func)


async def run_checks(
    app_configs: List = None,
    tags: List[str] = None,
    include_deployment: bool = False
) -> List[CheckMessage]:
    """
    Run all registered checks.

    Args:
        app_configs: App configs to check (default: all)
        tags: Tags to run (default: all)
        include_deployment: Include deployment checks

    Returns:
        List of CheckMessage objects
    """
    errors = []

    for check_func in _check_registry:
        # Filter by tag
        if tags:
            func_tag = getattr(check_func, '_check_tag', None)
            if func_tag and func_tag not in tags:
                continue

        # Run check
        try:
            result = check_func(app_configs=app_configs)

            # Handle async checks
            if asyncio.iscoroutine(result):
                result = await result

            if result:
                errors.extend(result)
        except Exception as e:
            errors.append(Error(
                f"Check {check_func.__name__} raised exception: {e}",
                id='checks.E001'
            ))

    return errors


def run_checks_sync(**kwargs) -> List[CheckMessage]:
    """Synchronous wrapper for run_checks."""
    return asyncio.run(run_checks(**kwargs))


# Built-in checks

@check(tag='settings')
def check_secret_key(**kwargs) -> List[CheckMessage]:
    """Check that SECRET_KEY is set."""
    import os
    errors = []

    secret_key = os.environ.get('SECRET_KEY', '')

    if not secret_key:
        errors.append(Error(
            'SECRET_KEY is not set',
            id='settings.E001',
            hint='Set SECRET_KEY environment variable'
        ))
    elif secret_key == 'your-secret-key-here':
        errors.append(Warning(
            'SECRET_KEY uses default value',
            id='settings.W001',
            hint='Generate a new secret key for production'
        ))
    elif len(secret_key) < 32:
        errors.append(Warning(
            'SECRET_KEY is too short',
            id='settings.W002',
            hint='Use at least 32 characters for security'
        ))

    return errors


@check(tag='database')
def check_database_connection(**kwargs) -> List[CheckMessage]:
    """Check database connection."""
    errors = []

    # This would check actual database connection
    # For now, just return empty
    return errors


@check(tag='security')
def check_debug_mode(**kwargs) -> List[CheckMessage]:
    """Check debug mode settings."""
    import os
    errors = []

    debug = os.environ.get('DEBUG', 'false').lower() == 'true'

    if debug:
        errors.append(Warning(
            'DEBUG mode is enabled',
            id='security.W001',
            hint='Disable DEBUG in production'
        ))

    return errors


@check(tag='security')
def check_allowed_hosts(**kwargs) -> List[CheckMessage]:
    """Check ALLOWED_HOSTS setting."""
    import os
    errors = []

    allowed_hosts = os.environ.get('ALLOWED_HOSTS', '')

    if not allowed_hosts:
        errors.append(Warning(
            'ALLOWED_HOSTS is empty',
            id='security.W002',
            hint='Set ALLOWED_HOSTS in production'
        ))

    return errors


@check(tag='security')
def check_https_settings(**kwargs) -> List[CheckMessage]:
    """Check HTTPS-related settings."""
    import os
    errors = []

    # Check SECURE_SSL_REDIRECT
    secure_ssl = os.environ.get('SECURE_SSL_REDIRECT', 'false').lower() == 'true'
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'

    if not debug and not secure_ssl:
        errors.append(Info(
            'SECURE_SSL_REDIRECT is not set',
            id='security.I001',
            hint='Enable HTTPS redirect in production'
        ))

    return errors


@check(tag='deployment')
def check_deployment(**kwargs) -> List[CheckMessage]:
    """Deployment checks."""
    errors = []

    # Check static files
    # Check media files
    # Check cache backend

    return errors


class CheckCommand:
    """
    Management command for running checks.

    Example:
        python manage.py check
        python manage.py check --tag database
        python manage.py check --deploy
    """

    help = 'Run system checks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tag', '-t',
            action='append',
            dest='tags',
            help='Run checks with these tags'
        )
        parser.add_argument(
            '--deploy',
            action='store_true',
            help='Run deployment checks'
        )
        parser.add_argument(
            '--fail-level',
            default='ERROR',
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            help='Message level to fail on'
        )

    async def handle(self, **options):
        tags = options.get('tags')
        include_deployment = options.get('deploy', False)

        if include_deployment and tags is None:
            tags = ['deployment']
        elif include_deployment:
            tags = list(tags) + ['deployment']

        errors = await run_checks(tags=tags, include_deployment=include_deployment)

        # Print results
        for error in errors:
            print(error)

        # Check fail level
        fail_level = CheckLevel[options.get('fail_level', 'ERROR')]
        serious_errors = [e for e in errors if e.level.value >= fail_level.value]

        if serious_errors:
            print(f"\nFound {len(serious_errors)} serious errors.")
            return 1
        elif errors:
            print(f"\nFound {len(errors)} warnings/info.")
            return 0
        else:
            print("No issues found.")
            return 0
