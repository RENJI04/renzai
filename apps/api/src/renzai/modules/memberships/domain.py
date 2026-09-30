"""Framework-free RBAC policy for organization membership."""

from enum import StrEnum


class MembershipRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    SECURITY_ANALYST = "security_analyst"
    DEVELOPER = "developer"
    VIEWER = "viewer"


class MembershipStatus(StrEnum):
    ACTIVE = "active"
    REMOVED = "removed"


ROLE_RANK = {
    MembershipRole.VIEWER: 10,
    MembershipRole.DEVELOPER: 20,
    MembershipRole.SECURITY_ANALYST: 30,
    MembershipRole.ADMIN: 40,
    MembershipRole.OWNER: 50,
}


def can_manage_members(actor: MembershipRole) -> bool:
    return ROLE_RANK[actor] >= ROLE_RANK[MembershipRole.ADMIN]


def can_assign_role(actor: MembershipRole, desired: MembershipRole) -> bool:
    if actor is MembershipRole.OWNER:
        return True
    return actor is MembershipRole.ADMIN and desired is not MembershipRole.OWNER


def can_manage_target(actor: MembershipRole, target: MembershipRole) -> bool:
    if actor is MembershipRole.OWNER:
        return True
    return actor is MembershipRole.ADMIN and target is not MembershipRole.OWNER
