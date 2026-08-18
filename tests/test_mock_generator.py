"""
Unit tests for the synthetic OMR generator fixture.
"""

from pathlib import Path

import cv2
import numpy as np
import pytest

from tests.fixtures.generate_mock_omr import generate_synthetic_omr_sheet


class TestSyntheticOMRGenerator:
    def test_generate_clean_sheet_dimensions(self):
        img, metadata = generate_synthetic_omr_sheet(num_questions=100)
        
        assert isinstance(img, np.ndarray)
        assert img.shape == (2339, 1654, 3)
        assert img.dtype == np.uint8
        assert metadata["total_questions"] == 100
        assert len(metadata["questions_layout"]) == 100
        assert metadata["format"] == "OptiScan_A4_100Q"
        assert len(metadata["fiducial_markers"]) == 4

    def test_custom_answers_and_student_id(self):
        custom_answers = {1: "A", 2: "B", 3: "C", 4: "D", 50: "A", 100: "D"}
        custom_id = "987654"

        img, metadata = generate_synthetic_omr_sheet(
            num_questions=100,
            filled_answers=custom_answers,
            student_id=custom_id,
        )

        assert metadata["student_id"] == custom_id
        for q_num, ans in custom_answers.items():
            assert metadata["ground_truth_answers"][str(q_num)] == ans

    def test_marker_pixels_are_black(self):
        img, metadata = generate_synthetic_omr_sheet(num_questions=100)
        tl_marker = metadata["fiducial_markers"]["top_left"]
        
        # Center pixel of Top-Left marker should be pure black (0, 0, 0)
        cx = tl_marker["x"] + tl_marker["w"] // 2
        cy = tl_marker["y"] + tl_marker["h"] // 2
        pixel_val = img[cy, cx]
        
        assert np.array_equal(pixel_val, [0, 0, 0])

    def test_rotations_and_distortions(self):
        img_rot, meta_rot = generate_synthetic_omr_sheet(
            num_questions=50,
            rotation_deg=15.0,
            noise_level=10.0,
            shadow_intensity=0.5,
        )
        assert img_rot.shape == (2339, 1654, 3)
        assert meta_rot["distortions"]["rotation_deg"] == 15.0
        assert meta_rot["distortions"]["noise_level"] == 10.0
        assert meta_rot["distortions"]["shadow_intensity"] == 0.5

    def test_save_to_disk(self, tmp_path: Path):
        img_path = tmp_path / "test_omr.png"
        json_path = tmp_path / "test_omr.json"

        img, meta = generate_synthetic_omr_sheet(
            num_questions=100,
            output_path=img_path,
            ground_truth_path=json_path,
        )

        assert img_path.exists()
        assert json_path.exists()
        
        # Read back saved image to verify validity
        loaded_img = cv2.imread(str(img_path))
        assert loaded_img is not None
        assert loaded_img.shape == (2339, 1654, 3)
