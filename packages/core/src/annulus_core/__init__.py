"""Annulus core — configuration, types, and shared utilities."""

from annulus_core.config import AnnulusSettings, ModelProfile, load_settings
from annulus_core.types import ChatMessage

__version__ = "0.1.0"

__all__ = [
    "AnnulusSettings",
    "ChatMessage",
    "ModelProfile",
    "load_settings",
]
