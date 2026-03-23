"""
FastStack Migrations Module

A Django-like migration system built on top of Alembic.
"""

from faststack.migrations.migration import Migration
from faststack.migrations.operations import (
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
from faststack.migrations.autogenerate import MigrationAutodetector
from faststack.migrations.loader import MigrationLoader
from faststack.migrations.executor import MigrationExecutor

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
    "MigrationAutodetector",
    "MigrationLoader",
    "MigrationExecutor",
]
