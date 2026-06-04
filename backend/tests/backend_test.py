"""Comprehensive backend API tests for Atlas Academy LMS."""
import os
import uuid
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback to reading frontend .env file
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                    break
    except Exception:
        pass

assert BASE_URL, "REACT_APP_BACKEND_URL not set"
API = f"{BASE_URL}/api"

def _cid(c):
    """Get id from a course/lesson/etc dict that may use 'id' or '_id'."""
    return c.get("id") or c.get("_id")


ADMIN_EMAIL = "admin@atlasacademy.io"
ADMIN_PASSWORD = "admin123"
STUDENT_EMAIL = "student@atlasacademy.io"
STUDENT_PASSWORD = "student123"


# ---------- Shared fixtures ----------
@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _login(session, email, password):
    r = session.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def admin_token(session):
    return _login(session, ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def new_student(session):
    """Register a brand new student each test session."""
    email = f"TEST_student_{uuid.uuid4().hex[:8]}@example.com"
    payload = {"email": email, "password": "pass1234", "name": "TEST Student"}
    r = session.post(f"{API}/auth/register", json=payload, timeout=15)
    assert r.status_code in (200, 201), r.text
    data = r.json()
    return {"email": email, "token": data["access_token"], "user": data["user"]}


@pytest.fixture(scope="session")
def student_headers(new_student):
    return {"Authorization": f"Bearer {new_student['token']}", "Content-Type": "application/json"}


# ---------- Health ----------
def test_health(session):
    r = session.get(f"{API}/health", timeout=10)
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


# ---------- Auth ----------
class TestAuth:
    def test_register_creates_student(self, session):
        email = f"TEST_reg_{uuid.uuid4().hex[:8]}@example.com"
        r = session.post(f"{API}/auth/register", json={"email": email, "password": "pw12345", "name": "Reg User"})
        assert r.status_code in (200, 201), r.text
        data = r.json()
        assert "access_token" in data
        assert data["user"]["email"].lower() == email.lower()
        assert data["user"]["role"] == "student"

    def test_admin_login(self, session):
        r = session.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert r.status_code == 200
        data = r.json()
        assert data["user"]["role"] == "admin"
        assert data["access_token"]

    def test_bad_password_401(self, session):
        r = session.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrongpw"})
        assert r.status_code == 401

    def test_me_current_user(self, session, admin_headers):
        r = session.get(f"{API}/auth/me", headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["email"] == ADMIN_EMAIL


# ---------- Courses ----------
class TestCourses:
    def test_list_courses_public(self, session):
        r = session.get(f"{API}/courses")
        assert r.status_code == 200
        courses = r.json()
        assert isinstance(courses, list)
        assert len(courses) >= 4, f"expected >=4 seeded courses, got {len(courses)}"
        for c in courses:
            assert c.get("is_published") is True

    def test_categories(self, session):
        r = session.get(f"{API}/courses/categories")
        assert r.status_code == 200
        cats = r.json()
        assert isinstance(cats, list)
        # sorted
        assert cats == sorted(cats, key=lambda x: str(x).lower()) or cats == sorted(cats)

    def test_course_by_slug(self, session):
        r = session.get(f"{API}/courses/slug/learning-core-3")
        # may be 404 since seeded slugs differ; try free course slug too
        if r.status_code == 404:
            r2 = session.get(f"{API}/courses/slug/foundations-of-modern-design")
            assert r2.status_code == 200, "neither slug exists"
        else:
            assert r.status_code == 200

    def test_admin_create_update_delete_course(self, session, admin_headers):
        payload = {
            "title": "TEST Course Z",
            "slug": f"test-course-{uuid.uuid4().hex[:6]}",
            "description": "test",
            "short_description": "short",
            "price": 0,
            "category": "Test",
            "level": "beginner",
            "is_published": True,
            "is_free": True,
        }
        r = session.post(f"{API}/courses", json=payload, headers=admin_headers)
        assert r.status_code in (200, 201), r.text
        course = r.json()
        cid = _cid(course)
        assert cid

        # non-admin 403
        r2 = session.post(f"{API}/courses", json=payload, headers={"Content-Type": "application/json"})
        assert r2.status_code in (401, 403)

        # patch
        r3 = session.patch(f"{API}/courses/{cid}", json={"title": "TEST Course Z2"}, headers=admin_headers)
        assert r3.status_code == 200
        assert r3.json()["title"] == "TEST Course Z2"

        # delete
        r4 = session.delete(f"{API}/courses/{cid}", headers=admin_headers)
        assert r4.status_code in (200, 204)


# ---------- Lessons ----------
class TestLessons:
    def _free_course(self, session):
        r = session.get(f"{API}/courses")
        for c in r.json():
            if c.get("is_free") or c.get("price", 0) == 0:
                return c
        return r.json()[0]

    def test_lessons_locked_for_non_enrolled(self, session, new_student):
        course = self._free_course(session)
        # use a paid course preferably (where lessons are locked)
        all_courses = session.get(f"{API}/courses").json()
        paid = next((c for c in all_courses if not c.get("is_free") and c.get("price", 0) > 0), None)
        target = paid or course
        headers = {"Authorization": f"Bearer {new_student['token']}"}
        r = session.get(f"{API}/lessons/by-course/{_cid(target)}", headers=headers)
        assert r.status_code == 200
        lessons = r.json()
        assert isinstance(lessons, list)
        if paid:
            non_preview = [l for l in lessons if not l.get("is_preview")]
            if non_preview:
                assert any(
                    not l.get("content_text") and not l.get("video_url") for l in non_preview
                ), "Locked lesson content should be stripped"

    def test_admin_lesson_crud(self, session, admin_headers):
        courses = session.get(f"{API}/courses").json()
        cid = _cid(courses[0])
        payload = {
            "course_id": cid,
            "title": "TEST Lesson",
            "lesson_type": "text",
            "content_text": "hello",
            "order_index": 999,
        }
        r = session.post(f"{API}/lessons", json=payload, headers=admin_headers)
        assert r.status_code in (200, 201), r.text
        lid = _cid(r.json())
        r2 = session.patch(f"{API}/lessons/{lid}", json={"title": "TEST Lesson 2"}, headers=admin_headers)
        assert r2.status_code == 200
        r3 = session.delete(f"{API}/lessons/{lid}", headers=admin_headers)
        assert r3.status_code in (200, 204)


# ---------- Enrollments / Progress / Certificate ----------
class TestEnrollments:
    @pytest.fixture(scope="class")
    def free_course(self, session):
        r = session.get(f"{API}/courses")
        for c in r.json():
            if c.get("slug") == "foundations-of-modern-design":
                return c
        # fallback to first free
        for c in r.json():
            if c.get("is_free") or c.get("price", 0) == 0:
                return c
        pytest.skip("no free course")

    @pytest.fixture(scope="class")
    def paid_course(self, session):
        r = session.get(f"{API}/courses")
        for c in r.json():
            if not c.get("is_free") and c.get("price", 0) > 0:
                return c
        return None

    def test_enroll_free(self, session, student_headers, free_course):
        r = session.post(
            f"{API}/enrollments/free",
            json={"course_id": _cid(free_course)},
            headers=student_headers,
        )
        assert r.status_code in (200, 201), r.text

    def test_enroll_paid_via_free_400(self, session, student_headers, paid_course):
        if not paid_course:
            pytest.skip("no paid course")
        r = session.post(
            f"{API}/enrollments/free",
            json={"course_id": _cid(paid_course)},
            headers=student_headers,
        )
        assert r.status_code == 400

    def test_my_enrollments_list(self, session, student_headers, free_course):
        r = session.get(f"{API}/enrollments/me", headers=student_headers)
        assert r.status_code == 200
        data = r.json()
        assert any((e.get("course_id") == _cid(free_course)) for e in data)

    def test_check_enrollment(self, session, student_headers, free_course):
        r = session.get(f"{API}/enrollments/check/{_cid(free_course)}", headers=student_headers)
        assert r.status_code == 200
        assert r.json().get("enrolled") is True

    def test_progress_and_certificate(self, session, student_headers, free_course):
        cid = _cid(free_course)
        rL = session.get(f"{API}/lessons/by-course/{cid}", headers=student_headers)
        assert rL.status_code == 200
        lessons = rL.json()
        assert len(lessons) >= 1
        last_progress = -1
        for lesson in lessons:
            r = session.post(
                f"{API}/enrollments/progress",
                json={"course_id": cid, "lesson_id": _cid(lesson)},
                headers=student_headers,
            )
            assert r.status_code in (200, 201), r.text
            data = r.json()
            prog = data.get("progress_percentage") or data.get("progress") or 0
            assert prog >= last_progress
            last_progress = prog

        # check enrollment completed
        rE = session.get(f"{API}/enrollments/me", headers=student_headers)
        target = next((e for e in rE.json() if e["course_id"] == cid), None)
        assert target and target.get("is_completed") is True, f"not completed: {target}"

        # certificate PDF
        rC = session.get(
            f"{API}/enrollments/certificate/{cid}",
            headers=student_headers,
        )
        assert rC.status_code == 200
        assert "application/pdf" in rC.headers.get("content-type", "").lower()


# ---------- Payments ----------
class TestPayments:
    def test_payments_config(self, session):
        r = session.get(f"{API}/payments/config")
        assert r.status_code == 200
        data = r.json()
        assert data.get("provider") == "paystack"
        assert data.get("configured") is False

    def test_payments_initialize_503(self, session, student_headers):
        # find a paid course
        courses = session.get(f"{API}/courses").json()
        paid = next((c for c in courses if not c.get("is_free") and c.get("price", 0) > 0), None)
        if not paid:
            pytest.skip("no paid course")
        r = session.post(
            f"{API}/payments/initialize",
            json={"course_id": _cid(paid), "callback_url": "https://example.com/cb"},
            headers=student_headers,
        )
        assert r.status_code == 503, f"expected 503 got {r.status_code} {r.text}"


# ---------- Testimonials ----------
class TestTestimonials:
    def test_list_approved(self, session):
        r = session.get(f"{API}/testimonials")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        for t in data:
            assert t.get("is_approved") is True

    def test_create_and_admin_approve(self, session, student_headers, admin_headers):
        payload = {"name": "TEST Reviewer", "quote": "TEST Great course!", "rating": 5}
        r = session.post(f"{API}/testimonials", json=payload, headers=student_headers)
        assert r.status_code in (200, 201), r.text
        t = r.json()
        assert t.get("is_approved") is False
        tid = _cid(t)
        r2 = session.patch(
            f"{API}/testimonials/{tid}",
            json={"is_approved": True, "is_featured": True},
            headers=admin_headers,
        )
        assert r2.status_code == 200
        assert r2.json().get("is_approved") is True


# ---------- Contacts ----------
class TestContacts:
    def test_create_contact_no_auth(self, session):
        r = session.post(
            f"{API}/contacts",
            json={"name": "TEST Contact", "email": "test@example.com", "message": "Hello", "subject": "Q"},
        )
        assert r.status_code in (200, 201), r.text
        assert _cid(r.json()) is not None

    def test_admin_contact_flow(self, session, admin_headers):
        # create
        r = session.post(
            f"{API}/contacts",
            json={"name": "TEST C2", "email": "t2@example.com", "message": "Hi", "subject": "S"},
        )
        cid = _cid(r.json())
        # list
        r2 = session.get(f"{API}/contacts", headers=admin_headers)
        assert r2.status_code == 200
        # mark read
        r3 = session.patch(f"{API}/contacts/{cid}/read", headers=admin_headers)
        assert r3.status_code == 200
        # delete
        r4 = session.delete(f"{API}/contacts/{cid}", headers=admin_headers)
        assert r4.status_code in (200, 204)


# ---------- Admin ----------
class TestAdmin:
    def test_stats(self, session, admin_headers):
        r = session.get(f"{API}/admin/stats", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        for k in ("users", "students", "courses", "enrollments"):
            assert k in data

    def test_users_list(self, session, admin_headers):
        r = session.get(f"{API}/admin/users", headers=admin_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_payments_list(self, session, admin_headers):
        r = session.get(f"{API}/admin/payments", headers=admin_headers)
        assert r.status_code == 200

    def test_non_admin_403(self, session, student_headers):
        r = session.get(f"{API}/admin/stats", headers=student_headers)
        assert r.status_code == 403
