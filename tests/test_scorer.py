"""
Unit tests for Scoring Engine, Marking Schemes, and Answer Key Models (Phase 6).
"""

from pathlib import Path

import cv2
import numpy as np
import pytest
from pydantic import ValidationError

from src.align import align_pipeline
from src.bubble_detect import detect_all_sheet_bubbles
from src.models.answer_key import AnswerKey, MarkingRule, SectionConfig
from src.models.template import TemplateConfig
from src.preprocess import preprocess_pipeline
from src.scorer import compute_sectional_scores, evaluate_question_response, score_student_sheet
from src.student_id import decode_student_id
from src.utils.exceptions import ScoringError, StudentIdParsingError
from tests.fixtures.generate_mock_omr import generate_synthetic_omr_sheet


class TestScorer:
    """Test suite for Phase 6: Scoring Engine & Models."""

    def test_marking_rule_evaluation(self):
        """Step 6.1: Test MarkingRule score delta computation."""
        rule = MarkingRule(correct=4.0, incorrect=-1.0, unattempted=0.0, multi_mark=-1.0, bonus=4.0)

        # Correct
        assert rule.evaluate_mark(status="SINGLE_MARK", is_correct=True) == 4.0

        # Incorrect
        assert rule.evaluate_mark(status="SINGLE_MARK", is_correct=False) == -1.0

        # Blank / Unattempted
        assert rule.evaluate_mark(status="BLANK", is_correct=False) == 0.0

        # Multiple Marked
        assert rule.evaluate_mark(status="MULTIPLE_MARKED", is_correct=False) == -1.0

        # Bonus
        assert rule.evaluate_mark(status="BLANK", is_bonus=True) == 4.0
        assert rule.evaluate_mark(status="SINGLE_MARK", is_correct=False, is_bonus=True) == 4.0

    def test_section_config(self):
        """Step 6.1: Test SectionConfig boundaries and custom rules."""
        custom_rule = MarkingRule(correct=5.0, incorrect=-2.0)
        sec = SectionConfig(name="Mathematics", q_start=1, q_end=25, rule=custom_rule)

        assert sec.name == "Mathematics"
        assert sec.question_count == 25
        assert sec.contains(1) is True
        assert sec.contains(25) is True
        assert sec.contains(26) is False

        # Invalid range: q_start > q_end
        with pytest.raises(ValidationError):
            SectionConfig(name="Invalid", q_start=30, q_end=20)

    def test_answer_key_validation(self, tmp_path: Path):
        """Step 6.1: Test AnswerKey schema parsing, question overrides, and JSON serialization."""
        answers = {
            "1": "A",
            "2": ["B", "C"],
            "3": "BONUS",
            "4": "D",
        }
        sec1 = SectionConfig(name="Sec1", q_start=1, q_end=2, rule=MarkingRule(correct=3.0, incorrect=0.0))
        sec2 = SectionConfig(name="Sec2", q_start=3, q_end=4)

        ak = AnswerKey(
            exam_id="TEST_EXAM_01",
            exam_title="Test Exam",
            answers_map=answers,
            marking_rules=MarkingRule(correct=4.0, incorrect=-1.0),
            sections=[sec1, sec2],
        )

        assert ak.exam_id == "TEST_EXAM_01"
        assert ak.total_questions == 4
        assert ak.get_correct_answer(1) == "A"
        assert ak.get_correct_answer(2) == ["B", "C"]
        assert ak.get_correct_answer(3) == "BONUS"

        # Section rule resolution
        assert ak.get_rule_for_question(1).correct == 3.0
        assert ak.get_rule_for_question(1).incorrect == 0.0
        assert ak.get_rule_for_question(3).correct == 4.0  # Falls back to default

        # JSON roundtrip
        out_file = tmp_path / "test_ak.json"
        ak.save_to_json(out_file)
        assert out_file.exists()

        loaded_ak = AnswerKey.load_from_json(out_file)
        assert loaded_ak.exam_id == "TEST_EXAM_01"
        assert loaded_ak.get_correct_answer(2) == ["B", "C"]

    def test_standard_answer_key_file(self):
        """Step 6.1: Verify config/answer_key.json exists and parses correctly."""
        ak_path = Path("config/answer_key.json")
        assert ak_path.exists(), "config/answer_key.json must exist"

        ak = AnswerKey.load_from_json(ak_path)
        assert ak.total_questions == 100
        assert len(ak.sections) == 4
        assert ak.get_correct_answer(1) == "A"
        assert ak.get_correct_answer(50) == ["A", "B"]
        assert ak.get_correct_answer(100) == "BONUS"

        # Check section C custom negative marking rule (-2.0)
        rule_c = ak.get_rule_for_question(60)
        assert rule_c.incorrect == -2.0

    def test_decode_student_id(self):
        """Step 6.2: Test student ID roll number decoding."""
        # 1. Test end-to-end on synthetic sheet with known student ID "202641"
        img_sheet, meta = generate_synthetic_omr_sheet(
            num_questions=50,
            student_id="202641",
            noise_level=2.0,
        )
        rgb_scaled, gray_clahe, binary_mask, _ = preprocess_pipeline(img_sheet)
        warped_rgb, warped_binary, _ = align_pipeline(rgb_scaled, binary_mask)

        id_grid_config = meta["id_grid_layout"]
        decoded = decode_student_id(warped_binary, id_grid_config)
        assert decoded == "202641"

        # 2. Test synthetic binary canvas with custom ID bubbles
        canvas = np.zeros((500, 500), dtype=np.uint8)
        # Create a 4-column grid (digits 0..9)
        test_grid = {}
        for col in range(4):
            for digit in range(10):
                cx = 50 + col * 50
                cy = 50 + digit * 40
                key = f"col_{col}_d_{digit}"
                test_grid[key] = {"cx": cx, "cy": cy, "r": 12, "col": col, "digit": digit}

        # Mark "7309"
        cv2.circle(canvas, (50 + 0 * 50, 50 + 7 * 40), 11, 255, -1)  # col 0 -> 7
        cv2.circle(canvas, (50 + 1 * 50, 50 + 3 * 40), 11, 255, -1)  # col 1 -> 3
        cv2.circle(canvas, (50 + 2 * 50, 50 + 0 * 40), 11, 255, -1)  # col 2 -> 0
        cv2.circle(canvas, (50 + 3 * 50, 50 + 9 * 40), 11, 255, -1)  # col 3 -> 9

        decoded_custom = decode_student_id(canvas, test_grid)
        assert decoded_custom == "7309"

        # 3. Test blank column handling
        canvas_blank = canvas.copy()
        # Erase col 1 (digit 3)
        cv2.circle(canvas_blank, (50 + 1 * 50, 50 + 3 * 40), 11, 0, -1)
        decoded_blank = decode_student_id(canvas_blank, test_grid)
        assert decoded_blank == "7X09"

        # Strict mode on blank column raises StudentIdParsingError
        with pytest.raises(StudentIdParsingError):
            decode_student_id(canvas_blank, test_grid, strict=True)

        # 4. Test ambiguous multi-mark handling
        canvas_multi = canvas.copy()
        cv2.circle(canvas_multi, (50 + 0 * 50, 50 + 2 * 40), 11, 255, -1)  # also mark digit 2 on col 0
        decoded_multi = decode_student_id(canvas_multi, test_grid)
        assert decoded_multi == "?309"

        with pytest.raises(StudentIdParsingError):
            decode_student_id(canvas_multi, test_grid, strict=True)

        # 5. Invalid / empty inputs
        with pytest.raises(ValueError):
            decode_student_id(np.array([]), test_grid)

        with pytest.raises(StudentIdParsingError):
            decode_student_id(canvas, {})

    def test_scoring_rules(self):
        """Step 6.3: Test scoring evaluation, positive/negative/bonus rules, and summary metrics."""
        # 1. Load standard 100Q answer key
        ak = AnswerKey.load_from_json("config/answer_key.json")

        # 2. Build mock student detection
        mock_detections: dict[int, dict] = {}
        for q in range(1, 101):
            if q <= 20:
                # Correct answers
                ans = ak.get_correct_answer(q)
                opt = ans if isinstance(ans, str) else ans[0]
                mock_detections[q] = {"selected_option": opt, "status": "SINGLE_MARK", "confidence": 0.95}
            elif 21 <= q <= 30:
                # Incorrect answers ('Z' or mismatched)
                mock_detections[q] = {"selected_option": "Z", "status": "SINGLE_MARK", "confidence": 0.90}
            elif 31 <= q <= 40:
                # Blank unattempted
                mock_detections[q] = {"selected_option": None, "status": "BLANK", "confidence": 0.99}
            elif 41 <= q <= 45:
                # Multiple marked
                mock_detections[q] = {"selected_option": None, "status": "MULTIPLE_MARKED", "confidence": 0.20}
            elif q == 50:
                # Multi-correct question (answer is ['A', 'B']) -> answer 'B' is correct
                mock_detections[q] = {"selected_option": "B", "status": "SINGLE_MARK", "confidence": 0.92}
            elif q == 60:
                # Section C question (incorrect with custom -2.0 penalty)
                mock_detections[q] = {"selected_option": "Z", "status": "SINGLE_MARK", "confidence": 0.88}
            elif q == 100:
                # Bonus question (answer is 'BONUS')
                mock_detections[q] = {"selected_option": "C", "status": "SINGLE_MARK", "confidence": 0.85}
            else:
                # Remaining are correct
                ans = ak.get_correct_answer(q)
                opt = ans if isinstance(ans, str) else (ans[0] if isinstance(ans, list) else "A")
                mock_detections[q] = {"selected_option": opt, "status": "SINGLE_MARK", "confidence": 0.95}

        # 3. Score sheet
        report = score_student_sheet(mock_detections, ak, student_id="STU_998877")

        assert report["student_id"] == "STU_998877"
        assert report["exam_id"] == "OPTISCAN_100Q_STANDARD_2026"
        assert report["counts"]["total_questions"] == 100
        assert report["counts"]["blank"] == 10
        assert report["counts"]["multiple_marked"] == 5
        assert report["counts"]["bonus"] == 1

        # Check section C custom negative mark on Q60
        q60_audit = next(item for item in report["questions_audit"] if item["question_number"] == 60)
        assert q60_audit["score_delta"] == -2.0
        assert q60_audit["is_correct"] is False

        # Check bonus question 100
        q100_audit = next(item for item in report["questions_audit"] if item["question_number"] == 100)
        assert q100_audit["score_delta"] == 4.0
        assert q100_audit["is_bonus"] is True

        # Check multi-correct question 50
        q50_audit = next(item for item in report["questions_audit"] if item["question_number"] == 50)
        assert q50_audit["score_delta"] == 4.0
        assert q50_audit["is_correct"] is True

        # 4. Error handling
        with pytest.raises(ScoringError):
            score_student_sheet({}, ak)

        with pytest.raises(ScoringError):
            score_student_sheet(mock_detections, None)

    def test_sectional_scoring(self):
        """Step 6.4: Test subject sectional breakdown and aggregate metrics."""
        ak = AnswerKey.load_from_json("config/answer_key.json")

        # Mock responses across 4 sections
        mock_detections: dict[int, dict] = {}
        for q in range(1, 101):
            # Perfect Physics (1..25)
            if q <= 25:
                ans = ak.get_correct_answer(q)
                mock_detections[q] = {"selected_option": ans, "status": "SINGLE_MARK", "confidence": 0.95}
            # Mixed Chemistry (26..50)
            elif 26 <= q <= 35:
                ans = ak.get_correct_answer(q)
                mock_detections[q] = {"selected_option": ans, "status": "SINGLE_MARK", "confidence": 0.90}
            elif 36 <= q <= 40:
                mock_detections[q] = {"selected_option": "Z", "status": "SINGLE_MARK", "confidence": 0.85}
            elif 41 <= q <= 50:
                mock_detections[q] = {"selected_option": None, "status": "BLANK", "confidence": 0.99}
            # Remaining sections: blank
            else:
                mock_detections[q] = {"selected_option": None, "status": "BLANK", "confidence": 0.99}

        report = score_student_sheet(mock_detections, ak, student_id="STU_12345")
        sec_scores = report["sectional_scores"]

        assert len(sec_scores) == 4
        assert "Section A (Physics)" in sec_scores
        assert "Section B (Chemistry)" in sec_scores
        assert "Section C (Mathematics)" in sec_scores
        assert "Section D (Biology)" in sec_scores

        # Verify Physics Section (25 / 25 correct -> 100.0 score)
        phy = sec_scores["Section A (Physics)"]
        assert phy["score"] == 100.0
        assert phy["max_score"] == 100.0
        assert phy["percentage"] == 100.0
        assert phy["accuracy_pct"] == 100.0
        assert phy["counts"]["correct"] == 25
        assert phy["counts"]["blank"] == 0

        # Verify Chemistry Section (10 correct = +40, 5 wrong = -5, 10 blank = 0 -> score 35)
        chem = sec_scores["Section B (Chemistry)"]
        assert chem["score"] == 35.0
        assert chem["max_score"] == 100.0
        assert chem["counts"]["correct"] == 10
        assert chem["counts"]["incorrect"] == 5
        assert chem["counts"]["blank"] == 10

        # Fallback test with sections=None
        general_breakdown = compute_sectional_scores(report["questions_audit"], sections=None)
        assert "General" in general_breakdown
        assert general_breakdown["General"]["counts"]["total_questions"] == 100

        # Empty evaluations edge case
        assert compute_sectional_scores([]) == {}

    def test_end_to_end_scoring_pipeline(self):
        """Step 6.5: Comprehensive end-to-end scoring pipeline test on full synthetic sheet."""
        # 1. Load standard 100Q answer key and template
        ak = AnswerKey.load_from_json("config/answer_key.json")
        template = TemplateConfig.load_from_json("config/template_100q.json")

        # 2. Build student answers matching 90% of answer key
        student_answers: dict[int, Optional[str]] = {}
        for q in range(1, 101):
            key_ans = ak.get_correct_answer(q)
            if q <= 80:
                # 80 correct
                student_answers[q] = key_ans if isinstance(key_ans, str) else key_ans[0]
            elif 81 <= q <= 90:
                # 10 wrong
                student_answers[q] = "D" if key_ans != "D" else "A"
            else:
                # 10 blank
                student_answers[q] = None

        # 3. Generate synthetic OMR sheet
        img_sheet, meta = generate_synthetic_omr_sheet(
            num_questions=100,
            student_id="554433",
            filled_answers=student_answers,
            noise_level=3.0,
        )

        # 4. Run preprocessing & alignment
        rgb_scaled, gray_clahe, binary_mask, _ = preprocess_pipeline(img_sheet)
        warped_rgb, warped_binary, _ = align_pipeline(rgb_scaled, binary_mask)

        # 5. Decode student roll number
        decoded_id = decode_student_id(warped_binary, meta["id_grid_layout"])
        assert decoded_id == "554433"

        # 6. Detect question bubble choices
        detected_results = detect_all_sheet_bubbles(warped_binary, warped_rgb, template)
        assert len(detected_results) == 100

        # 7. Score student sheet
        report = score_student_sheet(detected_results, ak, student_id=decoded_id)

        assert report["student_id"] == "554433"
        assert report["counts"]["total_questions"] == 100
        assert report["counts"]["correct"] == 80
        assert report["counts"]["incorrect"] == 10
        assert report["counts"]["blank"] == 9
        assert report["counts"]["bonus"] == 1
        assert report["total_score"] > 300.0
        # High accuracy on attempted
        assert report["accuracy_pct"] >= 85.0
        assert len(report["sectional_scores"]) == 4
        assert len(report["questions_audit"]) == 100


def test_answer_key_validation(tmp_path: Path):
    """Standalone test entrypoint matching PROJECT.md Step 6.1 command."""
    TestScorer().test_answer_key_validation(tmp_path)


def test_decode_student_id():
    """Standalone test entrypoint matching PROJECT.md Step 6.2 command."""
    TestScorer().test_decode_student_id()


def test_scoring_rules():
    """Standalone test entrypoint matching PROJECT.md Step 6.3 command."""
    TestScorer().test_scoring_rules()


def test_sectional_scoring():
    """Standalone test entrypoint matching PROJECT.md Step 6.4 command."""
    TestScorer().test_sectional_scoring()


def test_end_to_end_scoring_pipeline():
    """Standalone test entrypoint matching PROJECT.md Step 6.5 command."""
    TestScorer().test_end_to_end_scoring_pipeline()




