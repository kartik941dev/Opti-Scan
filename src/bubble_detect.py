"""
Bubble Slicing, Masking, Fill Detection, and Option Classification Engine for OptiScan (Phase 5).
"""

from typing import Any, Optional, Union

import cv2
import numpy as np

from src.models.template import BubbleCoord, QuestionLayout, TemplateConfig
from src.utils.exceptions import BubbleDetectionError
from src.utils.logger import get_logger

logger = get_logger("bubble_detect")


def extract_bubble_roi(
    image: np.ndarray,
    cx: int,
    cy: int,
    radius: int,
) -> np.ndarray:
    """
    Extract a square region of interest (ROI) of size (2*radius x 2*radius)
    centered at (cx, cy) from an image canvas with boundary clipping.

    Args:
        image: 2D or 3D NumPy array representing the canvas.
        cx: Center X coordinate in pixels.
        cy: Center Y coordinate in pixels.
        radius: Radius of the circular bubble in pixels.

    Returns:
        Square NumPy array of shape (2*radius, 2*radius) or (2*radius, 2*radius, C).

    Raises:
        ValueError: If radius <= 0 or image is empty.
    """
    if radius <= 0:
        raise ValueError(f"Bubble radius must be positive, got {radius}")
    if image is None or image.size == 0:
        raise ValueError("Input image array is empty or None")

    h, w = image.shape[:2]
    box_size = 2 * radius

    # Ideal bounding box coordinates
    x_min = cx - radius
    x_max = cx + radius
    y_min = cy - radius
    y_max = cy + radius

    # If completely within bounds, fast slice
    if 0 <= x_min and x_max <= w and 0 <= y_min and y_max <= h:
        return image[y_min:y_max, x_min:x_max].copy()

    # Otherwise, handle boundary clipping by allocating a zero canvas and copying the valid overlap
    if image.ndim == 3:
        roi = np.zeros((box_size, box_size, image.shape[2]), dtype=image.dtype)
    else:
        roi = np.zeros((box_size, box_size), dtype=image.dtype)

    # Valid overlap in source image
    src_x_min = max(0, x_min)
    src_x_max = min(w, x_max)
    src_y_min = max(0, y_min)
    src_y_max = min(h, y_max)

    if src_x_min < src_x_max and src_y_min < src_y_max:
        # Corresponding region in destination ROI
        dst_x_min = src_x_min - x_min
        dst_x_max = dst_x_min + (src_x_max - src_x_min)
        dst_y_min = src_y_min - y_min
        dst_y_max = dst_y_min + (src_y_max - src_y_min)

        roi[dst_y_min:dst_y_max, dst_x_min:dst_x_max] = image[src_y_min:src_y_max, src_x_min:src_x_max]

    return roi


