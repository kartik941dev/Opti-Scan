"""
OMR Layout Template Manager & Coordinate Grid Mapper.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


def create_standard_100q_grid(
    canvas_w: int = 1654,
    canvas_h: int = 2339,
    col_x_starts: Optional[List[int]] = None,
    grid_y_start: int = 650,
    q_y_step: int = 62,
    opt_x_step: int = 44,
    bubble_radius: int = 13,
) -> Dict[str, Any]:
    """
    Construct canonical 100-question coordinate grid specification (4 columns x 25 questions).
    """
    if col_x_starts is None:
        col_x_starts = [120, 500, 880, 1260]

    options = ["A", "B", "C", "D"]
    section_names = ["Section A (Physics)", "Section B (Chemistry)", "Section C (Mathematics)", "Section D (Biology)"]

    questions = []
    q_num = 1

    for col_idx, col_x in enumerate(col_x_starts):
        sec_name = section_names[col_idx] if col_idx < len(section_names) else f"Section {col_idx + 1}"
        for row_idx in range(25):
            q_y = grid_y_start + row_idx * q_y_step
            q_bubbles = {}
            for opt_idx, opt in enumerate(options):
                opt_x = col_x + 60 + opt_idx * opt_x_step
                q_bubbles[opt] = {
                    "cx": opt_x,
                    "cy": q_y,
                    "r": bubble_radius,
                }
            questions.append({
                "q_num": q_num,
                "section": sec_name,
                "options": q_bubbles,
            })
            q_num += 1

    # Student ID Grid (6 columns of 0-9 digits)
    id_origin_x = 200
    id_origin_y = 250
    id_dx = 38
    id_dy = 30
    id_radius = 11

    id_grid = {}
    for col in range(6):
        col_x = id_origin_x + col * id_dx
        for digit in range(10):
            row_y = id_origin_y + 35 + digit * id_dy
            id_grid[f"col_{col}_digit_{digit}"] = {
                "cx": col_x,
                "cy": row_y,
                "r": id_radius,
                "col": col,
                "digit": digit,
            }

    return {
        "name": "OptiScan_Standard_100Q",
        "canvas_width": canvas_w,
        "canvas_height": canvas_h,
        "dpi": 200,
        "total_questions": 100,
        "questions_layout": questions,
        "student_id_grid": id_grid,
    }


def load_template_config(template_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """
    Load layout template JSON or return standard 100Q grid if not found.
    """
    if template_path:
        p = Path(template_path)
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)

    # Check default location
    default_p = Path(__file__).resolve().parent.parent.parent / "templates" / "omr_template.json"
    if default_p.exists():
        with open(default_p, "r", encoding="utf-8") as f:
            return json.load(f)

    return create_standard_100q_grid()
