# SPDX-FileCopyrightText: 2026 Pace Wisdom Solutions Pvt. Ltd.
# SPDX-License-Identifier: Apache-2.0

"""A teacher must not turn staff into students and then manage them through the student endpoints."""

from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient

from curriculum.models import Course
from organizations.models import Batch, BatchStudent, Organization, OrganizationMember
from rbac.models import Role

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def w():
    org = Organization.objects.create(name="A", slug="a", contact_email="a@t.com")
    r = {n: Role.objects.get_or_create(name=n)[0] for n in ["org_admin", "teacher", "student"]}
    users = {n: User.objects.create_user(email=f"{n}@t.com", first_name=n) for n in ["admin", "teacher", "other", "student"]}
    members = {
        "admin": OrganizationMember.objects.create(organization=org, user=users["admin"], role=r["org_admin"]),
        "teacher": OrganizationMember.objects.create(organization=org, user=users["teacher"], role=r["teacher"]),
        "other": OrganizationMember.objects.create(organization=org, user=users["other"], role=r["teacher"]),
        "student": OrganizationMember.objects.create(organization=org, user=users["student"], role=r["student"]),
    }
    batch = Batch.objects.create(organization=org, name="B1", start_date="2026-01-01", end_date="2026-12-31")
    course = Course.objects.create(organization=org, title="C1")
    batch.courses.add(course)
    return dict(org=org, r=r, users=users, members=members, batch=batch, course=course)


def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def batch_add(w, actor, email):
    url = reverse("organization-batch-students-list", kwargs={"org_pk": w["org"].id, "batch_pk": w["batch"].id})
    return client(actor).post(url, {"students": [{"email": email, "first_name": "X"}]}, format="json")


def student_add(w, actor, email):
    url = reverse("organization-students-list", kwargs={"org_pk": w["org"].id})
    return client(actor).post(url, {"email": email, "first_name": "X"}, format="json")


def student_upload(w, actor, email):
    url = reverse("organization-students-bulk-upload", kwargs={"org_pk": w["org"].id})
    f = SimpleUploadedFile("s.csv", f"email,first_name\n{email},X\n".encode(), content_type="text/csv")
    return client(actor).post(url, {"file": f}, format="multipart")


def batch_upload(w, actor, email):
    url = reverse("organization-batch-students-bulk-upload", kwargs={"org_pk": w["org"].id, "batch_pk": w["batch"].id})
    f = SimpleUploadedFile("s.csv", f"email,first_name\n{email},X\n".encode(), content_type="text/csv")
    return client(actor).post(url, {"file": f}, format="multipart")


def student_url(w, user):
    return reverse("organization-students-detail", kwargs={"org_pk": w["org"].id, "pk": str(user.id)})


def role_names(member):
    return set(member.roles.values_list("name", flat=True))


@pytest.mark.parametrize("add", [batch_add, student_add, student_upload, batch_upload])
@pytest.mark.parametrize("target", ["admin", "teacher", "other"])
def test_teacher_cannot_enrol_staff_as_student(w, add, target):
    before = role_names(w["members"][target])
    with mock.patch("organizations.views._send_invite_link") as invite:
        res = add(w, w["users"]["teacher"], w["users"][target].email)
    assert res.status_code == 400
    assert role_names(w["members"][target]) == before
    assert not BatchStudent.objects.filter(student=w["members"][target]).exists()
    invite.assert_not_called()


def test_teacher_cannot_enrol_inactive_staff_as_student(w):
    OrganizationMember.objects.filter(pk=w["members"]["admin"].pk).update(is_active=False)
    assert batch_add(w, w["users"]["teacher"], "admin@t.com").status_code == 400
    assert "student" not in role_names(w["members"]["admin"])


def test_org_admin_can_enrol_teacher_as_learner(w):
    assert batch_add(w, w["users"]["admin"], "other@t.com").status_code == 201
    assert BatchStudent.objects.filter(batch=w["batch"], student=w["members"]["other"]).exists()
    assert OrganizationMember.objects.get(pk=w["members"]["other"].pk).role.name == "teacher"


def test_staff_with_extra_student_role_is_not_managed_as_student(w):
    for name in ("admin", "teacher"):
        w["members"][name].roles.add(w["r"]["student"])
    t = client(w["users"]["teacher"])

    assert t.patch(student_url(w, w["users"]["admin"]), {"is_active": False}, format="json").status_code == 404
    assert t.delete(student_url(w, w["users"]["admin"])).status_code == 404
    assert t.patch(student_url(w, w["users"]["teacher"]), {"course_id": w["course"].id}, format="json").status_code == 404
    admin = OrganizationMember.objects.get(pk=w["members"]["admin"].pk)
    assert admin.is_active and not admin.is_deleted
    assert OrganizationMember.objects.get(pk=w["members"]["teacher"].pk).course_id is None


def test_demoted_member_with_stale_teacher_role_is_still_a_student(w):
    w["members"]["student"].roles.add(w["r"]["teacher"])
    t = client(w["users"]["teacher"])
    listed = t.get(reverse("organization-students-list", kwargs={"org_pk": w["org"].id}))
    assert str(w["users"]["student"].id) in str(listed.data)
    assert t.patch(student_url(w, w["users"]["student"]), {"is_active": False}, format="json").status_code == 200


def test_teacher_still_manages_real_students(w):
    t = client(w["users"]["teacher"])
    assert t.patch(student_url(w, w["users"]["student"]), {"is_active": False}, format="json").status_code == 200
    assert t.delete(student_url(w, w["users"]["student"])).status_code == 204


def test_superuser_can_enrol_staff_as_learner(w):
    root = User.objects.create_superuser(email="root@t.com", password="x")
    assert batch_add(w, root, "teacher@t.com").status_code == 201
