"""
FastStack Management Commands Framework - Django-like BaseCommand.

Example:
    # myapp/management/commands/cleanup.py
    from faststack.core.management import BaseCommand

    class Command(BaseCommand):
        help = 'Cleanup old sessions and logs'

        def add_arguments(self, parser):
            parser.add_argument('--days', type=int, default=30)
            parser.add_argument('--dry-run', action='store_true')

        async def handle(self, *args, **options):
            days = options['days']
            dry_run = options['dry_run']
            self.stdout.write(f'Cleaning up data older than {days} days...')
            # ... cleanup logic

    # Run: python manage.py cleanup --days=60 --dry-run
"""

from typing import Any, Callable, Dict, List, Optional, Type
import argparse
import sys
import os
import asyncio
import importlib
import inspect
from pathlib import Path


class CommandError(Exception):
    """Exception raised during command execution."""
    pass


class CommandParser(argparse.ArgumentParser):
    """Custom argument parser for management commands."""

    def error(self, message: str):
        """Override to raise CommandError instead of sys.exit."""
        self.print_help(sys.stderr)
        raise CommandError(f"Error: {message}")


class OutputWrapper:
    """
    Wrapper for stdout/stderr with styling support.
    """

    def __init__(self, out=sys.stdout, ending='\n'):
        self._out = out
        self.ending = ending
        self.style_func = None

    def __getattr__(self, name: str) -> Any:
        return getattr(self._out, name)

    def write(self, msg: str, style_func: Callable = None, ending: str = None):
        """Write a message."""
        if style_func and self.style_func:
            msg = style_func(msg)

        if ending is None:
            ending = self.ending

        if isinstance(msg, bytes):
            msg = msg.decode()

        if ending and not msg.endswith(ending):
            msg += ending

        self._out.write(msg)

    def flush(self):
        """Flush output."""
        if hasattr(self._out, 'flush'):
            self._out.flush()


