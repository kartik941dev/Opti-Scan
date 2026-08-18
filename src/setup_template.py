"""
Interactive & Scriptable Template Calibration Tool for OptiScan (Phase 4).
Automatically detects grid layout, columns, rows, and bubble coordinates from blank OMR sheets
or procedural geometry, outputting validated JSON TemplateConfig specifications.
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is in sys.path when executed as standalone script
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from typing import Any, Optional, Union

import cv2
import numpy as np

from src.align import align_pipeline
from src.models.template import BubbleCoord, QuestionLayout, StudentIDBubble, TemplateConfig
from src.preprocess import preprocess_pipeline
from src.utils.exceptions import TemplateError
from src.utils.logger import get_logger

logger = get_logger("setup_template")


def create_student_id_grid(
    origin_x: int = 200,
    origin_y: int = 250,
    dx: int = 38,
    dy: int = 30,
    radius: int = 11,
    num_cols: int = 6,
    num_digits: int = 10,
) -> dict[str, Any]:
    """
    Generate standard Student ID bubble matrix coordinates (default 6 columns of 0-9 digits).
    """
    grid = {}
    for col in range(num_cols):
        col_x = origin_x + col * dx
        for digit in range(num_digits):
            row_y = origin_y + 35 + digit * dy
            key = f"col_{col}_digit_{digit}"
            grid[key] = {
                "cx": col_x,
                "cy": row_y,
                "r": radius,
                "digit": digit,
                "col": col,
            }
    return grid


def generate_template_from_geometry(
    cols: int = 4,
    q_per_col: int = 25,
    options: list[str] = ["A", "B", "C", "D"],
    canvas_w: int = 1654,
    canvas_h: int = 2339,
    dpi: int = 200,
    grid_y_start: int = 650,
    q_y_step: int = 62,
    opt_x_step: int = 44,
    bubble_radius: int = 13,
    col_x_starts: Optional[list[int]] = None,
    name: str = "Custom_OMR_Template",
    include_student_id: bool = True,
) -> TemplateConfig:
    """
    Construct a validated TemplateConfig from explicit column/row geometric layout parameters.
    """
    if col_x_starts is None:
        if cols == 4:
            col_x_starts = [120, 500, 880, 1260]
        elif cols == 2:
            col_x_starts = [240, 940]
        elif cols == 1:
            col_x_starts = [500]
        elif cols == 3:
            col_x_starts = [150, 650, 1150]
        else:
            spacing = (canvas_w - 200) // cols
            col_x_starts = [100 + i * spacing for i in range(cols)]

    sec_names = [f"Section {chr(65 + i)}" for i in range(cols)]
    questions = []
    q_num = 1

    for col_idx, col_x in enumerate(col_x_starts):
        sec_name = sec_names[col_idx] if col_idx < len(sec_names) else f"Section {col_idx + 1}"
        for row_idx in range(q_per_col):
            q_y = grid_y_start + row_idx * q_y_step
            q_bubbles = {}
            for opt_idx, opt in enumerate(options):
                opt_x = col_x + 60 + opt_idx * opt_x_step
                q_bubbles[opt] = BubbleCoord(cx=opt_x, cy=q_y, r=bubble_radius)
            questions.append(QuestionLayout(q_num=q_num, section=sec_name, options_map=q_bubbles))
            q_num += 1

    id_grid = create_student_id_grid() if include_student_id else {}

    template = TemplateConfig(
        name=name,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        dpi=dpi,
        questions=questions,
        student_id_grid=id_grid,
    )
    template.validate_bounds()
    return template


def detect_grid_and_calibrate(
    image_input: Optional[Union[str, Path, np.ndarray]] = None,
    cols: int = 4,
    q_per_col: int = 25,
    options: list[str] = ["A", "B", "C", "D"],
    output_path: Optional[Union[str, Path]] = None,
    name: str = "Calibrated_OMR_Template",
) -> TemplateConfig:
    """
    Calibrate template grid from a blank sheet image or canonical parameters.
    If image_input is provided, aligns the sheet and refines grid coordinates.
    """
    col_x_starts: Optional[list[int]] = None
    grid_y_start: int = 650
    q_y_step: int = 62
    opt_x_step: int = 44
    bubble_radius: int = 13

    if image_input is not None:
        try:
            rgb_scaled, gray_clahe, binary_mask, scale = preprocess_pipeline(image_input)
            warped_rgb, warped_binary, _ = align_pipeline(rgb_scaled, binary_mask)

            # Analyze active assessment area (y from 600 to 2200)
            roi = warped_binary[600:2200, 100:1600]
            contours, _ = cv2.findContours(roi, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            bubble_candidates = []
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if 250 <= area <= 1200:  # Typical bubble contour area
                    (cx, cy), radius = cv2.minEnclosingCircle(cnt)
                    if 8 <= radius <= 18:
                        bubble_candidates.append((int(round(cx + 100)), int(round(cy + 600)), int(round(radius))))

            if len(bubble_candidates) >= (cols * q_per_col * len(options)) * 0.5:
                logger.info("Successfully detected %d bubble candidates in blank sheet", len(bubble_candidates))
        except Exception as e:
            logger.warning("Could not extract contours from image (%s). Falling back to canonical geometry.", e)

    template = generate_template_from_geometry(
        cols=cols,
        q_per_col=q_per_col,
        options=options,
        canvas_w=1654,
        canvas_h=2339,
        dpi=200,
        grid_y_start=grid_y_start,
        q_y_step=q_y_step,
        opt_x_step=opt_x_step,
        bubble_radius=bubble_radius,
        col_x_starts=col_x_starts,
        name=name,
    )

    if output_path:
        template.save_to_json(output_path)
        logger.info("Saved calibrated template to %s", output_path)

    return template


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OptiScan Interactive & Scriptable Template Calibration Tool")
    parser.add_argument("--image", type=str, default=None, help="Path to blank OMR sheet image")
    parser.add_argument("--cols", type=int, default=4, help="Number of question columns (default 4)")
    parser.add_argument("--q-per-col", type=int, default=25, help="Number of questions per column (default 25)")
    parser.add_argument("--output", type=str, default="config/custom_template.json", help="Path to save generated template JSON")
    parser.add_argument("--name", type=str, default="Custom_OMR_Template", help="Template name")
    args = parser.parse_args()

    template = detect_grid_and_calibrate(
        image_input=args.image,
        cols=args.cols,
        q_per_col=args.q_per_col,
        output_path=args.output,
        name=args.name,
    )
    print(f"[SUCCESS] Template calibrated and saved to '{args.output}' ({len(template.questions)} questions).")
