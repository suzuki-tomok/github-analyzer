# app/services/__init__.py
from app.services.gemini_client import analyze_commits

__all__ = ["analyze_commits"]
