"""
Geometric Registration & 4-Point Perspective Correction Pipeline for OptiScan.
Detects fiducial corner markers, orders coordinates (TL, TR, BR, BL),
handles 3-point extrapolation for torn corners, and warps to canonical canvas.
"""

from typing import Optional, Union

import cv2
import numpy as np

from src.utils.exceptions import (
    FiducialMarkerNotFoundError,
    PerspectiveWarpError,
)
from src.utils.logger import get_logger

logger = get_logger("align")


def find_fiducial_markers(
    binary_image: np.ndarray,
    min_area: float = 400.0,
    max_area: float = 30000.0,
    min_aspect_ratio: float = 0.75,
    max_aspect_ratio: float = 1.30,
    min_solidity: float = 0.75,
) -> list[dict[str, Union[tuple[int, int], np.ndarray, float]]]:
    """
    Detect fiducial corner registration markers from an inverted binary image.

    Filters contours by:
    - Bounding area within [min_area, max_area]
    - Aspect ratio (width / height) close to 1.0 (square)
    - Solidity (contour area / convex hull area) high for solid squares.

    Args:
        binary_image: 2D inverted binary mask (ink/markers = 255, background = 0).
        min_area: Minimum contour area threshold.
        max_area: Maximum contour area threshold.
        min_aspect_ratio: Minimum aspect ratio (width / height).
        max_aspect_ratio: Maximum aspect ratio (width / height).
        min_solidity: Minimum solidity threshold (compactness).

    Returns:
        List of dicts containing marker info: {'center': (cx, cy), 'contour': cnt, 'area': area, 'bbox': (x, y, w, h)}
    """
    if binary_image.ndim != 2:
        raise ValueError(f"find_fiducial_markers expects a 2D binary image, got shape {binary_image.shape}")

    contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area or area > max_area:
            continue

        x, y, w, h = cv2.boundingRect(cnt)
        aspect_ratio = float(w) / float(h)
        if aspect_ratio < min_aspect_ratio or aspect_ratio > max_aspect_ratio:
            continue

        hull = cv2.convexHull(cnt)
        hull_area = cv2.contourArea(hull)
        if hull_area <= 0:
            continue

        solidity = float(area) / float(hull_area)
        if solidity < min_solidity:
            continue

        # Compute centroid using moments
        m = cv2.moments(cnt)
        if m["m00"] != 0:
            cx = int(round(m["m10"] / m["m00"]))
            cy = int(round(m["m01"] / m["m00"]))
        else:
            cx = x + w // 2
            cy = y + h // 2

        candidates.append({
            "center": (cx, cy),
            "contour": cnt,
            "area": area,
            "bbox": (x, y, w, h),
            "aspect_ratio": aspect_ratio,
            "solidity": solidity,
        })

    logger.debug("Detected %d candidate fiducial markers", len(candidates))
    return candidates


def order_corner_points(pts: np.ndarray) -> np.ndarray:
    """
    Sort 4 coordinates in consistent canonical clock-wise order:
    [Top-Left, Top-Right, Bottom-Right, Bottom-Left].

    Uses centroid polar angle sorting to guarantee 4 unique ordered corners
    regardless of sheet rotation angle.

    Args:
        pts: NumPy array of shape (4, 2) representing (x, y) coordinates.

    Returns:
        NumPy float32 array of shape (4, 2) ordered as [TL, TR, BR, BL].
    """
    if pts.shape != (4, 2):
        raise ValueError(f"order_corner_points expects shape (4, 2), got {pts.shape}")

    # Compute centroid
    center = pts.mean(axis=0)

    # Compute polar angle relative to centroid
    angles = np.arctan2(pts[:, 1] - center[1], pts[:, 0] - center[0])

    # Sort points clockwise by polar angle
    sort_idx = np.argsort(angles)
    clockwise_pts = pts[sort_idx]

    # Find the Top-Left point (smallest x + y sum)
    sums = clockwise_pts[:, 0] + clockwise_pts[:, 1]
    tl_idx = np.argmin(sums)

    # Roll array so TL is index 0 (followed clockwise by TR, BR, BL)
    ordered = np.roll(clockwise_pts, -tl_idx, axis=0)
    return ordered.astype(np.float32)


