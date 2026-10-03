"""Use an existing user session for control-plane incident and AI operations."""

import os

from renzai_sdk import AITaskType, RenzaiSession

with RenzaiSession(
    session_token=os.environ["RENZAI_SESSION_TOKEN"],
    csrf_token=os.environ["RENZAI_CSRF_TOKEN"],
    cookie_name=os.environ.get("RENZAI_SESSION_COOKIE", "renzai_session"),
    base_url=os.environ.get("RENZAI_BASE_URL", "http://localhost:8000"),
) as client:
    incidents = client.list_incidents(os.environ["RENZAI_ORGANIZATION_ID"], limit=10)
    for incident in incidents.items:
        print(incident.incident_id, incident.status)

    if incidents.items:
        client.request_ai(
            os.environ["RENZAI_ORGANIZATION_ID"],
            incidents.items[0].incident_id,
            task_type=AITaskType.INCIDENT_SUMMARY,
            idempotency_key="replace-with-stable-operation-key",
        )