def generate_inner_circle_mask(
    roi_size: int,
    radius: int,
    erosion_pct: float = 0.20,
) -> np.ndarray:
    """
    Generate a centered circular binary mask with inner erosion.
    Excludes the outer perimeter of the bubble circle to prevent printed
    outline ink from counting towards the student fill metric.

    Args:
        roi_size: Square ROI dimension in pixels (width == height).
        radius: Original bubble radius in pixels.
        erosion_pct: Percentage (0.0 to 1.0) of radius to erode from outer boundary. Default 0.20 (20%).

    Returns:
        2D binary NumPy array of shape (roi_size, roi_size) with values in {0, 255}.

    Raises:
        ValueError: If roi_size <= 0, radius <= 0, or erosion_pct not in [0.0, 1.0).
    """
    if roi_size <= 0:
        raise ValueError(f"roi_size must be positive, got {roi_size}")
    if radius <= 0:
        raise ValueError(f"radius must be positive, got {radius}")
    if not (0.0 <= erosion_pct < 1.0):
        raise ValueError(f"erosion_pct must be in range [0.0, 1.0), got {erosion_pct}")

    mask = np.zeros((roi_size, roi_size), dtype=np.uint8)
    center = (roi_size // 2, roi_size // 2)

    # Compute inner eroded radius
    inner_radius = max(1, int(round(radius * (1.0 - erosion_pct))))

    # Draw solid white circle on black mask
    cv2.circle(mask, center, inner_radius, 255, thickness=-1)

    return mask


def compute_fill_metrics(
    roi: np.ndarray,
    mask: np.ndarray,
    raw_gray_roi: Optional[np.ndarray] = None,
) -> dict[str, float]:
    """
    Extract fill density, darkness intensity, and contrast statistics for a bubble ROI.

    Args:
        roi: 2D binary ROI NumPy array (where student markings are 255 and background is 0).
        mask: 2D binary inner circular mask NumPy array (where active zone is 255).
        raw_gray_roi: Optional 2D raw grayscale ROI array (dark ink ~0-80, bright paper ~200-255).

    Returns:
        Dictionary containing:
            - 'fill_density': Ratio of marked foreground pixels in active mask (0.0 to 1.0).
            - 'mean_intensity': Inverted normalized grayscale darkness in active mask (0.0 to 1.0).
            - 'std_dev': Grayscale standard deviation in active mask.
            - 'filled_pixels': Count of marked pixels.
            - 'total_pixels': Total pixels inside inner circular mask.

    Raises:
        ValueError: If array dimensions do not match or arrays are empty.
    """
    if roi is None or mask is None:
        raise ValueError("ROI and mask arrays cannot be None")
    if roi.shape[:2] != mask.shape[:2]:
        raise ValueError(f"ROI shape {roi.shape} and mask shape {mask.shape} do not match")

    # If 3-channel image was passed as ROI, convert to single channel
    binary_slice = roi if roi.ndim == 2 else cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    mask_slice = mask if mask.ndim == 2 else cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)

    mask_indices = mask_slice > 0
    total_pixels = int(np.count_nonzero(mask_indices))

    if total_pixels == 0:
        return {
            "fill_density": 0.0,
            "mean_intensity": 0.0,
            "std_dev": 0.0,
            "filled_pixels": 0,
            "total_pixels": 0,
        }

    # Count filled pixels (in inverted binary mask, ink pixels are > 0 / 255)
    masked_bin_pixels = binary_slice[mask_indices]
    filled_pixels = int(np.count_nonzero(masked_bin_pixels > 0))
    fill_density = float(filled_pixels) / float(total_pixels)

    if raw_gray_roi is not None:
        if raw_gray_roi.shape[:2] != mask.shape[:2]:
            raise ValueError(f"raw_gray_roi shape {raw_gray_roi.shape} does not match mask shape {mask.shape}")
        gray_slice = raw_gray_roi if raw_gray_roi.ndim == 2 else cv2.cvtColor(raw_gray_roi, cv2.COLOR_BGR2GRAY)
        masked_gray = gray_slice[mask_indices].astype(np.float64)
        # Invert normalized grayscale so 1.0 is full black ink and 0.0 is paper white
        mean_intensity = float(1.0 - (np.mean(masked_gray) / 255.0))
        std_dev = float(np.std(masked_gray))
    else:
        mean_intensity = fill_density
        std_dev = float(np.std(masked_bin_pixels.astype(np.float64)))

    return {
        "fill_density": round(fill_density, 4),
        "mean_intensity": round(mean_intensity, 4),
        "std_dev": round(std_dev, 4),
        "filled_pixels": filled_pixels,
        "total_pixels": total_pixels,
    }


