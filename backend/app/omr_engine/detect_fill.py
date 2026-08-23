"""
Pure Computer Vision Bubble Fill Detection Engine.
"""

from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np


def extract_bubble_roi(
    image: np.ndarray,
    cx: int,
    cy: int,
    radius: int,
    padding: int = 4,
) -> np.ndarray:
    """
    Crop square region of interest (ROI) centered at (cx, cy) with radius + padding.
    """
    h, w = image.shape[:2]
    x1 = max(0, cx - radius - padding)
    y1 = max(0, cy - radius - padding)
    x2 = min(w, cx + radius + padding + 1)
    y2 = min(h, cy + radius + padding + 1)
    return image[y1:y2, x1:x2]


def compute_fill_density(
    binary_roi: np.ndarray,
    radius: int,
    erosion_margin: int = 2,
) -> float:
    """
    Compute ink fill density using circular inner-erosion mask to ignore outer printed ring.
    """
    if binary_roi.size == 0:
        return 0.0

    rh, rw = binary_roi.shape[:2]
    mask = np.zeros((rh, rw), dtype=np.uint8)
    inner_r = max(2, radius - erosion_margin)

    # Draw solid white circle at center of mask
    cv2.circle(mask, (rw // 2, rh // 2), inner_r, 255, -1)
    mask_pixels = cv2.countNonZero(mask)
    if mask_pixels == 0:
        return 0.0

    # Count white ink pixels inside inner circle
    ink_in_mask = cv2.countNonZero(cv2.bitwise_and(binary_roi, mask))
    return float(ink_in_mask) / float(mask_pixels)


def calibrate_threshold(densities: List[float], default_thresh: float = 0.40) -> float:
    """
    Dynamically calibrate fill threshold based on sheet-wide bubble density distribution.
    """
    if not densities:
        return default_thresh

    arr = np.array(densities, dtype=np.float32)
    # Check if we have two distinct clusters
    low_vals = arr[arr < 0.30]
    high_vals = arr[arr >= 0.30]

    if len(high_vals) > 0 and len(low_vals) > 0:
        low_p90 = np.percentile(low_vals, 90)
        high_p10 = np.percentile(high_vals, 10)
        if high_p10 > low_p90:
            return float((low_p90 + high_p10) / 2.0)

    # Fallback to Otsu thresholding
    arr_uint8 = np.clip(arr * 255.0, 0, 255).astype(np.uint8)
    otsu_val, _ = cv2.threshold(arr_uint8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    calib = float(otsu_val) / 255.0

    return max(0.25, min(0.60, calib))


def classify_question_bubbles(
    option_densities: Dict[str, float],
    threshold: float,
    multi_mark_tolerance: float = 0.12,
) -> Tuple[Optional[str], float, str]:
    """
    Classify student choice from option fill densities.

    Returns:
        tuple of (selected_option, confidence, status)
        status: 'SINGLE_MARK', 'BLANK', 'MULTIPLE_MARKED', 'FAINT_MARK'
    """
    sorted_opts = sorted(option_densities.items(), key=lambda x: x[1], reverse=True)
    top_opt, top_density = sorted_opts[0]
    second_opt, second_density = sorted_opts[1]

    # Case 1: Unattempted / Blank
    if top_density < 0.20 and top_density < threshold * 0.70:
        return None, 1.0 - top_density, "BLANK"

    # Case 2: Ambiguous Multiple Marks
    if second_density >= threshold * 0.85 and (top_density - second_density) < multi_mark_tolerance:
        return f"{top_opt}+{second_opt}", 0.5, "MULTIPLE_MARKED"

    # Case 3: Faint Mark
    if top_density < threshold and top_density >= 0.22 and (top_density - second_density) > 0.15:
        return top_opt, float(top_density / threshold), "FAINT_MARK"

    # Case 4: Single Mark above threshold
    if top_density >= threshold:
        separation = top_density - second_density
        confidence = min(1.0, max(0.6, separation * 1.5))
        return top_opt, float(confidence), "SINGLE_MARK"

    return None, 0.7, "BLANK"


def extract_all_bubbles_and_fills(
    warped_binary: np.ndarray,
    template_config: Dict[str, Any],
) -> Tuple[Dict[int, Dict[str, Any]], Dict[str, Dict[str, Any]], float]:
    """
    Extract fill densities and classify all questions and student ID grid on warped binary sheet.
    """
    q_layout = template_config.get("questions_layout", [])
    id_grid = template_config.get("student_id_grid", {})

    all_densities = []
    question_densities = {}

    # 1. Collect all fill densities across questions
    for q in q_layout:
        q_num = q["q_num"]
        q_opts = q["options"]
        opt_map = {}
        for opt_key, bubble_coord in q_opts.items():
            cx = int(bubble_coord["cx"])
            cy = int(bubble_coord["cy"])
            r = int(bubble_coord["r"])

            roi = extract_bubble_roi(warped_binary, cx, cy, r)
            density = compute_fill_density(roi, r)
            opt_map[opt_key] = density
            all_densities.append(density)

        question_densities[q_num] = opt_map

    # 2. Calibrate threshold for this specific sheet
    thresh = calibrate_threshold(all_densities)

    # 3. Classify each question
    question_results = {}
    for q_num, opt_map in question_densities.items():
        choice, conf, status = classify_question_bubbles(opt_map, thresh)
        question_results[q_num] = {
            "selected_option": choice,
            "confidence": conf,
            "status": status,
            "densities": opt_map,
        }

    # 4. Extract Student ID grid
    student_id_results = {}
    if id_grid:
        for key, coord in id_grid.items():
            cx = int(coord["cx"])
            cy = int(coord["cy"])
            r = int(coord["r"])
            roi = extract_bubble_roi(warped_binary, cx, cy, r)
            student_id_results[key] = {
                "col": coord["col"],
                "digit": coord["digit"],
                "density": compute_fill_density(roi, r),
                "cx": cx,
                "cy": cy,
            }

    return question_results, student_id_results, thresh
