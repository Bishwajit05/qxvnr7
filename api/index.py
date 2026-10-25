"""Vercel's Python entrypoint exports the same ASGI app used by Docker."""

from backend.app.main import app

__all__ = ["app"]