def calibrate_sheet_threshold(
    warped_gray: np.ndarray,
    unprinted_regions: Optional[list[tuple[int, int, int, int]]] = None,
    base_threshold: float = 0.45,
) -> float:
    """
    Dynamically calibrate fill threshold by sampling unprinted background paper margin reflectance.

    Args:
        warped_gray: Canonical grayscale image array (shape H x W or H x W x C).
        unprinted_regions: List of (x, y, w, h) bounding boxes representing blank margin regions.
                           If None, samples default 4 margin zones.
        base_threshold: Baseline fill threshold (default 0.45).

    Returns:
        Calibrated float threshold bounded between 0.25 and 0.70.

    Raises:
        ValueError: If warped_gray is None or empty.
    """
    if warped_gray is None or warped_gray.size == 0:
        raise ValueError("warped_gray image cannot be None or empty")

    gray = warped_gray if warped_gray.ndim == 2 else cv2.cvtColor(warped_gray, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]

    if unprinted_regions is None or len(unprinted_regions) == 0:
        # Default 4 margin sample zones on canonical sheet
        unprinted_regions = [
            (int(w * 0.15), int(h * 0.02), int(w * 0.20), int(h * 0.02)),   # Top margin
            (int(w * 0.15), int(h * 0.96), int(w * 0.20), int(h * 0.02)),   # Bottom margin
            (int(w * 0.02), int(h * 0.45), int(w * 0.02), int(h * 0.10)),   # Left margin
            (int(w * 0.96), int(h * 0.45), int(w * 0.02), int(h * 0.10)),   # Right margin
        ]

    sample_intensities = []
    for (rx, ry, rw, rh) in unprinted_regions:
        x_min = max(0, min(w - 1, rx))
        x_max = max(0, min(w, rx + rw))
        y_min = max(0, min(h - 1, ry))
        y_max = max(0, min(h, ry + rh))

        if x_min < x_max and y_min < y_max:
            patch = gray[y_min:y_max, x_min:x_max]
            if patch.size > 0:
                sample_intensities.extend(patch.flatten())

    if len(sample_intensities) == 0:
        logger.warning("No valid margin samples extracted for baseline threshold calibration. Using base %f", base_threshold)
        return float(base_threshold)

    mean_bg = float(np.mean(sample_intensities))
    # Standard clean paper is ~240. If mean_bg is darker, delta is positive and shifts threshold upward.
    delta = ((240.0 - mean_bg) / 255.0) * 0.20
    calibrated = float(np.clip(base_threshold + delta, 0.25, 0.70))

    logger.debug("Calibrated background threshold: base=%.3f, mean_bg=%.1f, delta=%.3f -> final=%.4f", base_threshold, mean_bg, delta, calibrated)
    return round(calibrated, 4)


def classify_question_options(
    option_metrics: dict[str, dict[str, Any]],
    threshold: float = 0.45,
    faint_threshold_ratio: float = 0.60,
    ambiguity_margin: float = 0.10,
) -> tuple[Optional[str], float, str]:
    """
    Classify student multiple-choice bubble responses for a single question.

    Args:
        option_metrics: Dictionary mapping option keys (e.g. 'A', 'B', 'C', 'D') to metric dicts.
        threshold: Calibrated fill density threshold for a definitive mark (e.g. 0.45).
        faint_threshold_ratio: Fraction of threshold considered a faint/smudged mark (e.g. 0.60 * threshold).
        ambiguity_margin: Separation margin required between top two candidates.

    Returns:
        tuple of (selected_option, confidence, status)
            - selected_option: Chosen option string ('A', 'B', ...) or None.
            - confidence: Confidence score between 0.0 and 1.0.
            - status: Detection status string: 'SINGLE_MARK', 'MULTIPLE_MARKED', 'BLANK', or 'FAINT_MARK'.
    """
    if not option_metrics:
        return None, 0.0, "BLANK"

    # Extract fill density metric per option
    fills: dict[str, float] = {}
    for opt_key, metrics in option_metrics.items():
        if isinstance(metrics, dict):
            fills[str(opt_key)] = float(metrics.get("fill_density", 0.0))
        elif isinstance(metrics, (int, float)):
            fills[str(opt_key)] = float(metrics)
        else:
            fills[str(opt_key)] = 0.0

    # Sort options by fill density descending
    sorted_options = sorted(fills.items(), key=lambda item: item[1], reverse=True)
    opt1, fill1 = sorted_options[0]
    opt2, fill2 = sorted_options[1] if len(sorted_options) > 1 else (None, 0.0)

    marked_options = [opt for opt, val in sorted_options if val >= threshold]
    faint_threshold = threshold * faint_threshold_ratio

    # 1. Multiple Marks Detected
    if len(marked_options) >= 2:
        # Check if top mark is overwhelming (> 40% difference due to pencil erasure)
        if fill1 - fill2 > 0.40:
            confidence = round(float(np.clip(fill1 - fill2, 0.50, 0.90)), 4)
            return opt1, confidence, "SINGLE_MARK"

        # Ambiguous multiple marks
        conf = round(float(max(0.0, 1.0 - (fill2 / max(fill1, 1e-6)))), 4)
        return None, conf, "MULTIPLE_MARKED"

    # 2. Single Definitive Mark Detected
    if len(marked_options) == 1:
        # Margin over next candidate
        margin = fill1 - fill2
        conf = round(float(np.clip(fill1 * 0.7 + margin * 0.3, 0.50, 1.0)), 4)
        return opt1, conf, "SINGLE_MARK"

    # 3. No Options Exceed Definitive Threshold: Check for Faint Mark vs Blank
    if fill1 >= faint_threshold:
        conf = round(float(fill1 / max(threshold, 1e-6)), 4)
        return opt1, conf, "FAINT_MARK"

    # 4. Completely Blank
    conf = round(float(max(0.0, 1.0 - fill1)), 4)
    return None, conf, "BLANK"


