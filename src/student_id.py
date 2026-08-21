"""
Student Roll Number / ID Grid Decoder for OptiScan (Phase 6).
Evaluates digit column bubbles (0-9) to decode multi-digit student ID / roll numbers.
"""

from typing import Any, Optional, Union

import numpy as np

from src.bubble_detect import compute_fill_metrics, extract_bubble_roi, generate_inner_circle_mask
from src.utils.exceptions import StudentIdParsingError
from src.utils.logger import get_logger

logger = get_logger("student_id")


def decode_student_id(
    warped_binary: np.ndarray,
    id_grid_config: Union[dict[str, Any], list[dict[str, Any]]],
    threshold: float = 0.40,
    erosion_pct: float = 0.20,
    strict: bool = False,
) -> str:
    """
    Decode student ID / roll number from the aligned binary canvas and ID grid specification.

    Args:
        warped_binary: Canonical binary mask where marked bubbles are foreground (255).
        id_grid_config: Mapping or list of student ID digit bubble specifications.
        threshold: Fill density threshold for identifying a marked digit bubble (default 0.40).
        erosion_pct: Inner circular mask erosion percentage (default 0.20).
        strict: If True, raises StudentIdParsingError on ambiguous multiple marks or blank columns.

    Returns:
        Decoded student ID string (e.g. "202641" or "10452X").

    Raises:
        StudentIdParsingError: If id_grid_config is empty or invalid, or if strict is True and decoding is ambiguous.
        ValueError: If warped_binary is None or empty.
    """
    if warped_binary is None or warped_binary.size == 0:
        raise ValueError("warped_binary cannot be None or empty")

    if not id_grid_config:
        raise StudentIdParsingError("Student ID grid configuration is missing or empty")

    # Extract bubble definitions into list
    bubbles: list[dict[str, Any]] = []
    if isinstance(id_grid_config, dict):
        for key, val in id_grid_config.items():
            if isinstance(val, dict):
                bubbles.append(val)
    elif isinstance(id_grid_config, list):
        for item in id_grid_config:
            if isinstance(item, dict):
                bubbles.append(item)
            elif hasattr(item, "model_dump"):
                bubbles.append(item.model_dump())

    if not bubbles:
        raise StudentIdParsingError("No valid digit bubble coordinates found in id_grid_config")

    # Group bubbles by column index
    columns: dict[int, list[dict[str, Any]]] = {}
    for b in bubbles:
        col = int(b.get("col", 0))
        if col not in columns:
            columns[col] = []
        columns[col].append(b)

    # Sort column indices
    sorted_col_indices = sorted(columns.keys())
    decoded_digits: list[str] = []

    for col_idx in sorted_col_indices:
        col_bubbles = columns[col_idx]
        # Sort by digit 0..9
        col_bubbles_sorted = sorted(col_bubbles, key=lambda b: int(b.get("digit", 0)))

        digit_fills: list[tuple[int, float]] = []

        for b in col_bubbles_sorted:
            cx = int(b["cx"])
            cy = int(b["cy"])
            r = int(b.get("radius", b.get("r", 11)))
            digit = int(b.get("digit", 0))

            bin_roi = extract_bubble_roi(warped_binary, cx=cx, cy=cy, radius=r)
            mask = generate_inner_circle_mask(roi_size=2 * r, radius=r, erosion_pct=erosion_pct)
            metrics = compute_fill_metrics(roi=bin_roi, mask=mask)

            fill_density = metrics["fill_density"]
            digit_fills.append((digit, fill_density))

        # Sort candidate digits by fill density descending
        digit_fills.sort(key=lambda item: item[1], reverse=True)
        top_digit, top_fill = digit_fills[0]
        second_digit, second_fill = digit_fills[1] if len(digit_fills) > 1 else (-1, 0.0)

        # Classification
        if top_fill >= threshold:
            # Check for ambiguous multiple marks in the same column
            if second_fill >= threshold and (top_fill - second_fill) < 0.20:
                logger.warning("Ambiguous multiple marks in student ID column %d (digits %d and %d)", col_idx, top_digit, second_digit)
                if strict:
                    raise StudentIdParsingError(
                        f"Ambiguous multiple marks in student ID column {col_idx}",
                        details={"col": col_idx, "candidates": [top_digit, second_digit], "fills": [top_fill, second_fill]},
                    )
                decoded_digits.append("?")
            else:
                decoded_digits.append(str(top_digit))
        else:
            logger.debug("No marked digit in student ID column %d (top fill: %.3f)", col_idx, top_fill)
            if strict:
                raise StudentIdParsingError(
                    f"No marked digit found in student ID column {col_idx}",
                    details={"col": col_idx, "top_fill": top_fill},
                )
            decoded_digits.append("X")

    result_id = "".join(decoded_digits)
    logger.info("Decoded student ID: '%s' (%d columns)", result_id, len(decoded_digits))
    return result_id
