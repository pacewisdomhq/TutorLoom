# SPDX-FileCopyrightText: 2026 Pace Wisdom Solutions Pvt. Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Course submits save against the learner's membership and never create or change one."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from curriculum.models import (
    Assessment, AssignmentSubmission, Course, Module, Node, Quiz, QuizOption,
    QuizQuestion, QuizSubmission, Task, TaskSubmission,
)
from organizations.models import Batch, BatchStudent, Organization, OrganizationMember
from rbac.models import Role

ONLY_LEARNERS = 'Only learners of this organisation can submit.'
COURSE_ACCESS_DENIED = 'Course access is not active for this student.'


@pytest.fixture
def setup(db):
    # Created first so Organization.objects.first() is not the course organisation.
    other_org = Organization.objects.create(name="Other Org", slug="other-org")
    org = Organization.objects.create(name="Course Org", slug="course-org")
    teacher_role, _ = Role.objects.get_or_create(name="teacher")

    course = Course.objects.create(organization=org, title="Course", status="Published")
    module = Module.objects.create(course=course, title="Module")
    node = Node.objects.create(module=module, title="Node")
    Assessment.objects.create(node=node, assignment_type='MCQ', prompt='Q', max_attempts=5)
    Task.objects.create(node=node, title="Task", allow_paragraph=True)
    quiz = Quiz.objects.create(node=node, name="Quiz")
    question = QuizQuestion.objects.create(quiz=quiz, question_text="Q1")
    right = QuizOption.objects.create(question=question, option_text="Right", is_correct=True)

    teacher = User.objects.create_user(email="teacher@sub.com", password="password123")
    teacher_member = OrganizationMember.objects.create(user=teacher, organization=org, role=teacher_role)

    student = User.objects.create_user(email="student@sub.com", password="password123")
    today = timezone.localdate()
    batch = Batch.objects.create(
        organization=org, name="Batch",
        start_date=today - timedelta(days=1), end_date=today + timedelta(days=30),
    )
    batch.courses.add(course)
    BatchStudent.objects.create(batch=batch, student=student, course=course)
    student_member = OrganizationMember.objects.get(user=student, organization=org)

    return {
        "org": org, "other_org": other_org, "node": node, "quiz": quiz,
        "quiz_answer": {"answers": [{"question": question.id, "selected_option": right.id}]},
        "teacher": teacher, "teacher_member": teacher_member,
        "student": student, "student_member": student_member,
    }


def _post(user, url, data):
    client = APIClient()
    client.force_authenticate(user=user)
    return client.post(url, data, format="json")


def _assignment(user, s):
    return _post(user, reverse("assignment-submission", kwargs={"node_id": s["node"].id}), {"payload": {}})


def _task(user, s):
    return _post(user, reverse("task-submission", kwargs={"node_id": s["node"].id}), {"payload": {"answer": "x"}})


def _quiz(user, s):
    return _post(user, reverse("quiz-submission", kwargs={"quiz_id": s["quiz"].id}), s["quiz_answer"])


def _role_names(member):
    member.refresh_from_db()
    return set(member.roles.values_list("name", flat=True))


def test_outsider_cannot_join_by_submitting_assignment(setup):
    outsider = User.objects.create_user(email="outsider@sub.com", password="password123")

    resp = _assignment(outsider, setup)

    assert resp.status_code == 403
    assert resp.data["detail"] == COURSE_ACCESS_DENIED
    assert not AssignmentSubmission.objects.exists()
    assert not OrganizationMember.objects.filter(user=outsider).exists()


def test_member_not_enrolled_in_course_cannot_submit_assignment(setup):
    learner = User.objects.create_user(email="learner@sub.com", password="password123")
    student_role, _ = Role.objects.get_or_create(name="student")
    OrganizationMember.objects.create(user=learner, organization=setup["org"], role=student_role)

    resp = _assignment(learner, setup)

    assert resp.status_code == 403
    assert resp.data["detail"] == COURSE_ACCESS_DENIED
    assert not AssignmentSubmission.objects.exists()


@pytest.mark.parametrize("submit", [_assignment, _task, _quiz])
def test_teacher_submit_is_refused_and_gains_no_student_role(setup, submit):
    resp = submit(setup["teacher"], setup)

    assert resp.status_code == 403
    assert resp.data["detail"] == ONLY_LEARNERS
    assert not AssignmentSubmission.objects.exists()
    assert not TaskSubmission.objects.exists()
    assert not QuizSubmission.objects.exists()
    assert "student" not in _role_names(setup["teacher_member"])


def test_superuser_without_membership_is_refused(setup):
    admin = User.objects.create_superuser(email="root@sub.com", password="password123")

    resp = _task(admin, setup)

    assert resp.status_code == 403
    assert resp.data["detail"] == ONLY_LEARNERS
    assert not OrganizationMember.objects.filter(user=admin).exists()


def test_inactive_member_cannot_submit_assignment(setup):
    member = setup["student_member"]
    member.is_active = False
    member.save()

    resp = _assignment(setup["student"], setup)

    assert resp.status_code == 403
    assert resp.data["detail"] == ONLY_LEARNERS
    assert not AssignmentSubmission.objects.exists()


@pytest.mark.parametrize("submit", [_task, _quiz])
def test_enrolled_member_with_other_role_submits_without_gaining_student_role(setup, submit):
    manager_role, _ = Role.objects.get_or_create(name="manager")
    member = setup["student_member"]
    member.role = manager_role
    member.save()
    member.roles.set([manager_role])

    resp = submit(setup["student"], setup)

    assert resp.status_code == 201
    assert "student" not in _role_names(member)


def test_student_submissions_are_saved_against_course_membership(setup):
    s = setup
    assert Organization.objects.first() == s["other_org"]

    assert _assignment(s["student"], s).status_code == 202
    assert _task(s["student"], s).status_code == 201
    assert _quiz(s["student"], s).status_code == 201

    for model in (AssignmentSubmission, TaskSubmission, QuizSubmission):
        assert model.objects.get().student == s["student_member"]
    assert OrganizationMember.objects.filter(user=s["student"]).count() == 1