class BaseCommand:
    """
    Base class for management commands.

    Subclass this to create custom management commands.

    Attributes:
        help: Short description of the command
        requires_system_checks: Whether to run system checks
        requires_migrations: Whether migrations must be applied
        stealth_options: Options that don't appear in help
        suppressed_base_arguments: Base args to hide from help

    Example:
        class Command(BaseCommand):
            help = 'Import data from CSV'

            def add_arguments(self, parser):
                parser.add_argument('file', type=str)
                parser.add_argument('--delimiter', default=',')

            async def handle(self, *args, **options):
                filename = options['file']
                # ... import logic
    """

    # Metadata
    help: str = ''
    missing_args_message: str = ''

    # System requirements
    requires_system_checks: bool = True
    requires_migrations: bool = False

    # Option handling
    stealth_options: tuple = ()
    suppressed_base_arguments: tuple = ()

    # Output streams
    stdout: OutputWrapper = None
    stderr: OutputWrapper = None

    # Style functions
    style: 'Style' = None

    def __init__(self, stdout=None, stderr=None, no_color=False):
        """
        Initialize command.

        Args:
            stdout: Output stream for stdout
            stderr: Output stream for stderr
            no_color: Disable colored output
        """
        self.stdout = OutputWrapper(stdout or sys.stdout)
        self.stderr = OutputWrapper(stderr or sys.stderr)
        self.no_color = no_color
        self.style = Style(no_color=no_color)

    def create_parser(self, prog_name: str, subcommand: str) -> CommandParser:
        """
        Create argument parser.

        Args:
            prog_name: Program name
            subcommand: Subcommand name

        Returns:
            CommandParser instance
        """
        parser = CommandParser(
            prog=f"{prog_name} {subcommand}",
            description=self.help or None,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        # Add standard arguments
        parser.add_argument(
            '--verbosity', '-v',
            type=int,
            default=1,
            choices=[0, 1, 2, 3],
            help='Verbosity level: 0=minimal, 1=normal, 2=verbose, 3=debug'
        )

        parser.add_argument(
            '--settings',
            help='Path to settings module'
        )

        parser.add_argument(
            '--traceback',
            action='store_true',
            help='Show full traceback on error'
        )

        parser.add_argument(
            '--no-color',
            action='store_true',
            help='Disable colored output'
        )

        # Add custom arguments
        self.add_arguments(parser)

        return parser

    def add_arguments(self, parser: CommandParser):
        """
        Add custom command arguments.

        Override this method to add command-specific arguments.

        Args:
            parser: CommandParser instance

        Example:
            def add_arguments(self, parser):
                parser.add_argument('file', type=str, help='Input file')
                parser.add_argument('--dry-run', action='store_true')
                parser.add_argument('--limit', type=int, default=100)
        """
        pass

    def print_help(self, prog_name: str, subcommand: str):
        """Print help message."""
        parser = self.create_parser(prog_name, subcommand)
        parser.print_help()

    def run_from_argv(self, argv: List[str]):
        """
        Run command from command line arguments.

        Args:
            argv: Command line arguments
        """
        parser = self.create_parser(argv[0], argv[1])

        try:
            options = parser.parse_args(argv[2:])
        except CommandError:
            raise

        # Handle no_color
        if options.no_color:
            self.style = Style(no_color=True)

        # Execute
        try:
            output = self.handle(*options._get_args(), **options._get_kwargs())

            if output:
                self.stdout.write(output)
        except CommandError as e:
            if options.traceback:
                raise
            self.stderr.write(str(e), style_func=self.style.ERROR)
            sys.exit(1)
        except KeyboardInterrupt:
            self.stdout.write('\n')
            sys.exit(130)
        except Exception as e:
            if options.traceback:
                raise
            self.stderr.write(f"Error: {e}\n", style_func=self.style.ERROR)
            sys.exit(1)

    def execute(self, *args, **options):
        """
        Execute the command.

        This method handles system checks and migrations before calling handle().

        Args:
            *args: Positional arguments
            **options: Keyword arguments

        Returns:
            Command output
        """
        # Run system checks
        if self.requires_system_checks:
            self.check()

        # Check migrations
        if self.requires_migrations:
            self.check_migrations()

        # Call handle
        output = self.handle(*args, **options)

        return output

    def handle(self, *args, **options):
        """
        Main command logic.

        Override this method to implement command functionality.

        Args:
            *args: Positional arguments
            **options: Keyword arguments

        Returns:
            Optional output string
        """
        raise NotImplementedError('Subclasses must implement handle()')

    async def ahandle(self, *args, **options):
        """
        Async main command logic.

        Override this for async commands.

        Args:
            *args: Positional arguments
            **options: Keyword arguments
        """
        raise NotImplementedError('Subclasses must implement ahandle()')

    def check(self):
        """Run system checks."""
        # Would integrate with FastStack's check framework
        pass

    def check_migrations(self):
        """Check for unapplied migrations."""
        # Would check migration status
        pass

    # Utility methods

    def confirm(self, message: str, default: bool = False) -> bool:
        """
        Ask for user confirmation.

        Args:
            message: Confirmation message
            default: Default value if user just presses Enter

        Returns:
            User's choice
        """
        default_str = 'Y/n' if default else 'y/N'
        prompt = f"{message} [{default_str}]: "

        try:
            response = input(prompt).strip().lower()

            if not response:
                return default

            return response in ('y', 'yes')
        except EOFError:
            return default

    def prompt(self, message: str, default: str = None) -> str:
        """
        Prompt user for input.

        Args:
            message: Prompt message
            default: Default value

        Returns:
            User input
        """
        if default:
            prompt = f"{message} [{default}]: "
        else:
            prompt = f"{message}: "

        try:
            response = input(prompt).strip()
            return response if response else default
        except EOFError:
            return default

    def info(self, message: str):
        """Print info message."""
        self.stdout.write(message, style_func=self.style.SUCCESS)

    def warning(self, message: str):
        """Print warning message."""
        self.stdout.write(message, style_func=self.style.WARNING)

    def error(self, message: str):
        """Print error message."""
        self.stderr.write(message, style_func=self.style.ERROR)

    def notice(self, message: str):
        """Print notice message."""
        self.stdout.write(message, style_func=self.style.NOTICE)


class Style:
    """
    Style functions for output coloring.
    """

    # ANSI color codes
    COLORS = {
        'black': 30,
        'red': 31,
        'green': 32,
        'yellow': 33,
        'blue': 34,
        'magenta': 35,
        'cyan': 36,
        'white': 37,
    }

    # ANSI style codes
    STYLES = {
        'bold': 1,
        'dim': 2,
        'underline': 4,
        'blink': 5,
        'reverse': 7,
    }

    def __init__(self, no_color: bool = False):
        self.no_color = no_color

    def _colorize(self, text: str, color: str = None, *styles: str) -> str:
        """Apply color and style to text."""
        if self.no_color or not sys.stdout.isatty():
            return text

        codes = []

        for style in styles:
            if style in self.STYLES:
                codes.append(str(self.STYLES[style]))

        if color in self.COLORS:
            codes.append(str(self.COLORS[color]))

        if codes:
            return f"\033[{';'.join(codes)}m{text}\033[0m"
        return text

    def SUCCESS(self, text: str) -> str:
        """Green text for success messages."""
        return self._colorize(text, 'green')

    def WARNING(self, text: str) -> str:
        """Yellow text for warnings."""
        return self._colorize(text, 'yellow')

    def ERROR(self, text: str) -> str:
        """Red text for errors."""
        return self._colorize(text, 'red', 'bold')

    def NOTICE(self, text: str) -> str:
        """Cyan text for notices."""
        return self._colorize(text, 'cyan')

    def HTTP_INFO(self, text: str) -> str:
        """Style for HTTP info."""
        return self._colorize(text, 'cyan')

    def HTTP_SUCCESS(self, text: str) -> str:
        """Style for HTTP success."""
        return self._colorize(text, 'green')

    def HTTP_REDIRECT(self, text: str) -> str:
        """Style for HTTP redirect."""
        return self._colorize(text, 'yellow')

    def HTTP_NOT_MODIFIED(self, text: str) -> str:
        """Style for 304 responses."""
        return self._colorize(text, 'cyan')

    def HTTP_BAD_REQUEST(self, text: str) -> str:
        """Style for 400 responses."""
        return self._colorize(text, 'yellow', 'bold')

    def HTTP_NOT_FOUND(self, text: str) -> str:
        """Style for 404 responses."""
        return self._colorize(text, 'yellow')

    def HTTP_SERVER_ERROR(self, text: str) -> str:
        """Style for 5xx responses."""
        return self._colorize(text, 'red', 'bold')

    def MIGRATE_HEADING(self, text: str) -> str:
        """Style for migration headings."""
        return self._colorize(text, 'cyan', 'bold')

    def MIGRATE_LABEL(self, text: str) -> str:
        """Style for migration labels."""
        return self._colorize(text, 'green')

    def SQL_FIELD(self, text: str) -> str:
        """Style for SQL field names."""
        return self._colorize(text, 'green')

    def SQL_COLTYPE(self, text: str) -> str:
        """Style for SQL column types."""
        return self._colorize(text, 'blue')

    def SQL_KEYWORD(self, text: str) -> str:
        """Style for SQL keywords."""
        return self._colorize(text, 'cyan')

    def URL(self, text: str) -> str:
        """Style for URLs."""
        return self._colorize(text, 'green', 'underline')


class CommandRegistry:
    """
    Registry for management commands.

    Discovers and loads commands from installed apps.
    """

    def __init__(self):
        self._commands: Dict[str, Type[BaseCommand]] = {}

    def register(self, name: str, command_class: Type[BaseCommand]):
        """Register a command."""
        self._commands[name] = command_class

    def get_command(self, name: str) -> Optional[Type[BaseCommand]]:
        """Get a command by name."""
        return self._commands.get(name)

    def get_commands(self) -> Dict[str, Type[BaseCommand]]:
        """Get all registered commands."""
        return self._commands.copy()

    def discover_commands(self, app_paths: List[str]):
        """
        Discover commands from app directories.

        Looks for management/commands/*.py files.

        Args:
            app_paths: List of app module paths
        """
        for app_path in app_paths:
            commands_dir = Path(app_path) / 'management' / 'commands'

            if commands_dir.exists():
                for command_file in commands_dir.glob('*.py'):
                    if command_file.name.startswith('_'):
                        continue

                    command_name = command_file.stem

                    try:
                        # Import the command module
                        module_path = f"{app_path}.management.commands.{command_name}"
                        module = importlib.import_module(module_path)

                        # Find Command class
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if (inspect.isclass(attr) and
                                issubclass(attr, BaseCommand) and
                                attr is not BaseCommand):
                                self.register(command_name, attr)
                                break
                    except Exception:
                        pass


# Global registry
registry = CommandRegistry()


# Built-in commands
class HelpCommand(BaseCommand):
    """Show help for commands."""

    help = 'Show available commands'

    def handle(self, *args, **options):
        commands = registry.get_commands()
        output = ['Available commands:', '']

        for name, cmd_class in sorted(commands.items()):
            help_text = cmd_class.help or ''
            output.append(f"  {name:20s} {help_text}")

        return '\n'.join(output)


class RunServerCommand(BaseCommand):
    """Run development server."""

    help = 'Start the development server'

    def add_arguments(self, parser):
        parser.add_argument('address', nargs='?', default='127.0.0.1:8000')
        parser.add_argument('--reload', action='store_true', help='Enable auto-reload')

    async def handle(self, *args, **options):
        import uvicorn

        address = options['address']
        host, port = address.split(':') if ':' in address else (address, 8000)

        self.stdout.write(f"Starting development server at http://{host}:{port}/\n")

        await uvicorn.run(
            'app:app',
            host=host,
            port=int(port),
            reload=options['reload']
        )


class ShellCommand(BaseCommand):
    """Start interactive shell."""

    help = 'Start an interactive Python shell'

    def add_arguments(self, parser):
        parser.add_argument('--ipython', action='store_true', help='Use IPython')
        parser.add_argument('--bpython', action='store_true', help='Use bpython')

    def handle(self, *args, **options):
        import code
        import importlib

        # Try to import app models
        try:
            from app import models
            imported_objects = {'models': models}
        except ImportError:
            imported_objects = {}

        # Try different shells
        if options['ipython']:
            try:
                from IPython import start_ipython
                start_ipython(argv=[], user_ns=imported_objects)
                return
            except ImportError:
                pass

        if options['bpython']:
            try:
                from bpython import embed
                embed(imported_objects)
                return
            except ImportError:
                pass

        # Default to standard Python shell
        shell = code.InteractiveConsole(imported_objects)
        shell.interact()


# Register built-in commands
registry.register('help', HelpCommand)
registry.register('runserver', RunServerCommand)
registry.register('shell', ShellCommand)
