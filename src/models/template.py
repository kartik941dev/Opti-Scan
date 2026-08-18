"""
Pydantic data models for OMR templates, bubble coordinates, question layouts, and student ID grids.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.utils.exceptions import TemplateError, TemplateMismatchError
from src.utils.logger import get_logger

logger = get_logger("models.template")


class BubbleCoord(BaseModel):
    """
    Coordinates and bounding properties for a single circular bubble on the canonical canvas.
    """
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    cx: int = Field(..., ge=0, description="X coordinate of the bubble center in pixels")
    cy: int = Field(..., ge=0, description="Y coordinate of the bubble center in pixels")
    r: int = Field(default=13, gt=0, alias="radius", description="Radius of the bubble in pixels")

    @property
    def radius(self) -> int:
        return self.r

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        """Return (x, y, width, height) bounding box of the circular bubble."""
        return (self.cx - self.r, self.cy - self.r, 2 * self.r, 2 * self.r)

    def is_within_bounds(self, canvas_w: int, canvas_h: int) -> bool:
        """Check whether the entire bubble circle fits within the canvas boundaries."""
        return (
            self.cx - self.r >= 0
            and self.cy - self.r >= 0
            and self.cx + self.r <= canvas_w
            and self.cy + self.r <= canvas_h
        )


class StudentIDBubble(BaseModel):
    """
    Represents a single digit bubble inside the student ID matrix grid.
    """
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    cx: int = Field(..., ge=0)
    cy: int = Field(..., ge=0)
    r: int = Field(default=11, gt=0, alias="radius")
    digit: int = Field(..., ge=0, le=9)
    col: int = Field(..., ge=0)


class QuestionLayout(BaseModel):
    """
    Layout and coordinate mapping for a single multiple-choice question.
    """
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    q_num: int = Field(..., ge=1, alias="question_number", description="1-indexed question identifier")
    section: str = Field(default="General", description="Section or subject name (e.g. Physics, Math)")
    options_map: dict[str, BubbleCoord] = Field(
        default_factory=dict,
        alias="bubbles",
        description="Map of option label (e.g. 'A', 'B', 'C', 'D') to BubbleCoord",
    )

    @field_validator("options_map", mode="before")
    @classmethod
    def parse_options_map(cls, value: Any) -> dict[str, BubbleCoord]:
        if not isinstance(value, dict):
            raise ValueError(f"options_map must be a dictionary, got {type(value).__name__}")
        parsed = {}
        for opt_key, opt_val in value.items():
            if isinstance(opt_val, BubbleCoord):
                parsed[str(opt_key)] = opt_val
            elif isinstance(opt_val, dict):
                parsed[str(opt_key)] = BubbleCoord(**opt_val)
            else:
                raise ValueError(f"Invalid bubble coordinate data for option {opt_key}: {opt_val}")
        return parsed

    @property
    def question_number(self) -> int:
        return self.q_num

    @property
    def bubbles(self) -> dict[str, BubbleCoord]:
        return self.options_map

    def get_bubble(self, option: str) -> BubbleCoord:
        opt_upper = str(option).upper()
        if opt_upper not in self.options_map:
            raise KeyError(f"Option '{option}' not found in question {self.q_num}. Available: {list(self.options_map.keys())}")
        return self.options_map[opt_upper]


class TemplateConfig(BaseModel):
    """
    Master template configuration schema defining the geometry and questions grid
    for standardized OMR sheets.
    """
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    name: str = Field(default="OptiScan_A4_Standard", description="Human-readable template name")
    canvas_w: int = Field(default=1654, gt=0, alias="canvas_width", description="Canonical canvas width in pixels")
    canvas_h: int = Field(default=2339, gt=0, alias="canvas_height", description="Canonical canvas height in pixels")
    dpi: int = Field(default=200, gt=0, description="DPI calibration of the canonical canvas")
    questions: list[QuestionLayout] = Field(
        default_factory=list,
        alias="questions_layout",
        description="Ordered list of question layout definitions",
    )
    student_id_grid: Optional[dict[str, Any]] = Field(
        default_factory=dict,
        alias="id_grid_layout",
        description="Student ID grid layout coordinates",
    )

    @field_validator("questions", mode="before")
    @classmethod
    def parse_questions_list(cls, value: Any) -> list[QuestionLayout]:
        if not isinstance(value, list):
            raise ValueError(f"questions must be a list, got {type(value).__name__}")
        parsed = []
        for item in value:
            if isinstance(item, QuestionLayout):
                parsed.append(item)
            elif isinstance(item, dict):
                parsed.append(QuestionLayout(**item))
            else:
                raise ValueError(f"Invalid question layout element: {item}")
        return parsed

    @property
    def total_questions(self) -> int:
        return len(self.questions)

    @property
    def canvas_width(self) -> int:
        return self.canvas_w

    @property
    def canvas_height(self) -> int:
        return self.canvas_h

    def get_question(self, q_num: int) -> Optional[QuestionLayout]:
        """Lookup QuestionLayout by question number."""
        for q in self.questions:
            if q.q_num == q_num:
                return q
        return None

    def validate_bounds(self, canvas_w: Optional[int] = None, canvas_h: Optional[int] = None) -> bool:
        """
        Verify that all question bubbles and student ID grid elements reside strictly within canvas dimensions.
        """
        w = canvas_w or self.canvas_w
        h = canvas_h or self.canvas_h

        for q in self.questions:
            for opt_key, bubble in q.options_map.items():
                if not bubble.is_within_bounds(w, h):
                    raise TemplateError(
                        f"Bubble '{opt_key}' in Question {q.q_num} exceeds canvas bounds ({w}x{h}): ({bubble.cx}, {bubble.cy}, r={bubble.r})",
                        details={"question": q.q_num, "option": opt_key, "cx": bubble.cx, "cy": bubble.cy, "r": bubble.r, "canvas_w": w, "canvas_h": h},
                    )

        if isinstance(self.student_id_grid, dict):
            for k, b_data in self.student_id_grid.items():
                if isinstance(b_data, dict) and "cx" in b_data and "cy" in b_data:
                    cx = b_data["cx"]
                    cy = b_data["cy"]
                    r = b_data.get("radius", b_data.get("r", 11))
                    if cx - r < 0 or cy - r < 0 or cx + r > w or cy + r > h:
                        raise TemplateError(
                            f"Student ID bubble '{k}' exceeds canvas bounds ({w}x{h}): ({cx}, {cy}, r={r})",
                            details={"key": k, "cx": cx, "cy": cy, "r": r, "canvas_w": w, "canvas_h": h},
                        )

        return True

    def save_to_json(self, output_path: Union[str, Path]) -> None:
        """Serialize template configuration to a JSON file."""
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2, by_alias=True))
        logger.info("Saved template '%s' with %d questions to %s", self.name, len(self.questions), out_p)

    @classmethod
    def load_from_json(cls, file_path: Union[str, Path]) -> "TemplateConfig":
        """Load and parse template configuration from a JSON file."""
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            raise TemplateError(f"Template JSON file does not exist: {path}", details={"file_path": str(path)})
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Handle format differences (e.g. top-level canvas_dimensions dict)
            if "canvas_dimensions" in data and isinstance(data["canvas_dimensions"], dict):
                dims = data["canvas_dimensions"]
                data["canvas_w"] = dims.get("width", 1654)
                data["canvas_h"] = dims.get("height", 2339)
                data["dpi"] = dims.get("dpi", 200)

            template = cls(**data)
            template.validate_bounds()
            return template
        except Exception as e:
            if isinstance(e, TemplateError):
                raise
            raise TemplateError(f"Failed to parse template from '{path}': {e}", details={"error": str(e)}) from e


def validate_template_coordinates(template: TemplateConfig, canvas_shape: tuple[int, int]) -> bool:
    """
    Validate that all coordinates defined in a template fit inside the given canvas shape (height, width).
    """
    h, w = canvas_shape[:2]
    return template.validate_bounds(canvas_w=w, canvas_h=h)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OptiScan Template Configuration Validator CLI")
    parser.add_argument("--validate", type=str, required=True, help="Path to template JSON file to validate")
    args = parser.parse_args()

    try:
        t = TemplateConfig.load_from_json(args.validate)
        print(f"[SUCCESS] Template '{t.name}' is valid. Total questions: {len(t.questions)}, Canvas: {t.canvas_w}x{t.canvas_h} @ {t.dpi} DPI.")
    except Exception as exc:
        print(f"[ERROR] Template validation failed: {exc}")
        exit(1)
