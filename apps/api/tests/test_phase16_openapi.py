from __future__ import annotations

from renzai.app import create_app
from renzai.core.config import Settings


def test_openapi_documents_existing_auth_boundaries_and_advisory_ai() -> None:
    app = create_app(Settings(app_environment="test", logging_level="CRITICAL"))
    schema = app.openapi()
    assert schema["info"]["version"] == "0.0.0-phase-16"
    schemes = schema["components"]["securitySchemes"]
    assert set(schemes) >= {"ApplicationBearer", "SessionCookie", "CsrfHeader"}
    assert schema["paths"]["/api/v1/analyze"]["post"]["security"] == [{"ApplicationBearer": []}]
    organization_security = schema["paths"]["/api/v1/organizations"]["post"]["security"]
    assert organization_security == [{"SessionCookie": [], "CsrfHeader": []}]
    tags = {item["name"]: item["description"] for item in schema["tags"]}
    assert "never authoritative enforcement" in tags["ai-intelligence"]
