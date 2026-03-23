#!/usr/bin/env python
"""
FastStack Management Script

This script provides access to FastStack CLI commands.
Run `python manage.py --help` for usage information.
"""

import sys
from pathlib import Path

# Ensure the package is importable
sys.path.insert(0, str(Path(__file__).parent))

from faststack.cli import app

if __name__ == "__main__":
    app()
