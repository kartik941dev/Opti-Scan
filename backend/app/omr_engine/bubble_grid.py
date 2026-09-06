"""
OMR Layout Template Manager & Coordinate Grid Mapper.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


def create_standard_100q_grid(
    canvas_w: int = 1654,
    canvas_h: int = 2339,
) -> Dict[str, Any]:
    """
    Construct canonical 100-question coordinate grid specification (4 columns x 25 questions).
    Matches the standard A4 200 DPI layout.
    """
    # 1. Student ID Grid (6 columns x 10 digits centered at top)
    id_grid = {}
    roll_xs = [694, 748, 800, 852, 906, 958]
    roll_ys = [366, 402, 436, 472, 506, 542, 576, 612, 646, 682]

    for col, cx in enumerate(roll_xs):
        for digit, cy in enumerate(roll_ys):
            id_grid[f"col_{col}_digit_{digit}"] = {
                "cx": cx,
                "cy": cy,
                "r": 14,
                "col": col,
                "digit": digit,
            }

    # 2. 4 Columns x 25 Questions
    col_opt_a = [178.0, 544.0, 910.0, 1276.0]
    opt_step = 48.0
    row_start_y = 864.0
    row_step_y = 55.1667
    sections = ["Section A (Physics)", "Section B (Chemistry)", "Section C (Mathematics)", "Section D (Biology)"]
    options = ["A", "B", "C", "D"]

    questions = []
    q_num = 1
    for col_idx, opt_a_x in enumerate(col_opt_a):
        sec_name = sections[col_idx]
        for row in range(25):
            cy = int(round(row_start_y + row * row_step_y))
            q_bubbles = {}
            for opt_idx, opt in enumerate(options):
                cx = int(round(opt_a_x + opt_idx * opt_step))
                q_bubbles[opt] = {
                    "cx": cx,
                    "cy": cy,
                    "r": 14,
                }
            questions.append({
                "q_num": q_num,
                "section": sec_name,
                "options": q_bubbles,
            })
            q_num += 1

    return {
        "name": "OptiScan_Standard_100Q",
        "canvas_width": canvas_w,
        "canvas_height": canvas_h,
        "dpi": 200,
        "total_questions": 100,
        "fiducial_markers": [
            {"corner": "TL", "cx": 60, "cy": 51, "size": 42},
            {"corner": "TR", "cx": 1594, "cy": 51, "size": 42},
            {"corner": "BR", "cx": 1594, "cy": 2235, "size": 42},
            {"corner": "BL", "cx": 60, "cy": 2235, "size": 42},
        ],
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
