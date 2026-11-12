"""/api/users/ must not let any signed-in user list or edit other accounts, and
org staff must not reinvite shared accounts."""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from organizations.models import Organization, OrganizationMember
from rbac.models import Role

pytestmark = pytest.mark.django_db
PW = "Passw0rd!xyz"


def _u(email, **kw):
    return User.objects.create_user(email=email, password=PW, first_name="F", last_name="L", **kw)


def client(u):
    c = APIClient()
    c.force_authenticate(user=u)
    return c


def fresh(u):
    return User._base_manager.get(pk=u.pk)


@pytest.fixture
def w():
    org = Organization.objects.create(name="A", slug="a", contact_email="a@t.com")
    student = _u("student@t.com")
    OrganizationMember.objects.create(organization=org, user=student, role=Role.objects.get(name="student"))
    other = _u("other@t.com")
    OrganizationMember.objects.create(organization=org, user=other, role=Role.objects.get(name="student"))
    teacher = _u("teacher@t.com")
    OrganizationMember.objects.create(organization=org, user=teacher, role=Role.objects.get(name="teacher"))
    su = User.objects.create_superuser(email="root@t.com", password=PW, first_name="Root", last_name="R")
    return dict(org=org, student=student, other=other, teacher=teacher, su=su)


def detail(u):
    return reverse("user-detail", kwargs={"pk": str(u.id)})


def test_student_cannot_list_users(w):
    assert client(w["student"]).get(reverse("user-list")).status_code == 403


def test_student_cannot_read_another_user(w):
    assert client(w["student"]).get(detail(w["other"])).status_code == 403


def test_user_reads_self(w):
    assert client(w["student"]).get(detail(w["student"])).status_code == 200


def test_student_cannot_deactivate_super_admin(w):
    r = client(w["student"]).patch(detail(w["su"]), {"is_active": False}, format="json")
    assert r.status_code == 403
    assert fresh(w["su"]).is_active is True


def test_student_cannot_rename_another_user(w):
    r = client(w["student"]).patch(detail(w["other"]), {"first_name": "Pwned"}, format="json")
    assert r.status_code == 403
    assert fresh(w["other"]).first_name == "F"


def test_user_updates_own_name(w):
    r = client(w["student"]).patch(detail(w["student"]), {"first_name": "New"}, format="json")
    assert r.status_code == 200
    assert fresh(w["student"]).first_name == "New"


def test_user_saves_profile_with_unchanged_is_active(w):
    r = client(w["student"]).patch(detail(w["student"]), {"first_name": "New", "is_active": True}, format="json")
    assert r.status_code == 200


def test_user_cannot_change_own_is_active(w):
    client(w["student"]).patch(detail(w["student"]), {"is_active": False}, format="json")
    client(w["student"]).patch(reverse("user-me"), {"is_active": False}, format="json")
    assert fresh(w["student"]).is_active is True


def test_superuser_updates_any_user(w):
    r = client(w["su"]).patch(detail(w["other"]), {"first_name": "Fixed"}, format="json")
    assert r.status_code == 200
    assert fresh(w["other"]).first_name == "Fixed"
    assert client(w["su"]).get(reverse("user-list")).status_code == 200


def test_teacher_cannot_reinvite(w):
    p = _u("pend@t.com", is_active=False, status=User.STATUS_PENDING)
    OrganizationMember.objects.create(organization=w["org"], user=p, role=Role.objects.get(name="student"))
    r = client(w["teacher"]).post(reverse("reinvite", kwargs={"identifier": "pend@t.com"}))
    assert r.status_code == 403
