"""
Unit tests for Bubble Slicing, Masking, and Fill Detection Engine (Phase 5).
"""

import numpy as np
import pytest

from src.align import align_pipeline
from src.bubble_detect import (
    calibrate_sheet_threshold,
    classify_question_options,
    compute_fill_metrics,
    detect_all_sheet_bubbles,
    extract_bubble_roi,
    generate_inner_circle_mask,
)
from src.models.template import TemplateConfig
from src.preprocess import preprocess_pipeline
from tests.fixtures.generate_mock_omr import generate_synthetic_omr_sheet


class TestBubbleDetect:
    """Test suite for Phase 5: Bubble Slicing and Detection."""

    def test_extract_bubble_roi(self):
        """Step 5.1: Test circular ROI extraction with exact (2r x 2r) geometry and clipping."""
        # 1. Standard centered extraction on 2D binary/grayscale canvas
        canvas = np.zeros((100, 100), dtype=np.uint8)
        canvas[40:60, 40:60] = 255  # Mark active region

        roi = extract_bubble_roi(canvas, cx=50, cy=50, radius=10)
        assert roi.shape == (20, 20)
        assert roi.dtype == np.uint8
        assert np.array_equal(roi, canvas[40:60, 40:60])

        # 2. Radius 13 (Standard OptiScan bubble size) -> 26x26 ROI
        roi_13 = extract_bubble_roi(canvas, cx=50, cy=50, radius=13)
        assert roi_13.shape == (26, 26)

        # 3. 3-channel RGB image extraction
        color_canvas = np.full((100, 100, 3), 128, dtype=np.uint8)
        color_roi = extract_bubble_roi(color_canvas, cx=30, cy=30, radius=8)
        assert color_roi.shape == (16, 16, 3)

        # 4. Boundary clipping: Top-Left corner breach (cx=5, cy=5, radius=10)
        # Bounding box is [-5:15, -5:15], should return 20x20 padded canvas
        tl_roi = extract_bubble_roi(canvas, cx=5, cy=5, radius=10)
        assert tl_roi.shape == (20, 20)

        # 5. Boundary clipping: Bottom-Right corner breach (cx=95, cy=95, radius=10)
        br_roi = extract_bubble_roi(canvas, cx=95, cy=95, radius=10)
        assert br_roi.shape == (20, 20)

        # 6. Error handling
        with pytest.raises(ValueError):
            extract_bubble_roi(canvas, cx=50, cy=50, radius=0)

        with pytest.raises(ValueError):
            extract_bubble_roi(canvas, cx=50, cy=50, radius=-5)

        with pytest.raises(ValueError):
            extract_bubble_roi(np.array([]), cx=50, cy=50, radius=10)

    def test_inner_circle_mask(self):
        """Step 5.2: Test inner-erosion circular mask generation."""
        # 1. 26x26 ROI with radius 13 and 20% erosion (inner radius = round(13 * 0.8) = 10)
        mask = generate_inner_circle_mask(roi_size=26, radius=13, erosion_pct=0.20)
        assert mask.shape == (26, 26)
        assert mask.dtype == np.uint8
        assert set(np.unique(mask)).issubset({0, 255})

        center_y, center_x = 13, 13
        # Center pixel must be white (255)
        assert mask[center_y, center_x] == 255

        # Pixels near outer printed ring boundary (e.g. distance = 12) must be excluded (0)
        assert mask[center_y, center_x + 12] == 0
        assert mask[center_y, center_x - 12] == 0
        assert mask[center_y + 12, center_x] == 0
        assert mask[center_y - 12, center_x] == 0

        # Pixels safely inside inner radius (e.g. distance = 5) must be 255
        assert mask[center_y, center_x + 5] == 255
        assert mask[center_y, center_x - 5] == 255

        # 2. No erosion (erosion_pct = 0.0) -> full radius
        full_mask = generate_inner_circle_mask(roi_size=20, radius=10, erosion_pct=0.0)
        assert full_mask[10, 10 + 9] == 255

        # 3. Validation errors
        with pytest.raises(ValueError):
            generate_inner_circle_mask(roi_size=0, radius=10)

        with pytest.raises(ValueError):
            generate_inner_circle_mask(roi_size=20, radius=-5)

        with pytest.raises(ValueError):
            generate_inner_circle_mask(roi_size=20, radius=10, erosion_pct=1.0)

        with pytest.raises(ValueError):
            generate_inner_circle_mask(roi_size=20, radius=10, erosion_pct=-0.1)

    def test_compute_fill_metrics(self):
        """Step 5.3: Test pixel fill density, mean intensity, and contrast metric extraction."""
        mask = generate_inner_circle_mask(roi_size=26, radius=13, erosion_pct=0.20)
        total_mask_pixels = np.count_nonzero(mask)

        # 1. 100% Fully filled bubble
        full_binary_roi = np.full((26, 26), 255, dtype=np.uint8)
        dark_gray_roi = np.full((26, 26), 20, dtype=np.uint8)  # Black ink ~20

        m_full = compute_fill_metrics(full_binary_roi, mask, dark_gray_roi)
        assert m_full["fill_density"] == 1.0
        assert m_full["filled_pixels"] == total_mask_pixels
        assert m_full["total_pixels"] == total_mask_pixels
        assert m_full["mean_intensity"] >= 0.90  # 1 - (20/255) ~ 0.92

        # 2. 0% Completely blank bubble
        blank_binary_roi = np.zeros((26, 26), dtype=np.uint8)
        white_gray_roi = np.full((26, 26), 245, dtype=np.uint8)  # Paper white ~245

        m_blank = compute_fill_metrics(blank_binary_roi, mask, white_gray_roi)
        assert m_blank["fill_density"] == 0.0
        assert m_blank["filled_pixels"] == 0
        assert m_blank["mean_intensity"] <= 0.10  # 1 - (245/255) ~ 0.04

        # 3. 50% Partially filled bubble (left half filled)
        half_binary_roi = np.zeros((26, 26), dtype=np.uint8)
        half_binary_roi[:, :13] = 255
        m_half = compute_fill_metrics(half_binary_roi, mask)
        assert 0.45 <= m_half["fill_density"] <= 0.55

        # 4. Dimension mismatch error handling
        bad_roi = np.zeros((20, 20), dtype=np.uint8)
        with pytest.raises(ValueError):
            compute_fill_metrics(bad_roi, mask)

    def test_calibrate_threshold(self):
        """Step 5.4: Test dynamic background baseline calibration from unprinted margins."""
        # 1. Clean standard paper canvas (gray = 240) -> threshold near 0.45
        clean_sheet = np.full((2339, 1654), 240, dtype=np.uint8)
        th_clean = calibrate_sheet_threshold(clean_sheet, base_threshold=0.45)
        assert abs(th_clean - 0.45) < 0.01

        # 2. Dark/underexposed paper canvas (gray = 150) -> dynamically shifted higher
        dark_sheet = np.full((2339, 1654), 150, dtype=np.uint8)
        th_dark = calibrate_sheet_threshold(dark_sheet, base_threshold=0.45)
        assert th_dark > 0.50  # 0.45 + ((240-150)/255)*0.20 ~ 0.5206

        # 3. Bright overexposed paper canvas (gray = 255) -> threshold ~ 0.438
        bright_sheet = np.full((2339, 1654), 255, dtype=np.uint8)
        th_bright = calibrate_sheet_threshold(bright_sheet, base_threshold=0.45)
        assert th_bright < 0.45

        # 4. Custom unprinted regions
        custom_regions = [(100, 100, 50, 50), (200, 200, 50, 50)]
        th_custom = calibrate_sheet_threshold(clean_sheet, unprinted_regions=custom_regions)
        assert abs(th_custom - 0.45) < 0.01

        # 5. Invalid / empty image error handling
        with pytest.raises(ValueError):
            calibrate_sheet_threshold(np.array([]))

    def test_classify_question_options(self):
        """Step 5.5: Test classification for single-mark, multi-mark, blank, and faint-mark responses."""
        # 1. Single Mark (Definitive 'B')
        metrics_single = {
            "A": {"fill_density": 0.02},
            "B": {"fill_density": 0.88},
            "C": {"fill_density": 0.01},
            "D": {"fill_density": 0.03},
        }
        opt, conf, status = classify_question_options(metrics_single, threshold=0.45)
        assert opt == "B"
        assert status == "SINGLE_MARK"
        assert conf > 0.80

        # 2. Multiple Marked ('A' and 'C' both filled)
        metrics_multi = {
            "A": {"fill_density": 0.78},
            "B": {"fill_density": 0.02},
            "C": {"fill_density": 0.82},
            "D": {"fill_density": 0.01},
        }
        opt_m, conf_m, status_m = classify_question_options(metrics_multi, threshold=0.45)
        assert opt_m is None
        assert status_m == "MULTIPLE_MARKED"

        # 3. Completely Blank
        metrics_blank = {
            "A": {"fill_density": 0.02},
            "B": {"fill_density": 0.04},
            "C": {"fill_density": 0.01},
            "D": {"fill_density": 0.03},
        }
        opt_b, conf_b, status_b = classify_question_options(metrics_blank, threshold=0.45)
        assert opt_b is None
        assert status_b == "BLANK"
        assert conf_b > 0.90

        # 4. Faint / Incomplete Mark (e.g. 0.32 fill with 0.45 threshold, faint_th = 0.27)
        metrics_faint = {
            "A": {"fill_density": 0.02},
            "B": {"fill_density": 0.01},
            "C": {"fill_density": 0.01},
            "D": {"fill_density": 0.32},
        }
        opt_f, conf_f, status_f = classify_question_options(metrics_faint, threshold=0.45)
        assert opt_f == "D"
        assert status_f == "FAINT_MARK"

        # 5. Empty metrics edge case
        assert classify_question_options({}) == (None, 0.0, "BLANK")

    def test_detect_all_sheet_bubbles_synthetic(self):
        """Step 5.6: Test end-to-end question bubble detection on synthetic OMR sheet."""
        # 1. Generate synthetic 100-question sheet with known answers
        img_sheet, meta = generate_synthetic_omr_sheet(num_questions=100, noise_level=3.0)
        rgb_scaled, gray_clahe, binary_mask, _ = preprocess_pipeline(img_sheet)
        warped_rgb, warped_binary, _ = align_pipeline(rgb_scaled, binary_mask)

        # 2. Load matching standard 100Q template
        template = TemplateConfig.load_from_json("config/template_100q.json")

        # 3. Detect all questions
        results = detect_all_sheet_bubbles(warped_binary, warped_rgb, template)
        assert len(results) == 100

        # 4. Compare with ground truth answers
        ground_truth = meta["ground_truth_answers"]
        correct_count = 0
        for q_num in range(1, 101):
            expected = ground_truth.get(str(q_num), ground_truth.get(q_num))
            detected = results[q_num]["selected_option"]
            if expected is not None:
                assert results[q_num]["status"] == "SINGLE_MARK"
                if detected == expected:
                    correct_count += 1
            else:
                assert results[q_num]["status"] == "BLANK"
                if detected is None:
                    correct_count += 1

        accuracy = correct_count / 100.0
        assert accuracy >= 0.98, f"Detection accuracy {accuracy*100:.1f}% below expected 98%"

    def test_detect_all_sheet_bubbles_blank(self):
        """Step 5.6: Test detection on a completely blank sheet."""
        blank_img, _ = generate_synthetic_omr_sheet(
            num_questions=100,
            filled_answers={q: None for q in range(1, 101)},
        )
        rgb_scaled, gray_clahe, binary_mask, _ = preprocess_pipeline(blank_img)
        warped_rgb, warped_binary, _ = align_pipeline(rgb_scaled, binary_mask)
        template = TemplateConfig.load_from_json("config/template_100q.json")

        results = detect_all_sheet_bubbles(warped_binary, warped_rgb, template)
        assert len(results) == 100
        for q_num in range(1, 101):
            assert results[q_num]["status"] == "BLANK"
            assert results[q_num]["selected_option"] is None



def test_extract_bubble_roi():
    """Standalone test entrypoint matching PROJECT.md Step 5.1 command."""
    TestBubbleDetect().test_extract_bubble_roi()


def test_inner_circle_mask():
    """Standalone test entrypoint matching PROJECT.md Step 5.2 command."""
    TestBubbleDetect().test_inner_circle_mask()


def test_compute_fill_metrics():
    """Standalone test entrypoint matching PROJECT.md Step 5.3 command."""
    TestBubbleDetect().test_compute_fill_metrics()


def test_calibrate_threshold():
    """Standalone test entrypoint matching PROJECT.md Step 5.4 command."""
    TestBubbleDetect().test_calibrate_threshold()


def test_classify_question_options():
    """Standalone test entrypoint matching PROJECT.md Step 5.5 command."""
    TestBubbleDetect().test_classify_question_options()


def test_detect_all_sheet_bubbles():
    """Standalone test entrypoint for Step 5.6 verification."""
    TestBubbleDetect().test_detect_all_sheet_bubbles_synthetic()





