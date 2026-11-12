# SPDX-FileCopyrightText: 2026 Pace Wisdom Solutions Pvt. Ltd.
# SPDX-License-Identifier: Apache-2.0

from accounts.models import User
from rbac.models import UserRole

from .models import OrganizationMember


def can_edit_shared_account(user, org, actor=None):
    """
    True when an org-scoped action may change the shared User row (name, phone,
    is_active) of ``user``.

    A User can belong to several organisations or hold platform privileges, so
    one org's staff must not edit it. Allowed only when ``actor`` acts for
    ``org`` (superuser or active org_admin of it) and the target is a plain
    account that belongs to no other organisation.
    """
    org_id = getattr(org, "pk", org)
    if actor is None or not getattr(actor, "is_authenticated", False):
        return False
    if not actor.is_superuser and not OrganizationMember.objects.filter(
        user=actor, organization_id=org_id, role__name="org_admin", is_active=True
    ).exists():
        return False
    return _is_plain_account(user, org_id)


def _is_plain_account(user, org_id):
    """Not privileged and not a member of any organisation other than ``org_id``."""
    if user.is_superuser or user.is_staff:
        return False
    if UserRole.objects.filter(user=user, role__name="admin").exists():
        return False
    return not OrganizationMember.objects.filter(user=user, is_deleted=False).exclude(
        organization_id=org_id
    ).exists()


def can_reinvite(user, org):
    """True when an org-scoped action may (re)send an invite to an existing user:
    still unaccepted and a plain account tied to no other organisation."""
    return (
        not user.is_active
        and user.status in (User.STATUS_PENDING, User.STATUS_REINVITED, User.STATUS_EXPIRED)
        and _is_plain_account(user, getattr(org, "pk", org))
    )
