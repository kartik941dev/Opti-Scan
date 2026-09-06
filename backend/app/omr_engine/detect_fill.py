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
    if image is None:
        return np.array([])
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


def compute_hybrid_fill_density(
    binary_roi: np.ndarray,
    gray_roi: Optional[np.ndarray],
    radius: int,
    erosion_margin: int = 3,
) -> float:
    """
    Compute robust fill density using both binary ink mask and grayscale darkness
    inside inner circular area to eliminate false positives from thick printed letters.
    """
    if binary_roi.size == 0:
        return 0.0

    rh, rw = binary_roi.shape[:2]
    mask = np.zeros((rh, rw), dtype=np.uint8)
    inner_r = max(2, radius - erosion_margin)

    cv2.circle(mask, (rw // 2, rh // 2), inner_r, 255, -1)
    mask_pixels = cv2.countNonZero(mask)
    if mask_pixels == 0:
        return 0.0

    ink_in_mask = cv2.countNonZero(cv2.bitwise_and(binary_roi, mask))
    bin_density = float(ink_in_mask) / float(mask_pixels)

    if gray_roi is not None and gray_roi.size > 0:
        mean_gray = cv2.mean(gray_roi, mask=mask)[0]
        gray_darkness = 1.0 - (mean_gray / 255.0)
        return float(0.4 * bin_density + 0.6 * gray_darkness)

    return bin_density


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
    multi_mark_tolerance: float = 0.10,
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
    warped_gray: Optional[np.ndarray] = None,
) -> Tuple[Dict[int, Dict[str, Any]], Dict[str, Dict[str, Any]], float]:
    """
    Extract fill densities and classify all questions and student ID grid on warped sheet.
    Incorporates dynamic grid offset detection and hybrid fill evaluation for robust
    performance across digital PDFs, mobile scans, and casual screenshots.
    """
    q_layout = template_config.get("questions_layout", [])
    id_grid = template_config.get("student_id_grid", {})

    r = 14
    ring_mask = np.zeros((2 * r + 1, 2 * r + 1), dtype=np.uint8)
    cv2.circle(ring_mask, (r, r), r, 255, 2)

    # 1. Detect dynamic Student ID grid vertical offset
    best_id_dy = 0
    if id_grid:
        max_id_score = -1
        for dy in range(-35, 36):
            score = 0
            for key, b in id_grid.items():
                cx = int(b["cx"])
                cy = int(b["cy"]) + dy
                patch = warped_binary[cy - r : cy + r + 1, cx - r : cx + r + 1]
                if patch.shape == ring_mask.shape:
                    score += cv2.countNonZero(cv2.bitwise_and(patch, ring_mask))
            if score > max_id_score:
                max_id_score = score
                best_id_dy = dy

    # 2. Detect section question row drift
    sections_q = []
    if len(q_layout) == 100:
        sections_q = [q_layout[0:25], q_layout[25:50], q_layout[50:75], q_layout[75:100]]
    elif q_layout:
        sections_q = [q_layout]

    question_row_dys = {}
    for s_qs in sections_q:
        row_best_dys = []
        for q in s_qs:
            best_dy = 0
            max_overlap = -1
            for dy in range(-15, 36):
                overlap = 0
                for opt, b in q["options"].items():
                    cx = int(b["cx"])
                    cy = int(b["cy"]) + dy
                    patch = warped_binary[cy - r : cy + r + 1, cx - r : cx + r + 1]
                    if patch.shape == ring_mask.shape:
                        overlap += cv2.countNonZero(cv2.bitwise_and(patch, ring_mask))
                if overlap > max_overlap:
                    max_overlap = overlap
                    best_dy = dy
            row_best_dys.append(best_dy)

        rows = np.arange(len(s_qs))
        poly = np.polyfit(rows, row_best_dys, 1)
        smoothed_dys = np.polyval(poly, rows)
        for row_idx, q in enumerate(s_qs):
            question_row_dys[q["q_num"]] = int(round(smoothed_dys[row_idx]))

    # 3. Extract fill densities across questions
    all_densities = []
    question_densities = {}
    question_coords = {}

    for q in q_layout:
        q_num = q["q_num"]
        q_opts = q["options"]
        row_dy = question_row_dys.get(q_num, 0)

        opt_map = {}
        coords_map = {}
        for opt_key, bubble_coord in q_opts.items():
            cx = int(bubble_coord["cx"])
            cy = int(bubble_coord["cy"]) + row_dy
            b_r = int(bubble_coord["r"])

            roi_bin = extract_bubble_roi(warped_binary, cx, cy, b_r)
            roi_gray = extract_bubble_roi(warped_gray, cx, cy, b_r) if warped_gray is not None else None
            density = compute_hybrid_fill_density(roi_bin, roi_gray, b_r)
            opt_map[opt_key] = density
            coords_map[opt_key] = {"cx": cx, "cy": cy, "r": b_r}
            all_densities.append(density)

        question_densities[q_num] = opt_map
        question_coords[q_num] = coords_map

    # 4. Calibrate threshold for this specific sheet
    thresh = calibrate_threshold(all_densities)

    # 5. Classify each question
    question_results = {}
    for q_num, opt_map in question_densities.items():
        choice, conf, status = classify_question_bubbles(opt_map, thresh, multi_mark_tolerance=0.10)
        question_results[q_num] = {
            "selected_option": choice,
            "confidence": conf,
            "status": status,
            "densities": opt_map,
            "bubble_coords": question_coords.get(q_num, {}),
        }

    # 6. Extract Student ID grid
    student_id_results = {}
    if id_grid:
        for key, coord in id_grid.items():
            cx = int(coord["cx"])
            cy = int(coord["cy"]) + best_id_dy
            b_r = int(coord["r"])
            roi_bin = extract_bubble_roi(warped_binary, cx, cy, b_r)
            roi_gray = extract_bubble_roi(warped_gray, cx, cy, b_r) if warped_gray is not None else None
            student_id_results[key] = {
                "col": coord["col"],
                "digit": coord["digit"],
                "density": compute_hybrid_fill_density(roi_bin, roi_gray, b_r),
                "cx": cx,
                "cy": cy,
            }

    return question_results, student_id_results, thresh
