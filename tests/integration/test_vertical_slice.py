import io
import zipfile

from fastapi.testclient import TestClient

from app import db, retrieval, services
from app.main import app


def test_full_local_vertical_slice(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(db, "DATABASE_PATH", tmp_path / "curriculumos.db")
    monkeypatch.setattr(services, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(services, "EXPORT_DIR", tmp_path / "exports")
    monkeypatch.setattr(retrieval, "INDEX_DIR", tmp_path / "retrieval")
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "ok"
        assert "CurriculumOS" in client.get("/").text
        assert client.get("/api/v1/courses").status_code == 401
        assert client.post("/api/v1/auth/sign-in", json={"email": "nobody@example.edu", "password": "short"}).status_code == 401
        auth_result = client.post("/api/v1/auth/sign-up", json={"email": "teacher@example.edu", "password": "correct-horse-battery-staple", "display_name": "Ayesha Teacher"})
        assert auth_result.status_code == 201
        client.headers.update({"Authorization": f"Bearer {auth_result.json()['access_token']}"})
        course = client.post("/api/v1/courses", json={"name": "Grade XI Mechanics", "grade": "XI", "subject": "Physics", "section": "A"}).json()
        course_id = course["id"]
        upload = client.post(
            f"/api/v1/courses/{course_id}/documents",
            data={"document_type": "textbook", "title": "Mechanics source"},
            files={"file": ("mechanics.txt", b"Force is a push or pull that can change motion.\n\nMomentum describes mass in motion and depends on velocity.\n\nEnergy is conserved when no work is done by an external force.", "text/plain")},
        )
        assert upload.status_code == 201
        assert client.get(f"/api/v1/jobs/{upload.json()['job_id']}").json()["status"] == "completed"
        block = client.get(f"/api/v1/courses/{course_id}/source-blocks").json()[0]
        source = client.get(f"/api/v1/courses/{course_id}/documents/{block['document_id']}/source")
        assert source.status_code == 200
        assert b"Force is a push" in source.content
        corrected = client.put(f"/api/v1/courses/{course_id}/source-blocks/{block['id']}", json={"text": "Force is a push or pull that changes motion."})
        assert corrected.status_code == 200
        assert "teacher_corrected" in corrected.json()["quality_flags"]
        indexed = client.post(f"/api/v1/courses/{course_id}/retrieval/rebuild")
        assert indexed.status_code == 200
        retrieved = client.get(f"/api/v1/courses/{course_id}/retrieval/search", params={"q": "mass and velocity"}).json()
        assert retrieved["results"][0]["page_number"] == 1
        assert "Momentum" in retrieved["results"][0]["text"]
        graph = client.post(f"/api/v1/courses/{course_id}/concept-graph/generate").json()
        assert len(graph["concepts"]) == 3
        for edge in graph["edges"]:
            assert client.post(f"/api/v1/courses/{course_id}/concept-edges/{edge['id']}/approve").status_code == 200
        schedule = client.post(f"/api/v1/courses/{course_id}/schedules/compile", json={"start_date": "2026-08-03", "end_date": "2026-08-31", "exam_date": "2026-09-01", "session_days": ["MONDAY", "WEDNESDAY", "FRIDAY"], "session_minutes": 45, "holidays": [], "revision_sessions": 2}).json()
        lessons = [entry for entry in schedule["entries"] if entry["kind"] == "lesson"]
        assert len(lessons) == 3
        locked = client.post(f"/api/v1/courses/{course_id}/schedule-entries/{lessons[0]['id']}/lock").json()
        assert locked["locked"] is True
        lesson = client.post(f"/api/v1/courses/{course_id}/schedule-entries/{lessons[0]['id']}/lesson/generate", json={}).json()
        assert lesson["content"]["source_block_ids"]
        edited_content = {**lesson["content"], "objectives": ["Teacher-approved objective."]}
        edited = client.put(f"/api/v1/courses/{course_id}/lessons/{lesson['id']}", params={"locked": "true"}, json=edited_content)
        assert edited.status_code == 200
        preserved = client.post(f"/api/v1/courses/{course_id}/schedule-entries/{lessons[0]['id']}/lesson/generate", json={}).json()
        assert preserved["preserved_teacher_work"] is True
        assert preserved["content"]["objectives"] == ["Teacher-approved objective."]
        concept_ids = [concept["id"] for concept in graph["concepts"][:2]]
        assessment = client.post(f"/api/v1/courses/{course_id}/assessments/generate", json={"concept_ids": concept_ids, "title": "Mechanics check"}).json()
        assert client.post(f"/api/v1/courses/{course_id}/assessments/{assessment['id']}/approve").json()["approved"] is True
        csv_text = "student_id,assessment_item_id,concept_id,earned_points,max_points\nS1,Q1," + concept_ids[0] + ",4,4\nS1,Q2," + concept_ids[1] + ",0,4\nS2,Q1," + concept_ids[0] + ",4,4\nS2,Q2," + concept_ids[1] + ",1,4\n"
        imported = client.post(f"/api/v1/courses/{course_id}/assessments/{assessment['id']}/results/import", files={"file": ("results.csv", csv_text, "text/csv")}).json()
        assert imported["imported_attempts"] == 4
        mastery = client.post(f"/api/v1/courses/{course_id}/mastery/recompute").json()
        assert mastery[0]["concept_id"] == concept_ids[1]
        remediation = client.post(f"/api/v1/courses/{course_id}/remediation/propose").json()
        assert remediation["concept_id"] == concept_ids[1]
        cancelled = [entry["id"] for entry in lessons[1:]]
        replanned = client.post(f"/api/v1/courses/{course_id}/remediation/{remediation['id']}/approve", json={"base_version_id": schedule["version"]["id"], "cancelled_session_ids": cancelled}).json()
        assert replanned["schedule"]["version"]["parent_version_id"] == schedule["version"]["id"]
        locked_after = next(entry for entry in replanned["schedule"]["entries"] if entry["concept_id"] == lessons[0]["concept_id"])
        assert locked_after["session_date"] == lessons[0]["session_date"]
        assert locked_after["locked"] is True
        assert any(entry["kind"] == "revision" for entry in replanned["schedule"]["entries"])
        assert any(entry["kind"] == "remediation" for entry in replanned["schedule"]["entries"])
        assert any(change["reason"] == "approved remediation" for change in replanned["schedule"]["diff"])
        published = client.post(f"/api/v1/courses/{course_id}/schedules/{replanned['schedule']['version']['id']}/publish").json()
        assert published["published_at"]
        exported = client.post(f"/api/v1/courses/{course_id}/exports/offline-pack", params={"version_id": replanned["schedule"]["version"]["id"]}).json()
        archive = client.get(exported["download_url"])
        assert archive.status_code == 200
        with zipfile.ZipFile(io.BytesIO(archive.content)) as package:
            assert {"index.html", "MANIFEST.json", "data/course.json", "app/service-worker.js"} <= set(package.namelist())
            assert "window.__PACK__" in package.read("index.html").decode()
            offline_app = package.read("app/app.js").decode()
            assert "fetch(" not in offline_app
            assert "pack.lessons.filter" in offline_app
            assert "pack.assessments.filter" in offline_app
            assert "const pack=window.__PACK__,esc=" in offline_app


def test_account_cannot_read_another_teachers_course_or_job(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(db, "DATABASE_PATH", tmp_path / "curriculumos.db")
    monkeypatch.setattr(services, "UPLOAD_DIR", tmp_path / "uploads")
    with TestClient(app) as client:
        owner = client.post("/api/v1/auth/sign-up", json={"email": "owner@example.edu", "password": "correct-horse-battery-staple", "display_name": "Course Owner"}).json()
        client.headers.update({"Authorization": f"Bearer {owner['access_token']}"})
        course = client.post("/api/v1/courses", json={"name": "Private physics", "grade": "XI", "subject": "Physics", "section": "A"}).json()
        upload = client.post(f"/api/v1/courses/{course['id']}/documents", files={"file": ("private.txt", b"Force changes motion.", "text/plain")})
        stranger = client.post("/api/v1/auth/sign-up", json={"email": "stranger@example.edu", "password": "correct-horse-battery-staple", "display_name": "Other Teacher"}).json()
        client.headers.update({"Authorization": f"Bearer {stranger['access_token']}"})
        assert client.get(f"/api/v1/courses/{course['id']}/dashboard").status_code == 403
        assert client.get(f"/api/v1/jobs/{upload.json()['job_id']}").status_code == 403


def test_failed_document_parse_is_visible_and_retryable(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(db, "DATABASE_PATH", tmp_path / "curriculumos.db")
    monkeypatch.setattr(services, "UPLOAD_DIR", tmp_path / "uploads")
    with TestClient(app) as client:
        account = client.post("/api/v1/auth/sign-up", json={"email": "parser@example.edu", "password": "correct-horse-battery-staple", "display_name": "Parser Teacher"}).json()
        client.headers.update({"Authorization": f"Bearer {account['access_token']}"})
        course = client.post("/api/v1/courses", json={"name": "Parsing recovery", "grade": "XI", "subject": "Physics", "section": "A"}).json()
        failed = client.post(f"/api/v1/courses/{course['id']}/documents", files={"file": ("broken.pdf", b"not-a-valid-pdf", "application/pdf")})
        assert failed.status_code == 422
        details = failed.json()["error"]["details"]
        dashboard = client.get(f"/api/v1/courses/{course['id']}/dashboard").json()
        assert dashboard["jobs"][0]["id"] == details["job_id"]
        assert dashboard["jobs"][0]["status"] == "failed"
        retried = client.post(f"/api/v1/courses/{course['id']}/documents/{details['document_id']}/retry")
        assert retried.status_code == 422
        assert client.get(f"/api/v1/jobs/{retried.json()['error']['details']['job_id']}").json()["status"] == "failed"
