"""
Unit tests for corner registration and perspective correction (Phase 3).
"""

import cv2
import numpy as np
import pytest

from src.align import (
    align_pipeline,
    extrapolate_missing_corner,
    find_fiducial_markers,
    get_four_corners,
    order_corner_points,
    warp_to_canonical,
)
from src.preprocess import preprocess_pipeline
from src.utils.exceptions import FiducialMarkerNotFoundError
from tests.fixtures.generate_mock_omr import generate_synthetic_omr_sheet


class TestAlignment:
    def test_order_corner_points(self):
        # 1. 4 unordered points in random permutation
        pts = np.array([
            [1500, 2000],  # BR
            [100, 100],    # TL
            [100, 2000],   # BL
            [1500, 100],   # TR
        ], dtype=np.float32)

        ordered = order_corner_points(pts)

        # Expected: [TL, TR, BR, BL]
        np.testing.assert_array_equal(ordered[0], [100, 100])
        np.testing.assert_array_equal(ordered[1], [1500, 100])
        np.testing.assert_array_equal(ordered[2], [1500, 2000])
        np.testing.assert_array_equal(ordered[3], [100, 2000])

        # 2. Rotated box points
        # Centered around (500, 500), rotated ~20 deg
        rotated_pts = np.array([
            [650.0, 750.0],  # BR
            [350.0, 250.0],  # TL
            [250.0, 650.0],  # BL
            [750.0, 350.0],  # TR
        ], dtype=np.float32)
        ord_rot = order_corner_points(rotated_pts)
        assert ord_rot.shape == (4, 2)
        np.testing.assert_array_equal(ord_rot[0], [350.0, 250.0])  # TL
        np.testing.assert_array_equal(ord_rot[1], [750.0, 350.0])  # TR
        np.testing.assert_array_equal(ord_rot[2], [650.0, 750.0])  # BR
        np.testing.assert_array_equal(ord_rot[3], [250.0, 650.0])  # BL

        # 3. Invalid shapes raise ValueError
        with pytest.raises(ValueError):
            order_corner_points(np.zeros((3, 2), dtype=np.float32))
        with pytest.raises(ValueError):
            order_corner_points(np.zeros((4, 3), dtype=np.float32))

    def test_extrapolate_missing_corner(self):
        # 1. Missing Bottom-Right (BR): Known TL=(100, 100), TR=(500, 100), BL=(100, 700) -> Expected BR=(500, 700)
        pts_missing_br = np.array([
            [100, 100],  # TL
            [500, 100],  # TR
            [100, 700],  # BL
        ], dtype=np.float32)
        rec_br = extrapolate_missing_corner(pts_missing_br)
        assert rec_br.shape == (4, 2)
        np.testing.assert_allclose(rec_br[0], [100, 100], atol=1.0)  # TL
        np.testing.assert_allclose(rec_br[1], [500, 100], atol=1.0)  # TR
        np.testing.assert_allclose(rec_br[2], [500, 700], atol=1.0)  # BR recovered
        np.testing.assert_allclose(rec_br[3], [100, 700], atol=1.0)  # BL

        # 2. Missing Top-Left (TL): Known TR=(500, 100), BR=(500, 700), BL=(100, 700) -> Expected TL=(100, 100)
        pts_missing_tl = np.array([
            [500, 100],  # TR
            [500, 700],  # BR
            [100, 700],  # BL
        ], dtype=np.float32)
        rec_tl = extrapolate_missing_corner(pts_missing_tl)
        np.testing.assert_allclose(rec_tl[0], [100, 100], atol=1.0)  # TL recovered

        # 3. Missing Top-Right (TR): Known TL=(100, 100), BR=(500, 700), BL=(100, 700) -> Expected TR=(500, 100)
        pts_missing_tr = np.array([
            [100, 100],  # TL
            [500, 700],  # BR
            [100, 700],  # BL
        ], dtype=np.float32)
        rec_tr = extrapolate_missing_corner(pts_missing_tr)
        np.testing.assert_allclose(rec_tr[1], [500, 100], atol=1.0)  # TR recovered

        # 4. Missing Bottom-Left (BL): Known TL=(100, 100), TR=(500, 100), BR=(500, 700) -> Expected BL=(100, 700)
        pts_missing_bl = np.array([
            [100, 100],  # TL
            [500, 100],  # TR
            [500, 700],  # BR
        ], dtype=np.float32)
        rec_bl = extrapolate_missing_corner(pts_missing_bl)
        np.testing.assert_allclose(rec_bl[3], [100, 700], atol=1.0)  # BL recovered

        # 5. Invalid shape raises ValueError
        with pytest.raises(ValueError):
            extrapolate_missing_corner(np.zeros((4, 2), dtype=np.float32))
        with pytest.raises(ValueError):
            extrapolate_missing_corner(np.zeros((2, 2), dtype=np.float32))

    def test_find_fiducials(self):
        # 1. Detect markers on clean synthetic OMR sheet
        img, meta = generate_synthetic_omr_sheet(num_questions=50)
        _, _, binary_mask, _ = preprocess_pipeline(img)

        markers = find_fiducial_markers(binary_mask, min_area=400, max_area=30000)
        assert len(markers) >= 4

        # Validate structure and characteristics of detected markers
        for m in markers:
            assert "center" in m
            assert "contour" in m
            assert "area" in m
            assert "bbox" in m
            assert "aspect_ratio" in m
            assert "solidity" in m
            # Fiducial markers are solid squares with aspect ratio ~1.0 and high solidity >=0.75
            assert 0.70 <= m["aspect_ratio"] <= 1.30
            assert m["solidity"] >= 0.75

        # 2. Rejection of non-square shapes (e.g. thin horizontal line)
        line_mask = np.zeros((500, 500), dtype=np.uint8)
        cv2.line(line_mask, (50, 250), (450, 250), 255, 3)
        assert len(find_fiducial_markers(line_mask)) == 0

        # 3. Invalid shape raises ValueError
        with pytest.raises(ValueError):
            find_fiducial_markers(np.zeros((100, 100, 3), dtype=np.uint8))

    def test_find_fiducials_on_clean_sheet(self):
        img, meta = generate_synthetic_omr_sheet(num_questions=50)
        _, _, binary_mask, _ = preprocess_pipeline(img)

        markers = find_fiducial_markers(binary_mask)
        # Should detect 4 solid corner squares
        assert len(markers) >= 4

        corners = get_four_corners(markers, binary_mask.shape)
        assert corners.shape == (4, 2)

        # Check approximate corner positions near margins
        # TL ~ (110, 110), TR ~ (1544, 110), BR ~ (1544, 2229), BL ~ (110, 2229)
        assert corners[0][0] < 200 and corners[0][1] < 200  # TL
        assert corners[1][0] > 1400 and corners[1][1] < 200 # TR
        assert corners[2][0] > 1400 and corners[2][1] > 2000 # BR
        assert corners[3][0] < 200 and corners[3][1] > 2000  # BL

    def test_insufficient_markers_raises_error(self):
        # Empty binary mask with no markers
        empty_mask = np.zeros((1000, 1000), dtype=np.uint8)
        markers = find_fiducial_markers(empty_mask)
        assert len(markers) == 0

        with pytest.raises(FiducialMarkerNotFoundError) as exc_info:
            get_four_corners(markers, empty_mask.shape)
        assert exc_info.value.error_code == "FIDUCIAL_MARKERS_NOT_FOUND"

    def test_warp_perspective(self):
        # 1. 3-channel color image warp
        color_img = np.full((1000, 800, 3), 200, dtype=np.uint8)
        corners = np.array([
            [50.0, 50.0],
            [750.0, 50.0],
            [750.0, 950.0],
            [50.0, 950.0],
        ], dtype=np.float32)

        warped, matrix = warp_to_canonical(color_img, corners, target_width=1654, target_height=2339)
        assert warped.shape == (2339, 1654, 3)
        assert matrix.shape == (3, 3)
        assert warped.dtype == np.uint8

        # 2. 2-channel/grayscale image warp
        gray_img = np.full((1000, 800), 128, dtype=np.uint8)
        warped_gray, matrix_gray = warp_to_canonical(gray_img, corners, target_width=800, target_height=1200)
        assert warped_gray.shape == (1200, 800)
        assert matrix_gray.shape == (3, 3)

        # 3. Degenerate collinear points raise PerspectiveWarpError
        collinear_corners = np.array([
            [10.0, 10.0],
            [20.0, 20.0],
            [30.0, 30.0],
            [40.0, 40.0],
        ], dtype=np.float32)
        with pytest.raises(Exception):
            warp_to_canonical(color_img, collinear_corners)

    @pytest.mark.parametrize("angle", [5.0, 15.0, 30.0, 45.0])
    def test_warp_perspective_and_rotations(self, angle: float):
        """
        Step 3.5: Validate warp accuracy and canonical projection against
        sheets rotated at 5, 15, 30, and 45 degrees.
        """
        img_rot, meta = generate_synthetic_omr_sheet(num_questions=50, rotation_deg=angle, noise_level=5.0)
        rgb_scaled, gray_clahe, binary_mask, scale = preprocess_pipeline(img_rot)

        warped_rgb, warped_binary, matrix = align_pipeline(
            rgb_scaled, binary_mask, target_width=1654, target_height=2339
        )

        assert warped_rgb.shape == (2339, 1654, 3)
        assert warped_binary.shape == (2339, 1654)
        assert matrix.shape == (3, 3)
        assert warped_binary.dtype == np.uint8

        # Ensure homography matrix is non-singular and valid
        det = np.linalg.det(matrix)
        assert not np.isnan(det) and not np.isinf(det) and abs(det) > 1e-6

        # Verify that active assessment grid has preserved ink markings (bubbles/text)
        assert 255 in np.unique(warped_binary)
        active_grid_ink = warped_binary[600:2000, 100:1500]
        assert active_grid_ink.sum() > 0



def test_find_fiducials():
    """Standalone test entrypoint for Step 3.1 verification."""
    TestAlignment().test_find_fiducials()


def test_order_corner_points():
    """Standalone test entrypoint for Step 3.2 verification."""
    TestAlignment().test_order_corner_points()


def test_extrapolate_missing_corner():
    """Standalone test entrypoint for Step 3.3 verification."""
    TestAlignment().test_extrapolate_missing_corner()


def test_warp_perspective():
    """Standalone test entrypoint for Step 3.4 verification."""
    TestAlignment().test_warp_perspective()


