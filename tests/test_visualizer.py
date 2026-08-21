"""
Unit tests for Visual Audit Overlays & Annotation Renderer (Phase 7).
"""

import cv2
import numpy as np
import pytest

from src.visualizer import (
    COLOR_AMBER,
    COLOR_CORRECT,
    COLOR_INCORRECT,
    COLOR_KEY,
    COLOR_WHITE,
    draw_amber_flag,
    draw_correct_indicator,
    draw_header_scorecard,
    draw_incorrect_indicator,
    draw_key_indicator,
    generate_annotated_sheet,
    overlay_transparent_circle,
)


class TestVisualizer:
    """Test suite for Phase 7: Visual Audit Overlays."""

    def test_drawing_primitives(self):
        """Step 7.1: Test low-level annotation drawing primitives."""
        # 1. Base white canvas
        canvas = np.full((200, 200, 3), 255, dtype=np.uint8)

        # 2. Test overlay_transparent_circle
        out_circle = overlay_transparent_circle(canvas.copy(), cx=50, cy=50, radius=20, color_bgr=COLOR_CORRECT, alpha=0.50)
        assert out_circle.shape == (200, 200, 3)
        # Check that center pixel has high green value and lower red/blue
        center_px = out_circle[50, 50]
        # COLOR_CORRECT is BGR (34, 177, 76) -> B=34, G=177, R=76
        # Blended with (255, 255, 255) at 0.5 -> G should be significantly higher than B
        assert center_px[1] > center_px[0]  # G > B

        # 3. Test draw_correct_indicator
        out_correct = draw_correct_indicator(canvas.copy(), cx=100, cy=100, r=15)
        assert out_correct.shape == (200, 200, 3)
        assert out_correct[100, 100][1] > out_correct[100, 100][0]  # Green dominant

        # 4. Test draw_incorrect_indicator
        out_incorrect = draw_incorrect_indicator(canvas.copy(), cx=100, cy=100, r=15)
        assert out_incorrect.shape == (200, 200, 3)
        # COLOR_INCORRECT is (36, 28, 237) -> R dominant
        assert out_incorrect[100, 100][2] > out_incorrect[100, 100][0]  # R > B

        # 5. Test draw_key_indicator
        out_key = draw_key_indicator(canvas.copy(), cx=100, cy=100, r=15)
        assert out_key.shape == (200, 200, 3)
        # COLOR_KEY is (232, 162, 0) -> B & G dominant
        assert out_key[100, 100][0] > 0

        # 6. Test draw_amber_flag
        out_amber = draw_amber_flag(canvas.copy(), cx=100, cy=100, r=15)
        assert out_amber.shape == (200, 200, 3)
        # COLOR_AMBER is (0, 140, 255) -> R dominant
        assert out_amber[100, 100][2] > out_amber[100, 100][0]

        # 7. Error handling
        with pytest.raises(ValueError):
            overlay_transparent_circle(np.array([]), cx=10, cy=10, radius=5, color_bgr=COLOR_CORRECT)

    def test_draw_header_scorecard(self):
        """Step 7.2: Test header scorecard banner rendering and grading brackets."""
        canvas = np.full((1000, 1000, 3), 255, dtype=np.uint8)

        eval_report_high = {
            "student_id": "STU_999",
            "exam_id": "PHYS_CHEM_2026",
            "total_score": 380.0,
            "max_score": 400.0,
            "percentage": 95.0,
            "accuracy_pct": 96.0,
            "counts": {
                "total_questions": 100,
                "attempted": 98,
                "correct": 95,
                "incorrect": 3,
                "blank": 2,
                "multiple_marked": 0,
                "faint_marked": 0,
                "bonus": 0,
            },
            "sectional_scores": {
                "Physics": {"score": 190.0, "max_score": 200.0},
                "Chemistry": {"score": 190.0, "max_score": 200.0},
            },
        }

        # Render on high score
        res_high = draw_header_scorecard(canvas.copy(), eval_report_high)
        assert res_high.shape == (1000, 1000, 3)

        # Test middle score bracket (50-74%)
        eval_report_mid = eval_report_high.copy()
        eval_report_mid["percentage"] = 60.0
        res_mid = draw_header_scorecard(canvas.copy(), eval_report_mid)
        assert res_mid.shape == (1000, 1000, 3)

        # Test qualified bracket (35-49%)
        eval_report_qual = eval_report_high.copy()
        eval_report_qual["percentage"] = 40.0
        res_qual = draw_header_scorecard(canvas.copy(), eval_report_qual)
        assert res_qual.shape == (1000, 1000, 3)

        # Test low score bracket (<35%)
        eval_report_low = eval_report_high.copy()
        eval_report_low["percentage"] = 25.0
        res_low = draw_header_scorecard(canvas.copy(), eval_report_low)
        assert res_low.shape == (1000, 1000, 3)

        # Test custom position
        res_custom = draw_header_scorecard(canvas.copy(), eval_report_high, pos=(10, 10, 500, 200))
        assert res_custom.shape == (1000, 1000, 3)

        # Error handling
        with pytest.raises(ValueError):
            draw_header_scorecard(np.array([]), eval_report_high)

    def test_generate_annotated_sheet(self):
        """Step 7.2 & 7.3: Test full-sheet annotation overlay generation."""
        from src.models.template import TemplateConfig

        template = TemplateConfig.load_from_json("config/template_100q.json")
        canvas = np.full((template.canvas_height, template.canvas_width, 3), 255, dtype=np.uint8)

        # Construct realistic multi-status evaluation report
        eval_result = {
            "student_id": "202641",
            "exam_id": "MIDTERM_100Q",
            "exam_title": "Standard Assessment",
            "total_score": 320.0,
            "max_score": 400.0,
            "percentage": 80.0,
            "accuracy_pct": 85.0,
            "counts": {
                "total_questions": 100,
                "attempted": 90,
                "correct": 80,
                "incorrect": 10,
                "blank": 10,
                "multiple_marked": 2,
                "faint_marked": 1,
                "bonus": 1,
            },
            "questions_audit": [
                # Q1: Correct (Selected A, Key A)
                {
                    "question_number": 1,
                    "selected_option": "A",
                    "correct_answer": "A",
                    "status": "SINGLE_MARK",
                    "is_correct": True,
                    "is_bonus": False,
                    "score_delta": 4.0,
                },
                # Q2: Incorrect (Selected B, Key C)
                {
                    "question_number": 2,
                    "selected_option": "B",
                    "correct_answer": "C",
                    "status": "SINGLE_MARK",
                    "is_correct": False,
                    "is_bonus": False,
                    "score_delta": -1.0,
                },
                # Q3: Blank (Selected None, Key D)
                {
                    "question_number": 3,
                    "selected_option": None,
                    "correct_answer": "D",
                    "status": "BLANK",
                    "is_correct": False,
                    "is_bonus": False,
                    "score_delta": 0.0,
                },
                # Q4: Multiple marked (Key B)
                {
                    "question_number": 4,
                    "selected_option": "A",
                    "correct_answer": "B",
                    "status": "MULTIPLE_MARKED",
                    "is_correct": False,
                    "is_bonus": False,
                    "score_delta": -1.0,
                },
                # Q5: Bonus question
                {
                    "question_number": 5,
                    "selected_option": "A",
                    "correct_answer": "BONUS",
                    "status": "SINGLE_MARK",
                    "is_correct": True,
                    "is_bonus": True,
                    "score_delta": 4.0,
                },
                # Q6: Multiple correct keys (e.g. ['A', 'B'])
                {
                    "question_number": 6,
                    "selected_option": "B",
                    "correct_answer": ["A", "B"],
                    "status": "SINGLE_MARK",
                    "is_correct": True,
                    "is_bonus": False,
                    "score_delta": 4.0,
                },
            ],
            "sectional_scores": {},
        }

        # 1. Generate full annotated sheet
        annotated = generate_annotated_sheet(canvas, eval_result, template)

        assert annotated is not None
        assert annotated.shape == (template.canvas_height, template.canvas_width, 3)

        # 2. Check Q1 bubble (A is correct): center should have green tint
        q1_a = template.get_question(1).bubbles["A"]
        assert annotated[q1_a.cy, q1_a.cx][1] > annotated[q1_a.cy, q1_a.cx][0]  # G > B

        # 3. Check Q2 bubble (B is wrong): center should have red tint
        q2_b = template.get_question(2).bubbles["B"]
        assert annotated[q2_b.cy, q2_b.cx][2] > annotated[q2_b.cy, q2_b.cx][0]  # R > B

        # 4. Check Q2 correct key (C is target): should have key indicator
        q2_c = template.get_question(2).bubbles["C"]
        assert annotated[q2_c.cy, q2_c.cx][0] > 0

        # 5. Check Q3 blank (Key D): should have key indicator on D
        q3_d = template.get_question(3).bubbles["D"]
        assert annotated[q3_d.cy, q3_d.cx][0] > 0

        # 6. Test with Grayscale input
        gray_canvas = np.full((template.canvas_height, template.canvas_width), 255, dtype=np.uint8)
        annotated_from_gray = generate_annotated_sheet(gray_canvas, eval_result, template)
        assert annotated_from_gray.shape == (template.canvas_height, template.canvas_width, 3)

        # 7. Test without scorecard banner
        annotated_no_banner = generate_annotated_sheet(canvas, eval_result, template, draw_scorecard=False)
        assert annotated_no_banner.shape == (template.canvas_height, template.canvas_width, 3)

        # 8. Test error handling
        with pytest.raises(ValueError):
            generate_annotated_sheet(np.array([]), eval_result, template)
        with pytest.raises(ValueError):
            generate_annotated_sheet(canvas, None, template)
        with pytest.raises(ValueError):
            generate_annotated_sheet(canvas, eval_result, None)

    def test_end_to_end_pipeline_with_visualization(self, tmp_path):
        """Integration test: mock sheet -> detect -> score -> visualize."""
        from src.bubble_detect import detect_all_sheet_bubbles
        from src.models.answer_key import AnswerKey, MarkingRule
        from src.models.template import TemplateConfig
        from src.scorer import score_student_sheet
        from tests.fixtures.generate_mock_omr import generate_synthetic_omr_sheet

        # 1. Generate synthetic OMR sheet
        filled_answers = {1: "A", 2: "B", 3: "C", 4: "D", 5: "A"}
        raw_img, gt_meta = generate_synthetic_omr_sheet(num_questions=100, filled_answers=filled_answers, student_id="123456")
        gray_img = cv2.cvtColor(raw_img, cv2.COLOR_BGR2GRAY)
        template = TemplateConfig.load_from_json("config/template_100q.json")

        # 2. Detect bubbles
        detections = detect_all_sheet_bubbles(raw_img, gray_img, template)
        assert len(detections) == 100

        # 3. Create Answer Key and Score
        ak_answers = {str(i): "A" for i in range(1, 101)}
        ak = AnswerKey(
            exam_id="INTEGRATION_TEST_01",
            answers_map=ak_answers,
            marking_rules=MarkingRule(correct=4.0, incorrect=-1.0),
        )
        score_report = score_student_sheet(detections, ak, student_id="123456")
        assert score_report["student_id"] == "123456"

        # 4. Generate Annotated Sheet
        annotated_sheet = generate_annotated_sheet(raw_img, score_report, template)
        assert annotated_sheet.shape == raw_img.shape

        # Verify saving to disk
        out_path = tmp_path / "annotated_audit.png"
        cv2.imwrite(str(out_path), annotated_sheet)
        assert out_path.exists()
        assert out_path.stat().st_size > 10000


def test_drawing_primitives():
    """Standalone test entrypoint matching PROJECT.md Step 7.1 command."""
    TestVisualizer().test_drawing_primitives()


def test_generate_annotated_sheet():
    """Standalone test entrypoint matching PROJECT.md Step 7.2 command."""
    TestVisualizer().test_generate_annotated_sheet()