def extrapolate_missing_corner(
    three_pts: np.ndarray,
    sheet_aspect_ratio: float = 1.414,
) -> np.ndarray:
    """
    Extrapolate 4th missing corner given 3 known corners using parallelogram vector geometry.
    For a rectangle/parallelogram: TL + BR = TR + BL
    Therefore:
    - TL = TR + BL - BR
    - TR = TL + BR - BL
    - BR = TR + BL - TL
    - BL = TL + BR - TR

    Args:
        three_pts: NumPy array of shape (3, 2) containing 3 known (x, y) points.
        sheet_aspect_ratio: Expected aspect ratio of canonical sheet (default 1.414 for standard A4).

    Returns:
        NumPy float32 array of shape (4, 2) ordered as [TL, TR, BR, BL].

    Raises:
        ValueError: If three_pts is not of shape (3, 2).
    """
    if three_pts.shape != (3, 2):
        raise ValueError(f"extrapolate_missing_corner expects shape (3, 2), got {three_pts.shape}")

    # Find the pair of points with the largest distance between them (the diagonal)
    d01 = np.linalg.norm(three_pts[0] - three_pts[1])
    d12 = np.linalg.norm(three_pts[1] - three_pts[2])
    d20 = np.linalg.norm(three_pts[2] - three_pts[0])

    if d01 >= d12 and d01 >= d20:
        # Diagonal is between pts 0 and 1, middle corner is pt 2
        p_missing = three_pts[0] + three_pts[1] - three_pts[2]
    elif d12 >= d01 and d12 >= d20:
        # Diagonal is between pts 1 and 2, middle corner is pt 0
        p_missing = three_pts[1] + three_pts[2] - three_pts[0]
    else:
        # Diagonal is between pts 2 and 0, middle corner is pt 1
        p_missing = three_pts[2] + three_pts[0] - three_pts[1]

    all_four = np.vstack([three_pts, p_missing])
    return order_corner_points(all_four)


def get_four_corners(
    marker_candidates: list[dict],
    image_shape: tuple[int, int],
) -> np.ndarray:
    """
    Select the best 4 corner registration points from candidate detections.
    Uses oriented minimum bounding box geometry for rotation invariance.

    Args:
        marker_candidates: List of detected marker dicts from find_fiducial_markers.
        image_shape: (height, width) of the image.

    Returns:
        NumPy float32 array of shape (4, 2) ordered [TL, TR, BR, BL].

    Raises:
        FiducialMarkerNotFoundError: If fewer than 3 markers are detected.
    """
    n_found = len(marker_candidates)

    if n_found < 3:
        raise FiducialMarkerNotFoundError(
            f"Insufficient corner markers detected (found {n_found}, required at least 3)",
            markers_found=n_found,
        )

    centers = np.array([m["center"] for m in marker_candidates], dtype=np.float32)

    if n_found == 4:
        return order_corner_points(centers)

    if n_found == 3:
        logger.warning("Exactly 3 markers found. Extrapolating 4th corner marker using vector geometry.")
        return extrapolate_missing_corner(centers)

    # If more than 4 candidates found, fit oriented bounding box to find the 4 extreme rotated corners
    rect = cv2.minAreaRect(centers.astype(np.float32))
    box_corners = cv2.boxPoints(rect)  # (4, 2) oriented corners

    selected_indices = set()
    selected_points = []
    for corner in box_corners:
        dists = np.linalg.norm(centers - corner, axis=1)
        sorted_indices = np.argsort(dists)
        for idx in sorted_indices:
            if idx not in selected_indices:
                selected_indices.add(idx)
                selected_points.append(centers[idx])
                break

    # If fewer than 4 unique points selected, fill remaining with closest unused
    if len(selected_points) < 4:
        for idx in range(len(centers)):
            if idx not in selected_indices:
                selected_indices.add(idx)
                selected_points.append(centers[idx])
            if len(selected_points) == 4:
                break

    return order_corner_points(np.array(selected_points, dtype=np.float32))


