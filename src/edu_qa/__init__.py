"""Offline-first educational question answering with optional AI and speech providers."""

from .history import LearningSession, SessionEntry
from .models import Answer, Evidence
from .service import EducationService

__all__ = ["Answer", "Evidence", "EducationService", "LearningSession", "SessionEntry"]
