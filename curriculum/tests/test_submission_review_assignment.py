# SPDX-FileCopyrightText: 2026 Pace Wisdom Solutions Pvt. Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Reading and grading task submissions needs the course assignment, not just the teacher role."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from curriculum.models import Course, Module, Node, StudentNodeProgress, Task, TaskSubmission
from organizations.models import Organization, OrganizationMember
from rbac.models import Role

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def review_setup():
    org = Organization.objects.create(name="Review Org", slug="review-org")
    roles = {name: Role.objects.get_or_create(name=name)[0] for name in ("org_admin", "teacher", "student")}
    users = {
        name: User.objects.create_user(email=f"{name}@review.test", first_name=name)
        for name in ("admin", "assigned", "unassigned", "student")
    }
    OrganizationMember.objects.create(organization=org, user=users["admin"], role=roles["org_admin"])
    OrganizationMember.objects.create(organization=org, user=users["assigned"], role=roles["teacher"])
    OrganizationMember.objects.create(organization=org, user=users["unassigned"], role=roles["teacher"])
    student = OrganizationMember.objects.create(organization=org, user=users["student"], role=roles["student"])

    course = Course.objects.create(organization=org, title="Course 1", status="Published")
    course.teachers.add(users["assigned"])
    node = Node.objects.create(module=Module.objects.create(course=course, title="M1"), title="Task node")
    task = Task.objects.create(node=node, title="Lab")
    submission = TaskSubmission.objects.create(task=task, student=student, payload={"paragraph": "my answer"})
    return {"org": org, "users": users, "course": course, "node": node, "submission": submission, "student": student}


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _detail_url(s):
    return (
        f"/api/organizations/{s['org'].pk}/node-submission-details/"
        f"?student_id={s['users']['student'].pk}&course_id={s['course'].pk}&node_id={s['node'].pk}"
    )


def _review_url(s):
    return f"/api/organizations/{s['org'].pk}/submissions/tasks/{s['submission'].pk}/review/"


REVIEW = {"decision": "Approved", "awarded_score": 100, "feedback": "ok"}


def test_unassigned_teacher_cannot_read_submissions(review_setup):
    assert _client(review_setup["users"]["unassigned"]).get(_detail_url(review_setup)).status_code == 403


def test_unassigned_teacher_cannot_review(review_setup):
    s = review_setup
    res = _client(s["users"]["unassigned"]).post(_review_url(s), REVIEW, format="json")
    assert res.status_code == 403
    s["submission"].refresh_from_db()
    assert s["submission"].status == "Pending"
    assert s["submission"].awarded_score is None
    assert not StudentNodeProgress.objects.filter(student=s["student"], node=s["node"]).exists()


@pytest.mark.parametrize("who", ["assigned", "admin"])
def test_assigned_teacher_and_admin_can_read_and_review(review_setup, who):
    s = review_setup
    client = _client(s["users"][who])
    assert client.get(_detail_url(s)).status_code == 200
    assert client.post(_review_url(s), REVIEW, format="json").status_code == 200
    s["submission"].refresh_from_db()
    assert s["submission"].status == "Approved"


def test_assigned_teacher_cannot_review_in_archived_course(review_setup):
    s = review_setup
    s["course"].status = "Archived"
    s["course"].save()
    assert _client(s["users"]["assigned"]).post(_review_url(s), REVIEW, format="json").status_code == 403
    assert _client(s["users"]["admin"]).post(_review_url(s), REVIEW, format="json").status_code == 200
