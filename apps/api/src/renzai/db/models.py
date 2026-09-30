"""Import all current models so Alembic sees module-owned metadata."""

from renzai.modules.api_keys.models import ApplicationApiKey
from renzai.modules.applications.models import Application
from renzai.modules.audit.models import AccountSecurityEvent, AuditEvent
from renzai.modules.auth.models import EmailVerificationToken, PasswordResetToken, Session
from renzai.modules.environments.models import Environment
from renzai.modules.gateway.models import GatewayProviderCall
from renzai.modules.memberships.models import Invitation, Membership
from renzai.modules.organizations.models import Organization
from renzai.modules.policies.models import Policy, PolicyCondition, PolicyDecision, PolicyVersion
from renzai.modules.providers.models import ProviderConfiguration
from renzai.modules.risk.models import RiskContribution, RiskProfile, RiskProfileVersion
from renzai.modules.security.models import AnalysisResult, Finding, SecurityEvent
from renzai.modules.users.models import PasswordCredential, User

__all__ = [
    "AccountSecurityEvent",
    "AuditEvent",
    "AnalysisResult",
    "Application",
    "ApplicationApiKey",
    "EmailVerificationToken",
    "Environment",
    "GatewayProviderCall",
    "Finding",
    "Invitation",
    "Membership",
    "Organization",
    "PasswordCredential",
    "PasswordResetToken",
    "Policy",
    "PolicyCondition",
    "PolicyDecision",
    "PolicyVersion",
    "ProviderConfiguration",
    "RiskContribution",
    "RiskProfile",
    "RiskProfileVersion",
    "Session",
    "SecurityEvent",
    "User",
]
