"""Annulus core — configuration, types, and shared utilities."""

from annulus_core.config import AnnulusSettings, ModelProfile, load_settings
from annulus_core.types import ChatMessage, RetrievedChunk

__version__ = "0.2.0"

__all__ = [
    "AnnulusSettings",
    "ChatMessage",
    "ModelProfile",
    "RetrievedChunk",
    "load_settings",
]
