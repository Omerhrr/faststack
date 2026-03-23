"""
FastStack Core Package

This package contains core functionality for FastStack framework.
"""

# Lazy imports to avoid circular dependencies
__all__ = ["forms", "views", "orm", "core"]

def __getattr__(name):
    """Lazy import modules on access."""
    if name == "forms":
        from faststack.faststack import forms as _forms
        return _forms
    elif name == "views":
        from faststack.faststack import views as _views
        return _views
    elif name == "orm":
        from faststack.faststack import orm as _orm
        return _orm
    elif name == "core":
        from faststack.faststack import core as _core
        return _core
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
