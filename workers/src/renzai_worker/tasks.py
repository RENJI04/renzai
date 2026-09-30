"""A side-effect-free task used only to verify Celery wiring."""
# mypy: disable-error-code=untyped-decorator

from __future__ import annotations

from renzai_worker.celery_app import celery_app


@celery_app.task(name="renzai.diagnostics.echo_request_id")
def echo_request_id(request_id: str) -> dict[str, str]:
    return {"status": "ok", "request_id": request_id}
