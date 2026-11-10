# SPDX-FileCopyrightText: 2026 Pace Wisdom Solutions Pvt. Ltd.
# SPDX-License-Identifier: Apache-2.0

import pytest
from django.urls import NoReverseMatch, reverse
from rest_framework.test import APIClient

from accounts.models import User
from curriculum.models import Course, Module, Node, Task, TaskSubmission
from organizations.models import Organization, OrganizationMember
from rbac.models import Role


@pytest.mark.django_db
def test_grade_route_is_gone_and_changes_nothing():
    org = Organization.objects.create(name="Org", slug="org")
    course = Course.objects.create(organization=org, title="Course")
    node = Node.objects.create(module=Module.objects.create(course=course, title="Module"), title="Node")
    task = Task.objects.create(node=node, title="Task", allow_paragraph=True)
    student = User.objects.create_user(email="student@test.com", password="password123")
    student_role, _ = Role.objects.get_or_create(name="student")
    member = OrganizationMember.objects.create(user=student, organization=org, role=student_role)
    submission = TaskSubmission.objects.create(task=task, student=member, payload={"answer": "x"})
    client = APIClient()
    client.force_authenticate(user=student)

    url = f"/api/submissions/{submission.id}/grade/"
    assert client.get(url).status_code == 404
    assert client.patch(url, {"awarded_score": 100, "feedback": "x"}, format="json").status_code == 404

    submission.refresh_from_db()
    assert submission.status == "Pending"
    assert submission.awarded_score is None
    with pytest.raises(NoReverseMatch):
        reverse("grade-submission", args=[submission.id])
