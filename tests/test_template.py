"""
Unit tests for Pydantic Template Data Models (Phase 4).
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from src.models.template import (
    BubbleCoord,
    QuestionLayout,
    StudentIDBubble,
    TemplateConfig,
    validate_template_coordinates,
)
from src.utils.exceptions import TemplateError
from tests.fixtures.generate_mock_omr import generate_synthetic_omr_sheet


class TestTemplateModels:
    """Test suite for Step 4.1: Pydantic Template Data Models."""

    def test_bubble_coord_creation_and_properties(self):
        # Create with cx, cy, r
        b1 = BubbleCoord(cx=100, cy=200, r=13)
        assert b1.cx == 100
        assert b1.cy == 200
        assert b1.r == 13
        assert b1.radius == 13
        assert b1.bbox == (87, 187, 26, 26)
        assert b1.is_within_bounds(1654, 2339) is True

        # Create with radius alias
        b2 = BubbleCoord(cx=50, cy=50, radius=10)
        assert b2.r == 10

        # Out of bounds check
        b_out = BubbleCoord(cx=10, cy=10, r=15)
        assert b_out.is_within_bounds(20, 20) is False  # cx - r = -5 < 0

        # Negative coordinate validation error
        with pytest.raises(ValidationError):
            BubbleCoord(cx=-10, cy=50, r=10)

    def test_question_layout_options(self):
        q = QuestionLayout(
            q_num=1,
            section="Physics",
            bubbles={
                "A": {"cx": 100, "cy": 200, "r": 12},
                "B": {"cx": 140, "cy": 200, "r": 12},
                "C": {"cx": 180, "cy": 200, "r": 12},
                "D": {"cx": 220, "cy": 200, "r": 12},
            },
        )

        assert q.q_num == 1
        assert q.question_number == 1
        assert q.section == "Physics"
        assert len(q.options_map) == 4

        # Option retrieval (case-insensitive)
        bubble_a = q.get_bubble("a")
        assert bubble_a.cx == 100
        assert bubble_a.cy == 200

        # Non-existent option
        with pytest.raises(KeyError):
            q.get_bubble("E")

    def test_template_schema_validation(self, tmp_path: Path):
        """Unified test verifying TemplateConfig instantiation, validation, and JSON I/O."""
        # 1. Build template with multiple questions
        questions = []
        for i in range(1, 11):
            q = QuestionLayout(
                q_num=i,
                section="Section 1",
                options_map={
                    "A": BubbleCoord(cx=100 + i * 10, cy=200, r=10),
                    "B": BubbleCoord(cx=130 + i * 10, cy=200, r=10),
                },
            )
            questions.append(q)

        template = TemplateConfig(
            name="Test_A4_10Q",
            canvas_w=1654,
            canvas_h=2339,
            dpi=200,
            questions=questions,
        )

        assert template.name == "Test_A4_10Q"
        assert template.total_questions == 10
        assert template.canvas_width == 1654
        assert template.canvas_height == 2339
        assert template.validate_bounds() is True

        # 2. JSON Serialization & Deserialization
        json_file = tmp_path / "test_template.json"
        template.save_to_json(json_file)
        assert json_file.exists()

        loaded_template = TemplateConfig.load_from_json(json_file)
        assert loaded_template.name == template.name
        assert loaded_template.total_questions == 10
        assert loaded_template.get_question(5).q_num == 5

        # 3. Out-of-bounds question triggers TemplateError
        bad_questions = [
            QuestionLayout(
                q_num=1,
                options_map={"A": BubbleCoord(cx=2000, cy=3000, r=20)},
            )
        ]
        bad_template = TemplateConfig(
            name="Bad_Template",
            canvas_w=1654,
            canvas_h=2339,
            questions=bad_questions,
        )
        with pytest.raises(TemplateError):
            bad_template.validate_bounds()

    def test_synthetic_omr_metadata_compatibility(self):
        # Generate synthetic sheet metadata and convert into TemplateConfig
        _, metadata = generate_synthetic_omr_sheet(num_questions=25)

        template = TemplateConfig(
            name=metadata["format"],
            canvas_w=metadata["canvas_dimensions"]["width"],
            canvas_h=metadata["canvas_dimensions"]["height"],
            dpi=metadata["canvas_dimensions"]["dpi"],
            questions=metadata["questions_layout"],
            student_id_grid=metadata["id_grid_layout"],
        )

        assert template.total_questions == 25
        assert template.validate_bounds() is True
        assert template.get_question(1) is not None
        assert len(template.get_question(1).options_map) == 4

    def test_validate_template_coordinates(self):
        """Step 4.4: Thorough coordinate bounds validator testing across all 4 edges and ID grids."""
        # 1. Valid inside canvas
        template = TemplateConfig(
            name="Simple_Template",
            canvas_w=1000,
            canvas_h=1000,
            questions=[
                QuestionLayout(
                    q_num=1,
                    options_map={"A": BubbleCoord(cx=500, cy=500, r=10)},
                )
            ],
            student_id_grid={
                "col_0_digit_0": {"cx": 200, "cy": 300, "r": 11, "digit": 0, "col": 0}
            }
        )
        assert validate_template_coordinates(template, (1000, 1000)) is True

        # 2. Left edge breach: cx - r < 0
        left_breach = TemplateConfig(
            name="Left_Breach",
            canvas_w=1000,
            canvas_h=1000,
            questions=[QuestionLayout(q_num=1, options_map={"A": BubbleCoord(cx=5, cy=500, r=10)})],
        )
        with pytest.raises(TemplateError) as exc_info:
            validate_template_coordinates(left_breach, (1000, 1000))
        assert "exceeds canvas bounds" in str(exc_info.value)

        # 3. Right edge breach: cx + r > W
        right_breach = TemplateConfig(
            name="Right_Breach",
            canvas_w=1000,
            canvas_h=1000,
            questions=[QuestionLayout(q_num=1, options_map={"A": BubbleCoord(cx=995, cy=500, r=10)})],
        )
        with pytest.raises(TemplateError):
            validate_template_coordinates(right_breach, (1000, 1000))

        # 4. Top edge breach: cy - r < 0
        top_breach = TemplateConfig(
            name="Top_Breach",
            canvas_w=1000,
            canvas_h=1000,
            questions=[QuestionLayout(q_num=1, options_map={"A": BubbleCoord(cx=500, cy=8, r=10)})],
        )
        with pytest.raises(TemplateError):
            validate_template_coordinates(top_breach, (1000, 1000))

        # 5. Bottom edge breach: cy + r > H
        bottom_breach = TemplateConfig(
            name="Bottom_Breach",
            canvas_w=1000,
            canvas_h=1000,
            questions=[QuestionLayout(q_num=1, options_map={"A": BubbleCoord(cx=500, cy=995, r=10)})],
        )
        with pytest.raises(TemplateError):
            validate_template_coordinates(bottom_breach, (1000, 1000))

        # 6. Student ID grid breach
        id_breach = TemplateConfig(
            name="ID_Breach",
            canvas_w=1000,
            canvas_h=1000,
            questions=[QuestionLayout(q_num=1, options_map={"A": BubbleCoord(cx=500, cy=500, r=10)})],
            student_id_grid={
                "col_0_digit_0": {"cx": 995, "cy": 300, "r": 11, "digit": 0, "col": 0}
            }
        )
        with pytest.raises(TemplateError):
            validate_template_coordinates(id_breach, (1000, 1000))



    def test_preset_templates_100q_and_50q(self):
        """Step 4.2: Verify standard preset config JSON files exist and pass validation."""
        template_100q_path = Path("config/template_100q.json")
        template_50q_path = Path("config/template_50q.json")

        assert template_100q_path.exists(), "config/template_100q.json must exist"
        assert template_50q_path.exists(), "config/template_50q.json must exist"

        t100 = TemplateConfig.load_from_json(template_100q_path)
        assert t100.total_questions == 100
        assert t100.canvas_width == 1654
        assert t100.canvas_height == 2339
        assert t100.validate_bounds() is True
        assert t100.get_question(1) is not None
        assert t100.get_question(100) is not None

        t50 = TemplateConfig.load_from_json(template_50q_path)
        assert t50.total_questions == 50
        assert t50.canvas_width == 1654
        assert t50.canvas_height == 2339
        assert t50.validate_bounds() is True
        assert t50.get_question(1) is not None
        assert t50.get_question(50) is not None

    def test_setup_template_generator(self, tmp_path: Path):
        """Step 4.3: Verify calibration and scriptable template generation."""
        from src.setup_template import detect_grid_and_calibrate, generate_template_from_geometry

        # 1. Procedural generation from geometry
        t_custom = generate_template_from_geometry(
            cols=2,
            q_per_col=20,
            options=["A", "B", "C", "D", "E"],
            name="Custom_40Q_5Opt",
        )
        assert t_custom.total_questions == 40
        assert len(t_custom.get_question(1).options_map) == 5
        assert "E" in t_custom.get_question(1).options_map
        assert t_custom.validate_bounds() is True

        # 2. Calibration tool with image input
        blank_img_path = Path("data/blank_templates/blank_100q.jpg")
        out_json = tmp_path / "calibrated_100q.json"
        
        calibrated_t = detect_grid_and_calibrate(
            image_input=blank_img_path if blank_img_path.exists() else None,
            cols=4,
            q_per_col=25,
            output_path=out_json,
            name="Calibrated_100Q",
        )

        assert out_json.exists()
        assert calibrated_t.total_questions == 100
        assert calibrated_t.validate_bounds() is True

        # Load back from disk
        loaded = TemplateConfig.load_from_json(out_json)
        assert loaded.name == "Calibrated_100Q"
        assert loaded.total_questions == 100


def test_template_schema_validation(tmp_path: Path):
    """Standalone test entrypoint matching PROJECT.md Step 4.1 command."""
    TestTemplateModels().test_template_schema_validation(tmp_path)


def test_setup_template_generator(tmp_path: Path):
    """Standalone test entrypoint matching PROJECT.md Step 4.3 command."""
    TestTemplateModels().test_setup_template_generator(tmp_path)


def test_validate_template_coordinates():
    """Standalone test entrypoint matching PROJECT.md Step 4.4 command."""
    TestTemplateModels().test_validate_template_coordinates()



