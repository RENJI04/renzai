"""ASGI entry point. Use `renzai.app.create_app` in tests or other hosts."""

from renzai.app import create_app

app = create_app()
