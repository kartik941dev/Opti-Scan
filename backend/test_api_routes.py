"""
Comprehensive FastAPI Backend Routes & Endpoints Test (Phase 4).
"""

import sys
from pathlib import Path
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app


def test_fastapi_backend_endpoints():
    print("=" * 60)
    print("OPTISCAN FASTAPI BACKEND API SUITE (PHASE 4)")
    print("=" * 60)

    client = TestClient(app)

    # 1. Health Checks
    print("\n[TEST 1] Testing Root & Health Check Endpoints...")
    res_root = client.get("/")
    assert res_root.status_code == 200
    print("  -> GET / [200 OK]:", res_root.json())

    res_health = client.get("/health")
    assert res_health.status_code == 200
    print("  -> GET /health [200 OK]:", res_health.json())

    # 2. Authentication Flow
    print("\n[TEST 2] Testing Educator Authentication (OAuth2 / JWT)...")
    res_login = client.post(
        "/api/v1/auth/login",
        data={"username": "teacher@optiscan.dev", "password": "optiscan2026"},
    )
    assert res_login.status_code == 200, f"Login failed: {res_login.text}"
    token_data = res_login.json()
    token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("  -> POST /api/v1/auth/login [200 OK]: Token acquired for user:", token_data["user"]["email"])

    res_me = client.get("/api/v1/auth/me", headers=headers)
    assert res_me.status_code == 200
    print("  -> GET /api/v1/auth/me [200 OK]: Authenticated user:", res_me.json())

    # 3. Exams CRUD
    print("\n[TEST 3] Testing Exams Management Endpoints...")
    res_exams = client.get("/api/v1/exams", headers=headers)
    assert res_exams.status_code == 200
    exams = res_exams.json()
    print(f"  -> GET /api/v1/exams [200 OK]: Found {len(exams)} existing exams")
    assert len(exams) > 0
    exam_id = exams[0]["id"]

    # 4. Answer Key Management
    print(f"\n[TEST 4] Testing Answer Key & Marking Rules for Exam #{exam_id}...")
    res_key = client.get(f"/api/v1/answer-keys/{exam_id}", headers=headers)
    assert res_key.status_code == 200
    key_data = res_key.json()
    print(f"  -> GET /api/v1/answer-keys/{exam_id} [200 OK]: Loaded {len(key_data['answers'])} question keys")

    # 5. Live OMR Evaluation via Demo Sheets
    print(f"\n[TEST 5] Testing POST /api/v1/omr/demo-sheets (5 sheets live evaluation)...")
    res_omr = client.post("/api/v1/omr/demo-sheets", data={"exam_id": exam_id})
    assert res_omr.status_code == 200
    graded_subs = res_omr.json()
    print(f"  -> POST /api/v1/omr/demo-sheets [200 OK]: Graded {len(graded_subs)} student sheets")
    for s in graded_subs:
        print(f"     • Candidate #{s['student_id']}: Score {s['total_score']}/{s['max_score']} ({s['percentage']}%) in {s['processing_time_ms']}ms")

    # 6. Results Overview & Psychometrics
    print(f"\n[TEST 6] Testing Psychometrics Overview for Exam #{exam_id}...")
    res_ov = client.get(f"/api/v1/results/{exam_id}/overview", headers=headers)
    assert res_ov.status_code == 200
    overview = res_ov.json()
    print(f"  -> GET /api/v1/results/{exam_id}/overview [200 OK]:")
    print(f"     • Total Graded: {overview['total_candidates']}")
    print(f"     • Class Average Score: {overview['average_score']} pts ({overview['average_percentage']}%)")
    print(f"     • Pass Rate: {overview['pass_rate_pct']}%")
    print(f"     • Test Reliability (KR-20): {overview['kr20_reliability']}")

    # 7. Item Analysis
    print(f"\n[TEST 7] Testing Question Item Analysis (Difficulty P & Discrimination D)...")
    res_items = client.get(f"/api/v1/results/{exam_id}/item-analysis", headers=headers)
    assert res_items.status_code == 200
    items = res_items.json()
    print(f"  -> GET /api/v1/results/{exam_id}/item-analysis [200 OK]: Computed item diagnostics for {len(items)} questions")
    sample_q = items[0]
    print(f"     • Q1: Key={sample_q['correct_key']} | Difficulty P={sample_q['difficulty_p']} ({sample_q['difficulty_label']}) | Discrimination D={sample_q['discrimination_d']}")

    # 8. Student Scorecard PDF Generation
    if graded_subs:
        test_student_id = graded_subs[0]["student_id"]
        print(f"\n[TEST 8] Testing PDF Scorecard generation for Student #{test_student_id}...")
        res_pdf = client.get(f"/api/v1/results/{exam_id}/scorecard/{test_student_id}")
        assert res_pdf.status_code == 200
        assert res_pdf.headers["content-type"] == "application/pdf"
        print(f"  -> GET /api/v1/results/{exam_id}/scorecard/{test_student_id} [200 OK]: Received PDF ({len(res_pdf.content)} bytes)")

    print("\n" + "=" * 60)
    print("ALL PHASE 4 FASTAPI BACKEND & ROUTE TESTS PASSED (100% SUCCESS)")
    print("=" * 60)


if __name__ == "__main__":
    test_fastapi_backend_endpoints()