def detect_all_sheet_bubbles(
    warped_img: np.ndarray,
    warped_gray: Optional[np.ndarray] = None,
    template: Optional[TemplateConfig] = None,
    threshold: Optional[float] = None,
    erosion_pct: float = 0.20,
) -> dict[int, dict[str, Any]]:
    """
    End-to-end detection orchestrator for all multiple-choice questions on an aligned sheet.

    Args:
        warped_img: Canonical aligned binary mask (or raw image) where student ink is foreground.
        warped_gray: Optional canonical aligned grayscale image for intensity/contrast metrics.
        template: TemplateConfig defining questions layout and coordinates.
        threshold: Optional manual fill threshold override. If None, dynamically calibrated.
        erosion_pct: Inner erosion percentage for bubble mask (default 0.20).

    Returns:
        Dictionary mapping question_number (int) to question detection results:
            - question_number: int
            - section: str
            - selected_option: Optional[str]
            - confidence: float
            - status: str ('SINGLE_MARK', 'MULTIPLE_MARKED', 'BLANK', 'FAINT_MARK')
            - options: dict[str, dict] containing individual bubble fill metrics

    Raises:
        ValueError: If template or image inputs are missing.
    """
    if warped_img is None or warped_img.size == 0:
        raise ValueError("warped_img cannot be None or empty")

    if template is None:
        raise ValueError("template (TemplateConfig) is required for detection")

    gray_canvas = warped_gray if warped_gray is not None else warped_img
    active_threshold = threshold if threshold is not None else calibrate_sheet_threshold(gray_canvas)

    results: dict[int, dict[str, Any]] = {}

    for question in template.questions:
        q_num = question.q_num
        section = question.section
        option_metrics: dict[str, dict[str, Any]] = {}

        for opt_key, bubble in question.options_map.items():
            cx = bubble.cx
            cy = bubble.cy
            r = bubble.r

            # 1. Slice binary ROI and optional grayscale ROI
            bin_roi = extract_bubble_roi(warped_img, cx=cx, cy=cy, radius=r)
            gray_roi = extract_bubble_roi(gray_canvas, cx=cx, cy=cy, radius=r) if gray_canvas is not None else None

            # 2. Generate inner-eroded circular mask
            mask = generate_inner_circle_mask(roi_size=2 * r, radius=r, erosion_pct=erosion_pct)

            # 3. Compute fill and darkness metrics
            metrics = compute_fill_metrics(roi=bin_roi, mask=mask, raw_gray_roi=gray_roi)
            option_metrics[str(opt_key)] = metrics

        # 4. Classify question response
        selected_opt, confidence, status = classify_question_options(
            option_metrics=option_metrics,
            threshold=active_threshold,
        )

        results[q_num] = {
            "question_number": q_num,
            "section": section,
            "selected_option": selected_opt,
            "confidence": confidence,
            "status": status,
            "options": option_metrics,
        }

    logger.info(
        "Detected all %d questions: %d single marks, %d multiple marked, %d blank, %d faint marks (threshold=%.4f)",
        len(results),
        sum(1 for r in results.values() if r["status"] == "SINGLE_MARK"),
        sum(1 for r in results.values() if r["status"] == "MULTIPLE_MARKED"),
        sum(1 for r in results.values() if r["status"] == "BLANK"),
        sum(1 for r in results.values() if r["status"] == "FAINT_MARK"),
        active_threshold,
    )

    return results





