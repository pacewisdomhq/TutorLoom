# SPDX-FileCopyrightText: 2026 Pace Wisdom Solutions Pvt. Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Batches and courses picked on student, staff and batch forms must belong to
the organisation in the URL."""

import datetime

import pytest
from rest_framework.test import APIClient

from accounts.models import User
from curriculum.models import Course
from organizations.models import Batch, BatchStudent, Organization, OrganizationMember
from rbac.models import Role, UserRole

pytestmark = pytest.mark.django_db
PW = "Passw0rd!xyz"
D1, D2 = datetime.date(2026, 1, 1), datetime.date(2026, 12, 31)


def _u(email):
    return User.objects.create_user(email=email, password=PW, first_name="F", last_name="L")


@pytest.fixture
def w():
    a = Organization.objects.create(name="A", slug="a", contact_email="a@t.com")
    b = Organization.objects.create(name="B", slug="b", contact_email="b@t.com")
    r = {n: Role.objects.get(name=n) for n in ["org_admin", "teacher", "student"]}
    batch_a = Batch.objects.create(organization=a, name="A1", start_date=D1, end_date=D2)
    batch_b = Batch.objects.create(organization=b, name="B1", start_date=D1, end_date=D2)
    course_a = Course.objects.create(organization=a, title="Course A")
    course_b = Course.objects.create(organization=b, title="Course B")
    batch_a.courses.add(course_a)
    teacher_b = _u("teacher-b@t.com")
    OrganizationMember.objects.create(organization=b, user=teacher_b, role=r["teacher"])
    UserRole.objects.get_or_create(user=teacher_b, role=r["teacher"])
    admin_b = _u("admin-b@t.com")
    OrganizationMember.objects.create(organization=b, user=admin_b, role=r["org_admin"])
    UserRole.objects.get_or_create(user=admin_b, role=r["org_admin"])
    student_b = _u("student-b@t.com")
    student_m = OrganizationMember.objects.create(organization=b, user=student_b, role=r["student"])
    staff_b = _u("staff-b@t.com")
    staff_m = OrganizationMember.objects.create(organization=b, user=staff_b, role=r["teacher"])
    return dict(a=a, b=b, batch_a=batch_a, batch_b=batch_b, course_a=course_a, course_b=course_b,
                teacher_b=teacher_b, admin_b=admin_b, student_b=student_b, student_m=student_m,
                staff_m=staff_m)


def client(u):
    c = APIClient()
    c.force_authenticate(user=u)
    return c


def test_student_cannot_be_put_in_another_orgs_batch(w):
    c = client(w["teacher_b"])
    url = f"/api/organizations/{w['b'].pk}/students/{w['student_b'].pk}/"
    r = c.patch(url, {"batch_ids": [w["batch_a"].pk]}, format="json")
    assert r.status_code == 400 and "batch_ids" in r.data, r.data
    assert not BatchStudent.objects.filter(batch=w["batch_a"]).exists()
    r = c.patch(url, {"batch_ids": [w["batch_b"].pk]}, format="json")
    assert r.status_code == 200
    assert BatchStudent.objects.filter(batch=w["batch_b"], student=w["student_m"]).exists()


def test_staff_cannot_be_put_in_another_orgs_batch(w):
    c = client(w["admin_b"])
    base = f"/api/organizations/{w['b'].pk}/staff/"
    r = c.post(base, {"user_email": "new-staff@t.com", "first_name": "N", "last_name": "S",
                      "role_name": "teacher", "batches": [w["batch_a"].pk]}, format="json")
    assert r.status_code == 400 and "batches" in r.data, r.data
    r = c.patch(f"{base}{w['staff_m'].pk}/", {"batches": [w["batch_a"].pk]}, format="json")
    assert r.status_code == 400 and "batches" in r.data, r.data
    assert not w["batch_a"].staff_members.exists()
    assert not w["course_a"].teachers.exists()
    # On 1.0.5 the course sync also created an active teacher membership in org A.
    assert not OrganizationMember.objects.filter(organization=w["a"]).exists()


def test_batch_cannot_link_another_orgs_course(w):
    c = client(w["teacher_b"])
    base = f"/api/organizations/{w['b'].pk}/batches/"
    r = c.post(base, {"name": "B2", "start_date": "2026-01-01", "end_date": "2026-12-31",
                      "courses": [w["course_a"].pk]}, format="json")
    assert r.status_code == 400 and "courses" in r.data, r.data
    r = c.patch(f"{base}{w['batch_b'].pk}/", {"courses": [w["course_a"].pk]}, format="json")
    assert r.status_code == 400 and "courses" in r.data, r.data
    assert list(w["course_a"].batches.all()) == [w["batch_a"]]
    r = c.patch(f"{base}{w['batch_b'].pk}/", {"courses": [w["course_b"].pk]}, format="json")
    assert r.status_code == 200, r.data
