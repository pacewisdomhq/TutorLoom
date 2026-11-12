"""An org-scoped action must not change the shared User account (name, status,
is_active, is_deleted) of someone it does not exclusively own."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from curriculum.models import Course
from organizations.models import Batch, BatchStudent, Organization, OrganizationMember
from rbac.models import Role, UserRole

pytestmark = pytest.mark.django_db
PW = "Passw0rd!xyz"


def _u(email, **kw):
    return User.objects.create_user(email=email, password=PW, first_name="F", last_name="L", **kw)


@pytest.fixture
def w():
    a = Organization.objects.create(name="A", slug="a", contact_email="a@t.com")
    b = Organization.objects.create(name="B", slug="b", contact_email="b@t.com")
    r = {n: Role.objects.get(name=n) for n in ["org_admin", "teacher", "student"]}
    admin_a = _u("admina@t.com")
    OrganizationMember.objects.create(organization=a, user=admin_a, role=r["org_admin"])
    teacher_a = _u("teachera@t.com")
    OrganizationMember.objects.create(organization=a, user=teacher_a, role=r["teacher"])
    victim_b = _u("victimb@t.com")
    OrganizationMember.objects.create(organization=b, user=victim_b, role=r["teacher"])
    su = User.objects.create_superuser(email="root@t.com", password=PW, first_name="Root", last_name="R")
    batch = Batch.objects.create(organization=a, name="B1", start_date="2026-01-01", end_date="2026-12-31")
    course = Course.objects.create(organization=a, title="C1")
    batch.courses.add(course)
    return dict(a=a, b=b, r=r, admin_a=admin_a, teacher_a=teacher_a, victim_b=victim_b, su=su, batch=batch)


def client(u):
    c = APIClient()
    c.force_authenticate(user=u)
    return c


def login(email):
    return APIClient().post(reverse("login"), {"email": email, "password": PW}, format="json")


def fresh(u):
    return User._base_manager.get(pk=u.pk)


def staff_add(w, email, status):
    url = reverse("organization-staff-list", kwargs={"org_pk": w["a"].id})
    return client(w["admin_a"]).post(url, {"user_email": email, "role_name": "teacher", "first_name": "Pwned",
                                           "last_name": "X", "status": status}, format="json")


def student_add(w, actor, email, **extra):
    url = reverse("organization-students-list", kwargs={"org_pk": w["a"].id})
    return client(actor).post(url, {"email": email, "first_name": "Renamed", **extra}, format="json")


def student_url(w, user):
    return reverse("organization-students-detail", kwargs={"org_pk": w["a"].id, "pk": str(user.id)})


# 1
def test_org_admin_add_staff_with_super_admin_email_leaves_account_alone(w):
    r = staff_add(w, "root@t.com", "expired")
    assert r.status_code == 201
    su = fresh(w["su"])
    assert (su.status, su.is_active, su.is_deleted, su.first_name) == (w["su"].status, True, False, "Root")
    assert login("root@t.com").status_code == 200


# 2
def test_org_admin_add_staff_with_other_org_user_leaves_account_alone(w):
    r = staff_add(w, "victimb@t.com", "expired")
    assert r.status_code == 201
    v = fresh(w["victim_b"])
    assert (v.status, v.is_active, v.first_name) == (w["victim_b"].status, True, "F")
    assert OrganizationMember.objects.filter(organization=w["a"], user=v).exists()
    assert login("victimb@t.com").status_code == 200


# 3
def test_teacher_cannot_delete_account_via_batch_student_patch(w):
    t = client(w["teacher_a"])
    BatchStudent.objects.create(batch=w["batch"], student=OrganizationMember.objects.get(organization=w["a"], user=w["admin_a"]))
    url = reverse("organization-batch-students-detail",
                  kwargs={"org_pk": w["a"].id, "batch_pk": w["batch"].id, "pk": str(w["admin_a"].id)})
    t.patch(url, {"status": "deleted"}, format="json")
    u = fresh(w["admin_a"])
    assert (u.is_deleted, u.is_active, u.status) == (False, True, w["admin_a"].status)
    assert login("admina@t.com").status_code == 200


# 4
def test_teacher_cannot_deactivate_super_admin_via_student_toggle(w):
    assert student_add(w, w["teacher_a"], "root@t.com").status_code == 201
    r = client(w["teacher_a"]).patch(student_url(w, w["su"]), {"is_active": False}, format="json")
    assert r.status_code == 200
    assert fresh(w["su"]).is_active is True
    assert login("root@t.com").status_code == 200
    assert OrganizationMember.objects.get(organization=w["a"], user=w["su"]).is_active is False


# 5
def test_teacher_student_add_does_not_rename_existing_user(w):
    assert student_add(w, w["teacher_a"], "victimb@t.com", last_name="Zed", phone_number="9999999999").status_code == 201
    v = fresh(w["victim_b"])
    assert (v.first_name, v.last_name) == ("F", "L")
    assert not v.phone_number


# 6
def test_staff_bulk_csv_keeps_other_org_pending_user(w):
    p = _u("pendingb@t.com", is_active=False, status=User.STATUS_PENDING)
    OrganizationMember.objects.create(organization=w["b"], user=p, role=w["r"]["teacher"])
    from accounts.models import InviteToken
    InviteToken.objects.create(user=p, token="tok", expires_at="2099-01-01T00:00:00Z", attempt_number=1, organization=w["b"])
    csv = b"email,first_name,last_name,status\npendingb@t.com,Pwned,X,expired\n"
    url = reverse("organization-staff-bulk-upload", kwargs={"org_pk": w["a"].id})
    r = client(w["admin_a"]).post(url, {"file": SimpleUploadedFile("s.csv", csv, content_type="text/csv"),
                                        "role_name": "teacher"}, format="multipart")
    assert r.status_code == 201, r.data
    u = fresh(p)
    assert (u.status, u.first_name) == (User.STATUS_PENDING, "F")
    assert InviteToken.objects.filter(user=p, is_revoked=False, token="tok").exists()


# 7
def test_org_admin_still_manages_single_org_accounts(w):
    s = _u("solo@t.com")
    OrganizationMember.objects.create(organization=w["a"], user=s, role=w["r"]["teacher"])
    admin = client(w["admin_a"])
    # rename a staff member who belongs only to A
    m = OrganizationMember.objects.get(organization=w["a"], user=s)
    url = reverse("organization-staff-detail", kwargs={"org_pk": w["a"].id, "pk": m.id})
    assert admin.patch(url, {"first_name": "Renamed"}, format="json").status_code == 200
    assert fresh(s).first_name == "Renamed"
    # staff toggle is membership-only
    assert admin.patch(url, {"is_active": False}, format="json").status_code == 200
    assert fresh(s).is_active is True
    assert OrganizationMember.objects.get(pk=m.pk).is_active is False
    # student deactivation through the org student endpoint kills the account
    st = _u("pupil@t.com")
    OrganizationMember.objects.create(organization=w["a"], user=st, role=w["r"]["student"])
    assert admin.patch(student_url(w, st), {"is_active": False}, format="json").status_code == 200
    assert fresh(st).is_active is False
    assert login("pupil@t.com").status_code in (400, 401, 403)


# 8
def test_teacher_deactivates_single_org_student_membership_only(w):
    st = _u("pupil@t.com")
    OrganizationMember.objects.create(organization=w["a"], user=st, role=w["r"]["student"])
    bs_member = OrganizationMember.objects.get(organization=w["a"], user=st)
    BatchStudent.objects.create(batch=w["batch"], student=bs_member)
    token = str(RefreshToken.for_user(st).access_token)
    batch_url = reverse("organization-batches-detail", kwargs={"org_pk": w["a"].id, "pk": w["batch"].id})
    live = APIClient()
    live.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    assert live.get(batch_url).status_code == 200

    r = client(w["teacher_a"]).patch(student_url(w, st), {"is_active": False}, format="json")
    assert r.status_code == 200
    assert fresh(st).is_active is True
    assert OrganizationMember.objects.get(pk=bs_member.pk).is_active is False
    lst = client(w["admin_a"]).get(reverse("organization-students-list", kwargs={"org_pk": w["a"].id}))
    rows = lst.data["results"] if isinstance(lst.data, dict) else lst.data
    assert [x["status"] for x in rows if x["email"] == "pupil@t.com"] == ["inactive"]
    lr = login("pupil@t.com")
    assert lr.status_code == 403 and "inactive" in lr.data["detail"]
    assert live.get(batch_url).status_code == 403


# 9
def test_helper_refuses_privileged_and_shared_targets(w):
    from organizations.accounts import can_edit_shared_account

    a = w["a"]
    plain = _u("plain@t.com")
    OrganizationMember.objects.create(organization=a, user=plain, role=w["r"]["student"])
    assert can_edit_shared_account(plain, a, actor=w["admin_a"])
    assert not can_edit_shared_account(plain, a, actor=w["teacher_a"])
    assert can_edit_shared_account(plain, a, actor=w["su"])
    assert not can_edit_shared_account(plain, a)

    staffer = _u("staffer@t.com", is_staff=True)
    assert not can_edit_shared_account(staffer, a, actor=w["admin_a"])
    adm = _u("globaladmin@t.com")
    UserRole.objects.create(user=adm, role=Role.objects.get_or_create(name="admin")[0])
    assert not can_edit_shared_account(adm, a, actor=w["admin_a"])
    assert not can_edit_shared_account(w["su"], a, actor=w["admin_a"])
    assert not can_edit_shared_account(w["victim_b"], a, actor=w["admin_a"])  # member of B


def _reinvite(actor, email):
    return client(actor).post(reverse("reinvite", kwargs={"identifier": email}))


# reinvite endpoint
def test_org_admin_cannot_reinvite_super_admin_after_adding_as_staff(w):
    assert staff_add(w, "root@t.com", "active").status_code == 201
    assert _reinvite(w["admin_a"], "root@t.com").status_code == 403
    assert fresh(w["su"]).is_active is True
    assert login("root@t.com").status_code == 200


def test_org_admin_cannot_reinvite_other_org_user(w):
    assert staff_add(w, "victimb@t.com", "active").status_code == 201
    assert _reinvite(w["admin_a"], "victimb@t.com").status_code == 403
    assert fresh(w["victim_b"]).is_active is True


def test_org_admin_can_reinvite_own_pending_user(w):
    p = _u("pend@t.com", is_active=False, status=User.STATUS_PENDING)
    OrganizationMember.objects.create(organization=w["a"], user=p, role=w["r"]["teacher"])
    assert _reinvite(w["admin_a"], "pend@t.com").status_code == 200


# members endpoint
def test_org_admin_members_add_keeps_other_org_pending_invite(w):
    from accounts.models import InviteToken
    p = _u("pendingb@t.com", is_active=False, status=User.STATUS_PENDING)
    OrganizationMember.objects.create(organization=w["b"], user=p, role=w["r"]["teacher"])
    InviteToken.objects.create(user=p, token="tok", expires_at="2099-01-01T00:00:00Z", attempt_number=1, organization=w["b"])
    i = _u("inactive@t.com", is_active=False, status=User.STATUS_INACTIVE)
    url = reverse("organization-members-list", kwargs={"org_pk": w["a"].id})
    for email in ("pendingb@t.com", "inactive@t.com"):
        client(w["admin_a"]).post(url, {"user_email": email, "role_name": "teacher"}, format="json")
    assert InviteToken.objects.filter(user=p, is_revoked=False, token="tok").exists()
    assert fresh(i).status == User.STATUS_INACTIVE
