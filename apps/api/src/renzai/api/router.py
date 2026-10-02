"""API composition through the Phase 9 incident-management boundary."""

from fastapi import APIRouter

from renzai.api.analytics import router as analytics_router
from renzai.api.analyze import router as analyze_router
from renzai.api.applications import router as applications_router
from renzai.api.auth import router as auth_router
from renzai.api.gateway import router as gateway_router
from renzai.api.health import router as health_router
from renzai.api.incidents import router as incidents_router
from renzai.api.organizations import router as organizations_router
from renzai.api.policies import router as policies_router
from renzai.api.providers import router as providers_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(analytics_router)
api_router.include_router(incidents_router)
api_router.include_router(auth_router)
api_router.include_router(organizations_router)
api_router.include_router(applications_router)
api_router.include_router(analyze_router)
api_router.include_router(policies_router)
api_router.include_router(providers_router)

# Health/readiness are intentionally exposed at the root per the Phase 3 contract.
root_router = APIRouter()
root_router.include_router(health_router)
root_router.include_router(gateway_router)
