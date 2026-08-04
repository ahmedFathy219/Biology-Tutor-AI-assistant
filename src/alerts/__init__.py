# src/alerts/__init__.py

from .buzzer import (
    BuzzerController,
    getBuzzerController,
)

__all__ = [
    "BuzzerController",
    "getBuzzerController",
]