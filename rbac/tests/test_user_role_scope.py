# SPDX-FileCopyrightText: 2026 Pace Wisdom Solutions Pvt. Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Roles can only be edited by the super admin, and org admins can only manage
org-level roles for plain members of their own organisation."""

import pytest
from rest_framework.test import APIClient

from accounts.models import User
from organizations.models import Organization, OrganizationMember
from rbac.models import Role, UserRole

pytestmark = pytest.mark.django_db
PW = "Passw0rd!xyz"


def _u(email, **kw):
    return User.objects.create_user(email=email, password=PW, first_name="F", last_name="L", **kw)


def client(u):
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.fixture
def w():
    a = Organization.objects.create(name="A", slug="a", contact_email="a@t.com")
    b = Organization.objects.create(name="B", slug="b", contact_email="b@t.com")
    r = {n: Role.objects.get(name=n) for n in ["superadmin", "org_admin", "teacher", "student"]}
    r["admin"] = Role.objects.get_or_create(name="admin")[0]  # not seeded; may exist in old databases
    student = _u("student@t.com")
    OrganizationMember.objects.create(organization=a, user=student, role=r["student"])
    teacher = _u("teacher@t.com")
    OrganizationMember.objects.create(organization=a, user=teacher, role=r["teacher"])
    UserRole.objects.get_or_create(user=teacher, role=r["teacher"])
    org_admin = _u("orgadmin@t.com")
    OrganizationMember.objects.create(organization=a, user=org_admin, role=r["org_admin"])
    other_b = _u("otherb@t.com")
    OrganizationMember.objects.create(organization=b, user=other_b, role=r["student"])
    UserRole.objects.get_or_create(user=other_b, role=r["student"])
    su = User.objects.create_superuser(email="root@t.com", password=PW, first_name="Root", last_name="R")
    UserRole.objects.get_or_create(user=su, role=r["superadmin"])
    # Org admin only through a global UserRole, no org_admin membership.
    global_oa = _u("globaloa@t.com")
    UserRole.objects.get_or_create(user=global_oa, role=r["org_admin"])
    # Demoted org admin: membership role is teacher, the m2m still holds org_admin.
    m2m_oa = _u("m2moa@t.com")
    m = OrganizationMember.objects.create(organization=a, user=m2m_oa, role=r["org_admin"])
    m.role = r["teacher"]
    m.save()
    assert m.roles.filter(name="org_admin").exists()
    return dict(a=a, r=r, student=student, teacher=teacher, org_admin=org_admin, other_b=other_b,
                su=su, global_oa=global_oa, m2m_oa=m2m_oa)


def test_student_cannot_change_roles(w):
    c = client(w["student"])
    sid, oid = w["r"]["student"].pk, w["r"]["org_admin"].pk
    # Delete org_admin, then rename student to org_admin: both steps must be refused.
    assert c.delete(f"/api/roles/{oid}/").status_code == 403
    assert c.patch(f"/api/roles/{sid}/", {"name": "org_admin"}, format="json").status_code == 403
    assert c.put(f"/api/roles/{sid}/", {"name": "org_admin"}, format="json").status_code == 403
    assert c.post("/api/roles/", {"name": "teacher"}, format="json").status_code == 403
    assert Role.objects.get(pk=sid).name == "student"
    assert Role.objects.filter(pk=oid, name="org_admin").exists()


def test_superuser_can_change_roles(w):
    r = client(w["su"]).patch(f"/api/roles/{w['r']['admin'].pk}/", {"description": "x"}, format="json")
    assert r.status_code == 200


@pytest.mark.parametrize("who", ["global_oa", "m2m_oa"])
def test_org_admin_without_membership_role_sees_nothing_and_cannot_assign(w, who):
    c = client(w[who])
    r = c.get("/api/user-roles/")
    assert r.status_code == 200
    rows = r.data["results"] if isinstance(r.data, dict) else r.data
    assert rows == []
    assert c.post("/api/user-roles/", {"user": str(w[who].pk), "role": w["r"]["admin"].pk}, format="json").status_code == 403
    su_row = UserRole.objects.get(user=w["su"], role=w["r"]["superadmin"])
    assert c.delete(f"/api/user-roles/{su_row.pk}/").status_code in (403, 404)
    assert UserRole.objects.filter(pk=su_row.pk).exists()
    assert not UserRole.objects.filter(user=w[who], role=w["r"]["admin"]).exists()


def test_org_admin_cannot_grant_admin(w):
    c = client(w["org_admin"])
    assert c.post("/api/user-roles/", {"user": str(w["teacher"].pk), "role": w["r"]["admin"].pk}, format="json").status_code == 403
    r = c.post("/api/user-roles/update-role/", {"user": w["teacher"].email, "old_role": "teacher", "new_role": "admin"}, format="json")
    assert r.status_code == 403
    assert not UserRole.objects.filter(user=w["teacher"], role=w["r"]["admin"]).exists()
    assert client(w["teacher"]).get("/api/users/").status_code == 403


def test_org_admin_can_grant_org_roles_in_own_org(w):
    r = client(w["org_admin"]).post("/api/user-roles/", {"user": str(w["student"].pk), "role": w["r"]["teacher"].pk}, format="json")
    assert r.status_code == 201


def test_org_admin_list_hides_admin_and_superadmin_rows(w):
    admin = _u("admin@t.com")
    OrganizationMember.objects.create(organization=w["a"], user=admin, role=w["r"]["teacher"])
    UserRole.objects.get_or_create(user=admin, role=w["r"]["admin"])
    r = client(w["org_admin"]).get("/api/user-roles/")
    rows = r.data["results"] if isinstance(r.data, dict) else r.data
    names = {row["role_detail"]["name"] for row in rows}
    assert "admin" not in names and "superadmin" not in names
    assert "teacher" in names


def test_org_admin_cannot_touch_platform_admin_member(w):
    admin = _u("admin@t.com")
    OrganizationMember.objects.create(organization=w["a"], user=admin, role=w["r"]["teacher"])
    UserRole.objects.get_or_create(user=admin, role=w["r"]["admin"])
    row = UserRole.objects.create(user=admin, role=w["r"]["teacher"])
    c = client(w["org_admin"])
    assert c.delete(f"/api/user-roles/{row.pk}/").status_code in (403, 404)
    assert UserRole.objects.filter(pk=row.pk).exists()


def test_superuser_can_grant_admin(w):
    r = client(w["su"]).post("/api/user-roles/", {"user": str(w["teacher"].pk), "role": w["r"]["admin"].pk}, format="json")
    assert r.status_code == 201
