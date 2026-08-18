"""
Synthetic OMR Sheet Generator for testing and calibration.
Generates realistic A4 OMR sheets with known ground-truth answers,
student IDs, fiducial corner markers, and configurable distortions.
"""

import argparse
import json
import random
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np


def generate_synthetic_omr_sheet(
    num_questions: int = 100,
    filled_answers: Optional[dict[int, str]] = None,
    student_id: str = "202641",
    noise_level: float = 0.0,
    rotation_deg: float = 0.0,
    shadow_intensity: float = 0.0,
    output_path: Optional[str | Path] = None,
    ground_truth_path: Optional[str | Path] = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """
    Generate a synthetic A4 OMR sheet image and ground-truth metadata.

    Args:
        num_questions: Total questions (default 100, organized in 4 columns of 25).
        filled_answers: Mapping of question number (1-indexed) to chosen option ('A', 'B', 'C', 'D').
                        If None, random answers are assigned.
        student_id: 6-digit student ID string (e.g. "202641").
        noise_level: Std deviation of Gaussian noise (0.0 to 50.0).
        rotation_deg: Rotation angle in degrees (-45.0 to +45.0).
        shadow_intensity: Gradient shadow strength (0.0 to 1.0).
        output_path: Optional file path to save the generated image.
        ground_truth_path: Optional file path to save the ground-truth JSON metadata.

    Returns:
        tuple of (image_np_array, ground_truth_dict)
    """
    # Canonical A4 canvas @ 200 DPI: Width=1654, Height=2339
    canvas_w = 1654
    canvas_h = 2339
    img = np.full((canvas_h, canvas_w, 3), 255, dtype=np.uint8)

    # 1. Draw 4 Solid Fiducial Corner Markers (60x60 black squares)
    marker_size = 60
    markers = {
        "top_left": {"x": 80, "y": 80, "w": marker_size, "h": marker_size},
        "top_right": {"x": canvas_w - 80 - marker_size, "y": 80, "w": marker_size, "h": marker_size},
        "bottom_right": {"x": canvas_w - 80 - marker_size, "y": canvas_h - 80 - marker_size, "w": marker_size, "h": marker_size},
        "bottom_left": {"x": 80, "y": canvas_h - 80 - marker_size, "w": marker_size, "h": marker_size},
    }

    for m in markers.values():
        cv2.rectangle(img, (m["x"], m["y"]), (m["x"] + m["w"], m["y"] + m["h"]), (0, 0, 0), -1)

    # 2. Draw Header & Title
    cv2.putText(img, "OPTISCAN EVALUATION SHEET", (380, 120), cv2.FONT_HERSHEY_DUPLEX, 1.3, (0, 0, 0), 3)
    cv2.putText(img, "Standard A4 OMR Assessment Format - 100 Questions", (450, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (80, 80, 80), 2)
    cv2.line(img, (180, 185), (canvas_w - 180, 185), (0, 0, 0), 2)

    # 3. Draw Student ID Grid (6 Digits: Columns for 0-9)
    id_origin_x = 200
    id_origin_y = 250
    id_dx = 38
    id_dy = 30
    id_bubble_radius = 11

    cv2.putText(img, "STUDENT ROLL NO / ID:", (id_origin_x, id_origin_y - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    
    # Ensure student_id is 6 digits
    clean_id = str(student_id).zfill(6)[:6]
    id_grid_coords = {}

    for col_idx in range(6):
        col_x = id_origin_x + col_idx * id_dx
        # Header box with digit text
        cv2.rectangle(img, (col_x - 14, id_origin_y - 18), (col_x + 14, id_origin_y + 8), (0, 0, 0), 1)
        target_digit = int(clean_id[col_idx])
        cv2.putText(img, clean_id[col_idx], (col_x - 6, id_origin_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

        for digit in range(10):
            row_y = id_origin_y + 35 + digit * id_dy
            key = f"col_{col_idx}_digit_{digit}"
            id_grid_coords[key] = {"cx": col_x, "cy": row_y, "digit": digit, "col": col_idx}
            # Draw unfilled bubble
            cv2.circle(img, (col_x, row_y), id_bubble_radius, (0, 0, 0), 2)
            cv2.putText(img, str(digit), (col_x - 4, row_y + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)
            # Fill if matches student ID digit
            if digit == target_digit:
                cv2.circle(img, (col_x, row_y), id_bubble_radius - 1, (0, 0, 0), -1)

    # Draw Instructions Box
    instr_x = 600
    instr_y = 230
    cv2.rectangle(img, (instr_x, instr_y), (canvas_w - 200, instr_y + 340), (0, 0, 0), 1)
    cv2.putText(img, "EXAM INSTRUCTIONS & MARKING RULES:", (instr_x + 20, instr_y + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    instructions = [
        "1. Use Black/Blue ballpoint pen or 2B pencil only.",
        "2. Darken completely inside the bubble circle.",
        "3. Do not make stray marks outside the bubble area.",
        "4. Multiple marks on a single question will be flagged.",
        "5. Correct: (+4.0)  |  Incorrect: (-1.0)  |  Blank: (0.0)",
    ]
    for i, line in enumerate(instructions):
        cv2.putText(img, line, (instr_x + 20, instr_y + 75 + i * 35), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (50, 50, 50), 1)

    # 4. Draw Question Grids (4 Columns of 25 Questions)
    options = ["A", "B", "C", "D"]
    col_x_starts = [120, 500, 880, 1260]
    grid_y_start = 650
    q_y_step = 62
    opt_x_step = 44
    bubble_radius = 13

    if filled_answers is None:
        # Default random ground-truth generation
        random.seed(42)
        filled_answers = {q: random.choice(["A", "B", "C", "D", None]) for q in range(1, num_questions + 1)}

    question_coords = []
    ground_truth_answers = {}

    q_num = 1
    for col_idx, col_x in enumerate(col_x_starts):
        # Section Header
        sec_name = ["SECTION A (Physics)", "SECTION B (Chemistry)", "SECTION C (Mathematics)", "SECTION D (Biology)"][col_idx]
        cv2.putText(img, sec_name, (col_x, grid_y_start - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)
        cv2.line(img, (col_x, grid_y_start - 25), (col_x + 300, grid_y_start - 25), (0, 0, 0), 1)

        for row_idx in range(25):
            if q_num > num_questions:
                break

            q_y = grid_y_start + row_idx * q_y_step
            # Draw Question Number
            q_str = f"{q_num:02d}." if q_num < 100 else f"{q_num}."
            cv2.putText(img, q_str, (col_x, q_y + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)

            chosen_opt = filled_answers.get(q_num)
            ground_truth_answers[str(q_num)] = chosen_opt
            q_bubbles = {}

            for opt_idx, opt in enumerate(options):
                opt_x = col_x + 60 + opt_idx * opt_x_step
                q_bubbles[opt] = {"cx": opt_x, "cy": q_y, "radius": bubble_radius}

                # Draw outer circular outline
                cv2.circle(img, (opt_x, q_y), bubble_radius, (0, 0, 0), 2)
                cv2.putText(img, opt, (opt_x - 5, q_y + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 100, 100), 1)

                # Fill bubble if chosen
                if chosen_opt == opt:
                    # Solid dark fill
                    cv2.circle(img, (opt_x, q_y), bubble_radius - 1, (10, 10, 10), -1)

            question_coords.append({
                "question_number": q_num,
                "section": sec_name,
                "bubbles": q_bubbles,
            })
            q_num += 1

    # 5. Apply Perturbations (Shadows, Rotation, Noise)
    if shadow_intensity > 0.0:
        # Create subtle diagonal gradient shadow
        y_indices, x_indices = np.indices((canvas_h, canvas_w))
        gradient = (x_indices / canvas_w + y_indices / canvas_h) / 2.0
        shadow_map = 1.0 - (gradient * shadow_intensity * 0.4)
        shadow_map = np.clip(shadow_map, 0.4, 1.0)[:, :, np.newaxis]
        img = np.clip(img.astype(np.float32) * shadow_map, 0, 255).astype(np.uint8)

    if noise_level > 0.0:
        gaussian_noise = np.random.normal(0, noise_level, img.shape).astype(np.float32)
        img = np.clip(img.astype(np.float32) + gaussian_noise, 0, 255).astype(np.uint8)

    if abs(rotation_deg) > 0.001:
        center = (canvas_w // 2, canvas_h // 2)
        rot_mat = cv2.getRotationMatrix2D(center, rotation_deg, 1.0)
        img = cv2.warpAffine(img, rot_mat, (canvas_w, canvas_h), borderMode=cv2.BORDER_CONSTANT, borderValue=(240, 240, 240))

    # 6. Assemble Ground Truth Metadata
    metadata = {
        "format": "OptiScan_A4_100Q",
        "canvas_dimensions": {"width": canvas_w, "height": canvas_h, "dpi": 200},
        "student_id": clean_id,
        "fiducial_markers": markers,
        "total_questions": num_questions,
        "ground_truth_answers": ground_truth_answers,
        "questions_layout": question_coords,
        "id_grid_layout": id_grid_coords,
        "distortions": {
            "noise_level": noise_level,
            "rotation_deg": rotation_deg,
            "shadow_intensity": shadow_intensity,
        },
    }

    # 7. Save to disk if paths provided
    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out_p), img)

    if ground_truth_path:
        gt_p = Path(ground_truth_path)
        gt_p.parent.mkdir(parents=True, exist_ok=True)
        with open(gt_p, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

    return img, metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OptiScan Synthetic OMR Sheet Generator")
    parser.add_argument("--output", type=str, default="data/sample_sheets/mock_clean.png", help="Path to save output image")
    parser.add_argument("--metadata", type=str, default="data/sample_sheets/mock_clean_metadata.json", help="Path to save metadata JSON")
    parser.add_argument("--student-id", type=str, default="202641", help="6-digit student ID")
    parser.add_argument("--noise", type=float, default=0.0, help="Noise level std-dev (0-50)")
    parser.add_argument("--rotation", type=float, default=0.0, help="Rotation angle in degrees (-45 to 45)")
    parser.add_argument("--shadow", type=float, default=0.0, help="Shadow gradient intensity (0.0 to 1.0)")
    args = parser.parse_args()

    print(f"Generating synthetic OMR sheet: {args.output}...")
    img, meta = generate_synthetic_omr_sheet(
        output_path=args.output,
        ground_truth_path=args.metadata,
        student_id=args.student_id,
        noise_level=args.noise,
        rotation_deg=args.rotation,
        shadow_intensity=args.shadow,
    )
    print(f"Successfully generated {img.shape[1]}x{img.shape[0]} OMR sheet with {meta['total_questions']} questions.")
