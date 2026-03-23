"""
FastStack Migrations Module

A Django-like migration system built on top of Alembic.
"""

from faststack.faststack.migrations.migration import Migration
from faststack.faststack.migrations.operations import (
    CreateModel,
    DeleteModel,
    RenameModel,
    AddField,
    RemoveField,
    RenameField,
    AlterField,
    AddIndex,
    RemoveIndex,
    RunPython,
    RunSQL,
)

__all__ = [
    "Migration",
    "CreateModel",
    "DeleteModel",
    "RenameModel",
    "AddField",
    "RemoveField",
    "RenameField",
    "AlterField",
    "AddIndex",
    "RemoveIndex",
    "RunPython",
    "RunSQL",
]
