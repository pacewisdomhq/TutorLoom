# SPDX-FileCopyrightText: 2026 Pace Wisdom Solutions Pvt. Ltd.
# SPDX-License-Identifier: Apache-2.0

"""A deactivated account stays deactivated: a password reset token cannot be
used on accept-invite, and an old link cannot turn it into an expired invite."""

import datetime
from datetime import timedelta
from unittest import mock

import pytest
from django.core.signing import TimestampSigner
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import InviteToken, User
from accounts.views import _build_signed_token
from organizations.models import Batch, Organization, OrganizationMember
from organizations.views import BatchStudentViewSet
from rbac.models import Role, UserRole

pytestmark = pytest.mark.django_db
PW = "Passw0rd!xyz"
NEW_PW = "NewStudPass12345!"


def _deactivated(email, status=User.STATUS_ACTIVE):
    u = User.objects.create_user(email=email, password=PW, first_name="F", last_name="L")
    u.is_active = False
    u.status = status
    u.save()
    return u


@pytest.mark.parametrize("status", [User.STATUS_ACTIVE, User.STATUS_INACTIVE])
def test_accept_invite_refuses_deactivated_user(status):
    u = _deactivated(f"stud-{status}@t.com", status)
    r = APIClient().post("/api/auth/accept-invite/",
                         {"token": _build_signed_token(u.email), "password": NEW_PW}, format="json")
    assert r.status_code == 400
    assert "access" not in r.data and "refresh" not in r.data
    u.refresh_from_db()
    assert not u.is_active
    assert u.check_password(PW)


def test_accept_invite_still_activates_pending_invitee():
    u = User.objects.create_user(email="invitee@t.com", password=PW, first_name="F", last_name="L")
    u.is_active = False
    u.status = User.STATUS_PENDING
    u.save()
    r = APIClient().post("/api/auth/accept-invite/",
                         {"token": _build_signed_token(u.email), "password": NEW_PW}, format="json")
    assert r.status_code == 200
    u.refresh_from_db()
    assert u.is_active and u.status == User.STATUS_ACTIVE


def test_old_link_does_not_turn_deactivated_user_into_expired_invite():
    u = _deactivated("old-link@t.com", User.STATUS_INACTIVE)
    signer = TimestampSigner()
    with mock.patch("django.core.signing.time.time", return_value=0):
        token = signer.sign(f"{u.email}:x")
    r = APIClient().get("/api/auth/verify-invite/", {"token": token})
    assert r.status_code == 400
    u.refresh_from_db()
    assert u.status == User.STATUS_INACTIVE


@pytest.mark.parametrize("stored", [User.STATUS_EXPIRED, User.STATUS_PENDING])
def test_reinvited_expired_student_can_accept_fresh_invite(stored):
    """Adding an expired invitee to a batch re-invites them; the fresh link must work."""
    org = Organization.objects.create(name="A", slug="a", contact_email="a@t.com")
    batch = Batch.objects.create(organization=org, name="A1", start_date=datetime.date(2026, 1, 1),
                                 end_date=datetime.date(2026, 12, 31))
    admin = User.objects.create_user(email="adm@t.com", password=PW)
    role = Role.objects.get(name="org_admin")
    OrganizationMember.objects.create(organization=org, user=admin, role=role)
    UserRole.objects.get_or_create(user=admin, role=role)
    old = timezone.now() - timedelta(days=10)
    inv = User.objects.create_user(email="inv@t.com", is_active=False, status=stored, first_name="Old", last_name="N")
    User.objects.filter(pk=inv.pk).update(last_invited_at=old, date_joined=old)

    view = BatchStudentViewSet()
    view.request = mock.Mock(user=admin)
    with mock.patch("accounts.views.send_html_email_via_ses"):
        view._process_single_student({"email": "inv@t.com", "first_name": "New", "last_name": "N"}, org, batch)
    token = InviteToken.objects.filter(user=inv, is_revoked=False).latest("id").token
    r = APIClient().post("/api/auth/accept-invite/", {"token": token, "password": NEW_PW}, format="json")
    assert r.status_code == 200, r.data
