"""
Benchmark regression test for the 10 National Engineering & Science Assessment OMR sheets.
"""

import csv
from pathlib import Path
import pytest
from backend.app.routes.omr_upload import process_omr_image, load_template_config
from backend.app.db.models import AnswerKeyModel, MarkingRule, SectionConfig
from backend.app.routes.answer_key import generate_default_100q_answers


def test_national_assessment_benchmark_10_sheets():
    files_dir = Path(r"C:\Users\kp941\OneDrive\Desktop\files")
    expected_csv = files_dir / "expected_scores_all10.csv"
    if not expected_csv.exists():
        pytest.skip("Benchmark files directory not present on this machine")

    answers = generate_default_100q_answers()
    ak = AnswerKeyModel(
        exam_id="test_nesa_exam",
        exam_title="National Engineering & Science Assessment 2026",
        answers=answers,
        default_rule=MarkingRule(correct=4.0, incorrect=-1.0, unattempted=0.0, multi_mark=0.0, bonus=4.0),
        sections=[
            SectionConfig(name="Section A (Physics)", q_start=1, q_end=25),
            SectionConfig(name="Section B (Chemistry)", q_start=26, q_end=50),
            SectionConfig(name="Section C (Mathematics)", q_start=51, q_end=75),
            SectionConfig(name="Section D (Biology)", q_start=76, q_end=100),
        ]
    )
    template_cfg = load_template_config()

    with open(expected_csv, "r", encoding="utf-8") as f:
        expected_rows = list(csv.DictReader(f))

    for row in expected_rows:
        pdf_path = files_dir / row["file"]
        if not pdf_path.exists():
            continue

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        res = process_omr_image(
            image_bytes=pdf_bytes,
            filename=row["file"],
            answer_key=ak,
            template_config=template_cfg,
            exam_id="test_nesa_exam",
        )

        assert res["student_id"] == row["roll_no"], f"Mismatch roll for {row['file']}"
        assert res["total_score"] == float(row["total_marks"]), f"Mismatch score for {row['file']}"
        assert res["total_correct"] == int(row["correct"]), f"Mismatch correct for {row['file']}"
        assert res["total_incorrect"] == int(row["incorrect"]), f"Mismatch incorrect for {row['file']}"
