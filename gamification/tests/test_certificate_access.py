# SPDX-FileCopyrightText: 2026 Pace Wisdom Solutions Pvt. Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Certificates must not be reachable by their numeric id without the owner's login."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from curriculum.models import Course
from gamification.models import Certificate
from organizations.models import Organization, OrganizationMember
from rbac.models import Role

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def cert_setup():
    org = Organization.objects.create(name="Access Org", slug="access-org")
    student_role, _ = Role.objects.get_or_create(name="student")
    owner = User.objects.create_user(email="owner@access.test", first_name="Alice", last_name="Private")
    other = User.objects.create_user(email="other@access.test", first_name="Bob", last_name="Other")
    for user in (owner, other):
        OrganizationMember.objects.create(user=user, organization=org, role=student_role)
    course = Course.objects.create(organization=org, title="Access Course", status="Published")
    cert = Certificate.objects.create(
        certificate_id="CERT-C-1-ACCE55ED", student=owner, course=course, organization=org
    )
    return {"org": org, "owner": owner, "other": other, "cert": cert}


@pytest.mark.parametrize("suffix", ["html", "preview", "download"])
def test_public_routes_refuse_numeric_id(cert_setup, suffix):
    cert = cert_setup["cert"]
    client = APIClient()
    assert client.get(f"/api/certificates/{cert.pk}/{suffix}/").status_code == 404
    assert client.get(f"/api/certificates/{cert.certificate_id}/{suffix}/").status_code == 200


def test_public_verify_hides_email_and_user_id(cert_setup):
    cert = cert_setup["cert"]
    res = APIClient().get(f"/api/certificates/{cert.certificate_id}/")
    assert res.status_code == 200
    student = res.data["student"]
    assert "email" not in student
    assert "id" not in student
    assert student["full_name"] == "Alice Private"


@pytest.mark.parametrize("query", ["?format=json", ""])
def test_org_download_needs_owner_or_staff(cert_setup, query):
    s = cert_setup
    url = f"/api/organizations/{s['org'].pk}/certificates/{s['cert'].pk}/download/{query}"

    assert APIClient().get(url).status_code == 401

    other = APIClient()
    other.force_authenticate(user=s["other"])
    assert other.get(url).status_code == 404

    owner = APIClient()
    owner.force_authenticate(user=s["owner"])
    assert owner.get(url).status_code == 200

    admin = APIClient()
    admin.force_authenticate(user=User.objects.create_superuser(email="root@access.test", password="x"))
    assert admin.get(url).status_code == 200
