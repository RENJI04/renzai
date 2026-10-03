from __future__ import annotations

from renzai.api.analyze import PLAYGROUND_ROLES
from renzai.modules.ai_intelligence.application import AI_CONFIG_EDITORS, AI_REQUESTERS
from renzai.modules.applications.application import APP_EDITORS, OPERATORS
from renzai.modules.incidents.domain import INCIDENT_COMMENTERS, INCIDENT_EDITORS
from renzai.modules.memberships.domain import MembershipRole, can_manage_members
from renzai.modules.policies.application import POLICY_EDITORS
from renzai.modules.providers.application import PROVIDER_EDITORS

ALL_ROLES = frozenset(MembershipRole)
OWNER_ADMIN = frozenset({MembershipRole.OWNER, MembershipRole.ADMIN})
SECURITY_OPERATORS = OWNER_ADMIN | {MembershipRole.SECURITY_ANALYST}
INTEGRATION_EDITORS = OWNER_ADMIN | {MembershipRole.DEVELOPER}


def test_phase13_rbac_matrix_matches_the_authoritative_role_boundaries() -> None:
    matrix = {
        "organization_and_membership_management": frozenset(
            role for role in MembershipRole if can_manage_members(role)
        ),
        "application_environment_and_key_management": frozenset(APP_EDITORS),
        "privacy_and_retention_management": frozenset(OPERATORS),
        "policy_management": frozenset(POLICY_EDITORS),
        "provider_management": frozenset(PROVIDER_EDITORS),
        "incident_status_and_assignment": frozenset(INCIDENT_EDITORS),
        "incident_comment": frozenset(INCIDENT_COMMENTERS),
        "playground_analysis": frozenset(PLAYGROUND_ROLES),
        "analytics_read": ALL_ROLES,
        "ai_provider_management": frozenset(AI_CONFIG_EDITORS),
        "ai_intelligence_request": frozenset(AI_REQUESTERS),
    }
    assert matrix == {
        "organization_and_membership_management": OWNER_ADMIN,
        "application_environment_and_key_management": INTEGRATION_EDITORS,
        "privacy_and_retention_management": OWNER_ADMIN,
        "policy_management": SECURITY_OPERATORS,
        "provider_management": OWNER_ADMIN,
        "incident_status_and_assignment": SECURITY_OPERATORS,
        "incident_comment": SECURITY_OPERATORS | {MembershipRole.DEVELOPER},
        "playground_analysis": INTEGRATION_EDITORS | {MembershipRole.SECURITY_ANALYST},
        "analytics_read": ALL_ROLES,
        "ai_provider_management": OWNER_ADMIN,
        "ai_intelligence_request": SECURITY_OPERATORS,
    }
