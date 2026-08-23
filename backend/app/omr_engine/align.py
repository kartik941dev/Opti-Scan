"""
Corner Detection, Ordering & 4-Point Homography Perspective Alignment.
"""

from typing import List, Optional, Tuple, Union
import cv2
import numpy as np


def find_fiducial_markers(
    binary_mask: np.ndarray,
    min_area: float = 1000.0,
    max_area: float = 35000.0,
    min_aspect_ratio: float = 0.70,
    max_aspect_ratio: float = 1.30,
    min_solidity: float = 0.80,
) -> List[dict]:
    """
    Detect square fiducial registration corner markers on inverted binary sheet.
    """
    contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
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

    return candidates


def order_corner_points(pts: np.ndarray) -> np.ndarray:
    """
    Order 4 corner coordinates in clockwise order starting from Top-Left:
    [Top-Left, Top-Right, Bottom-Right, Bottom-Left].
    """
    if pts.shape != (4, 2):
        raise ValueError(f"order_corner_points expects shape (4, 2), got {pts.shape}")

    center = pts.mean(axis=0)
    angles = np.arctan2(pts[:, 1] - center[1], pts[:, 0] - center[0])
    sort_idx = np.argsort(angles)
    clockwise_pts = pts[sort_idx]

    sums = clockwise_pts[:, 0] + clockwise_pts[:, 1]
    tl_idx = np.argmin(sums)

    ordered = np.roll(clockwise_pts, -tl_idx, axis=0)
    return ordered.astype(np.float32)


def extrapolate_missing_corner(three_pts: np.ndarray) -> np.ndarray:
    """
    Extrapolate 4th missing corner given 3 known corners using vector geometry.
    """
    d01 = np.linalg.norm(three_pts[0] - three_pts[1])
    d12 = np.linalg.norm(three_pts[1] - three_pts[2])
    d20 = np.linalg.norm(three_pts[2] - three_pts[0])

    if d01 >= d12 and d01 >= d20:
        p_missing = three_pts[0] + three_pts[1] - three_pts[2]
    elif d12 >= d01 and d12 >= d20:
        p_missing = three_pts[1] + three_pts[2] - three_pts[0]
    else:
        p_missing = three_pts[2] + three_pts[0] - three_pts[1]

    all_four = np.vstack([three_pts, p_missing])
    return order_corner_points(all_four)


def get_four_corners(
    marker_candidates: List[dict],
    image_shape: Tuple[int, int],
) -> np.ndarray:
    """
    Select the optimal 4 corner registration coordinates.
    """
    n_found = len(marker_candidates)
    if n_found < 3:
        # Fallback to sheet boundaries if fiducials are obscured
        h, w = image_shape[:2]
        return np.array([
            [80.0, 80.0],
            [w - 80.0, 80.0],
            [w - 80.0, h - 80.0],
            [80.0, h - 80.0],
        ], dtype=np.float32)

    centers = np.array([m["center"] for m in marker_candidates], dtype=np.float32)
    if n_found == 4:
        return order_corner_points(centers)

    if n_found == 3:
        return extrapolate_missing_corner(centers)

    rect = cv2.minAreaRect(centers)
    box_corners = cv2.boxPoints(rect)

    selected_points = []
    selected_indices = set()
    for corner in box_corners:
        dists = np.linalg.norm(centers - corner, axis=1)
        for idx in np.argsort(dists):
            if idx not in selected_indices:
                selected_indices.add(idx)
                selected_points.append(centers[idx])
                break

    if len(selected_points) == 4:
        return order_corner_points(np.array(selected_points, dtype=np.float32))

    return order_corner_points(centers[:4])


def align_pipeline(
    bgr_image: np.ndarray,
    binary_mask: np.ndarray,
    target_width: int = 1654,
    target_height: int = 2339,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Detect fiducials and compute homography perspective warp.
    """
    markers = find_fiducial_markers(binary_mask)
    src_corners = get_four_corners(markers, binary_mask.shape)

    dst_corners = np.array([
        [110.0, 110.0],                          # Top-Left center
        [target_width - 110.0, 110.0],           # Top-Right center
        [target_width - 110.0, target_height - 110.0],  # Bottom-Right center
        [110.0, target_height - 110.0],          # Bottom-Left center
    ], dtype=np.float32)

    matrix, _ = cv2.findHomography(src_corners, dst_corners, cv2.RANSAC, 5.0)
    if matrix is None:
        matrix = cv2.getPerspectiveTransform(src_corners, dst_corners)

    warped_bgr = cv2.warpPerspective(bgr_image, matrix, (target_width, target_height), flags=cv2.INTER_LINEAR)
    warped_binary = cv2.warpPerspective(binary_mask, matrix, (target_width, target_height), flags=cv2.INTER_NEAREST)

    return warped_bgr, warped_binary, matrix
