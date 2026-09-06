"""
HTTP API Integration and Edge Case Tests for OptiScan Endpoints.
"""

import io
import json
import sys
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, ".")

from app.main import app

client = TestClient(app)


class TestAPIEndpoints(unittest.TestCase):
    """Test all API routes with edge cases."""

    def test_health_check(self):
        res = client.get("/api/v1/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "healthy")

    def test_get_and_save_answer_key_1000q(self):
        # 1. Save 1000Q Answer Key with 5 custom sections
        answers = {str(i): ["A", "B", "C", "D"][(i - 1) % 4] for i in range(1, 1001)}
        payload = {
            "exam_id": "exam_test_1000q",
            "exam_title": "1000-Question Mega Assessment",
            "total_questions": 1000,
            "answers": answers,
            "default_rule": {"correct": 4.0, "incorrect": -1.0, "unattempted": 0.0, "multi_mark": -1.0, "bonus": 4.0},
            "sections": [
                {"name": "Section A (Physics)", "q_start": 1, "q_end": 200},
                {"name": "Section B (Chemistry)", "q_start": 201, "q_end": 400},
                {"name": "Section C (Math)", "q_start": 401, "q_end": 600},
                {"name": "Section D (Bio)", "q_start": 601, "q_end": 800},
                {"name": "Section E (Aptitude)", "q_start": 801, "q_end": 1000},
            ],
        }
        res = client.post("/api/v1/answer-keys", json=payload)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["total_questions"], 1000)

        # 2. Get Answer Key
        get_res = client.get("/api/v1/answer-keys/exam_test_1000q")
        self.assertEqual(get_res.status_code, 200)
        data = get_res.json()
        self.assertEqual(len(data["answers"]), 1000)
        self.assertEqual(len(data["sections"]), 5)

        # 3. Export CSV
        export_res = client.get("/api/v1/answer-keys/exam_test_1000q/export-csv")
        self.assertEqual(export_res.status_code, 200)
        self.assertIn("text/csv", export_res.headers.get("content-type", ""))
        lines = export_res.text.strip().splitlines()
        self.assertEqual(len(lines), 1001)  # Header + 1000 Qs

    def test_upload_file_csv_endpoint(self):
        """Test uploading CSV file directly via HTTP multipart form."""
        csv_data = "Question,Section,Answer\nQ01,Physics,D\nQ02,Physics,D\nQ03,Physics,B\n"
        files = {"file": ("answer_key.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
        data = {"exam_id": "exam_upload_test"}

        res = client.post("/api/v1/answer-keys/upload-json", data=data, files=files)
        self.assertEqual(res.status_code, 200)
        res_data = res.json()
        self.assertEqual(len(res_data["answers"]), 3)
        self.assertEqual(res_data["answers"]["1"], "D")

    def test_paste_text_endpoint(self):
        """Test pasting raw answer key text via HTTP."""
        payload = {
            "exam_id": "exam_paste_test",
            "raw_text": "Q1: A\nQ2: B\nQ3: C\nQ4: D\nQ5: BONUS",
            "total_questions": 50,
        }
        res = client.post("/api/v1/answer-keys/paste-text", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data["answers"]), 5)
        self.assertEqual(data["answers"]["5"], "BONUS")

    def test_exams_crud_and_question_limit(self):
        """Test Exam creation with custom question limits up to 1000."""
        create_payload = {
            "title": "NEET Mock Test 2026",
            "code": "NEET-2026-720Q",
            "description": "Full syllabus mock examination",
            "total_questions": 720,
        }
        res = client.post("/api/v1/exams", json=create_payload)
        self.assertEqual(res.status_code, 201)
        exam_id = res.json()["id"]
        self.assertEqual(res.json()["total_questions"], 720)

        # Check auto-created key
        key_res = client.get(f"/api/v1/answer-keys/{exam_id}")
        self.assertEqual(key_res.status_code, 200)
        self.assertEqual(key_res.json()["total_questions"], 720)
        self.assertEqual(len(key_res.json()["answers"]), 720)


if __name__ == "__main__":
    unittest.main()