def warp_to_canonical(
    image: np.ndarray,
    ordered_corners: np.ndarray,
    target_width: int = 1654,
    target_height: int = 2339,
    dst_corners: Optional[np.ndarray] = None,
    border_value: Optional[Union[int, tuple]] = None,
    interpolation: int = cv2.INTER_CUBIC,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Apply 4-point perspective transform (Homography warp) to map the active
    sheet region to a canonical high-resolution canvas.

    Args:
        image: Input image array (Grayscale or RGB).
        ordered_corners: 4 ordered points [TL, TR, BR, BL] of shape (4, 2).
        target_width: Target canvas width in pixels (e.g. 1654 for A4 @ 200 DPI).
        target_height: Target canvas height in pixels (e.g. 2339 for A4 @ 200 DPI).
        dst_corners: Optional target coordinates for the 4 ordered corners.
                     If None, maps to canonical fiducial marker centers (margin 110px).
        border_value: Pixel fill value for areas outside bounding warp.
        interpolation: OpenCV interpolation mode.

    Returns:
        tuple of (warped_image, homography_matrix)

    Raises:
        PerspectiveWarpError: If homography computation fails.
    """
    if ordered_corners.shape != (4, 2):
        raise PerspectiveWarpError(f"ordered_corners must have shape (4, 2), got {ordered_corners.shape}")

    area = cv2.contourArea(ordered_corners.astype(np.float32))
    if area < 10.0:
        raise PerspectiveWarpError(f"Degenerate corner coordinates with near-zero area: {area:.2f}")

    if dst_corners is None:
        margin_x = int(round(target_width * (110.0 / 1654.0)))
        margin_y = int(round(target_height * (110.0 / 2339.0)))
        target_dst = np.array([
            [margin_x, margin_y],
            [target_width - margin_x, margin_y],
            [target_width - margin_x, target_height - margin_y],
            [margin_x, target_height - margin_y],
        ], dtype=np.float32)
    else:
        target_dst = dst_corners.astype(np.float32)

    if border_value is None:
        border_val = (255, 255, 255) if image.ndim == 3 else (0 if np.array_equal(np.unique(image), [0, 255]) else 255)
    else:
        border_val = border_value

    try:
        matrix = cv2.getPerspectiveTransform(ordered_corners.astype(np.float32), target_dst)
        if matrix is None or np.any(np.isnan(matrix)) or np.any(np.isinf(matrix)) or abs(np.linalg.det(matrix)) < 1e-9:
            raise PerspectiveWarpError("Homography transform matrix computation returned invalid or singular matrix")

        warped = cv2.warpPerspective(
            image,
            matrix,
            (target_width, target_height),
            flags=interpolation,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=border_val,
        )
        return warped, matrix

    except Exception as e:
        if isinstance(e, PerspectiveWarpError):
            raise
        raise PerspectiveWarpError(f"Error executing perspective warp: {str(e)}") from e


def align_pipeline(
    raw_image: np.ndarray,
    binary_mask: np.ndarray,
    target_width: int = 1654,
    target_height: int = 2339,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Full registration & alignment pipeline:
    1. Find 4 corner fiducial markers in binary mask.
    2. Order corners to [TL, TR, BR, BL].
    3. Warp both raw RGB image and binary mask to canonical template resolution.

    Args:
        raw_image: RGB normalized input image.
        binary_mask: Inverted adaptive binary mask.
        target_width: Canonical template width.
        target_height: Canonical template height.

    Returns:
        tuple of (warped_rgb, warped_binary, homography_matrix)
    """
    markers = find_fiducial_markers(binary_mask)
    corners = get_four_corners(markers, binary_mask.shape)

    warped_rgb, matrix = warp_to_canonical(
        raw_image,
        corners,
        target_width=target_width,
        target_height=target_height,
        border_value=(255, 255, 255),
        interpolation=cv2.INTER_CUBIC,
    )
    warped_binary, _ = warp_to_canonical(
        binary_mask,
        corners,
        target_width=target_width,
        target_height=target_height,
        border_value=0,
        interpolation=cv2.INTER_NEAREST,
    )

    logger.debug("Sheet successfully aligned and warped to %dx%d", target_width, target_height)
    return warped_rgb, warped_binary, matrix
