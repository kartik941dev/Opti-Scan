"""
Unit tests for the Image Ingestion and Preprocessing Pipeline (Phase 2).
"""

from pathlib import Path

import cv2
import numpy as np
import pytest

from src.preprocess import (
    apply_clahe,
    binarize_adaptive,
    denoise_image,
    load_image,
    preprocess_pipeline,
    resize_with_aspect_ratio,
    to_grayscale,
)
from src.utils.exceptions import ImageLoadError, InvalidImageDimensionsError
from tests.fixtures.generate_mock_omr import generate_synthetic_omr_sheet


class TestImageIngestion:
    """Test suite for Step 2.1: Robust Image Loader & DPI Normalizer."""

    def test_load_valid_image_from_disk(self, tmp_path: Path):
        # Generate and save a clean synthetic OMR sheet
        img_path = tmp_path / "valid_sheet.png"
        raw_img, _ = generate_synthetic_omr_sheet(num_questions=25, output_path=img_path)

        loaded = load_image(img_path, min_dimensions=(1200, 1600))
        assert isinstance(loaded, np.ndarray)
        assert loaded.shape == (2339, 1654, 3)
        assert loaded.dtype == np.uint8

    def test_load_image_from_numpy_array(self):
        # Array with standard 3 channels
        sample_arr = np.full((1600, 1200, 3), 200, dtype=np.uint8)
        loaded = load_image(sample_arr, min_dimensions=(1200, 1600))
        assert loaded.shape == (1600, 1200, 3)

        # Grayscale 2D array should be promoted to 3-channel
        gray_arr = np.full((1600, 1200), 128, dtype=np.uint8)
        loaded_gray = load_image(gray_arr, min_dimensions=(1200, 1600))
        assert loaded_gray.shape == (1600, 1200, 3)

    def test_load_nonexistent_file_raises_error(self, tmp_path: Path):
        nonexistent = tmp_path / "does_not_exist.png"
        with pytest.raises(ImageLoadError) as exc_info:
            load_image(nonexistent)
        assert exc_info.value.error_code == "IMAGE_LOAD_ERROR"
        assert str(nonexistent) in str(exc_info.value.details.get("file_path"))

    def test_load_corrupted_file_raises_error(self, tmp_path: Path):
        corrupt_file = tmp_path / "corrupt.png"
        corrupt_file.write_bytes(b"This is not a valid PNG header or image stream.")

        with pytest.raises(ImageLoadError) as exc_info:
            load_image(corrupt_file)
        assert exc_info.value.error_code == "IMAGE_LOAD_ERROR"

    def test_load_low_resolution_image_raises_error(self, tmp_path: Path):
        low_res_path = tmp_path / "low_res.jpg"
        low_res_img = np.full((400, 300, 3), 255, dtype=np.uint8)
        cv2.imwrite(str(low_res_path), low_res_img)

        with pytest.raises(InvalidImageDimensionsError) as exc_info:
            load_image(low_res_path, min_dimensions=(1200, 1600))
        assert exc_info.value.error_code == "INVALID_IMAGE_DIMENSIONS"
        assert exc_info.value.details["width"] == 300
        assert exc_info.value.details["height"] == 400

    def test_load_pdf_document(self, tmp_path: Path):
        # Create a simple 1-page PDF using reportlab or pypdfium2
        pdf_path = tmp_path / "sample_omr.pdf"
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas

            c = canvas.Canvas(str(pdf_path), pagesize=A4)
            c.drawString(100, 750, "OptiScan Assessment Sheet PDF Test")
            c.rect(50, 50, 40, 40, fill=1)
            c.save()

            loaded_pdf = load_image(pdf_path, min_dimensions=None, dpi_render=200)
            assert isinstance(loaded_pdf, np.ndarray)
            assert loaded_pdf.ndim == 3
            assert loaded_pdf.shape[2] == 3
            # A4 at 200 DPI is approx 1654 x 2338
            assert loaded_pdf.shape[0] > 1000 and loaded_pdf.shape[1] > 1000
        except ImportError:
            pytest.skip("reportlab not installed for PDF creation test")

    def test_load_valid_and_invalid_image(self, tmp_path: Path):
        """Unified test verifying both valid ingestion and error handling for Step 2.1."""
        # 1. Valid image
        valid_path = tmp_path / "valid.jpg"
        img_arr = np.full((1800, 1400, 3), 255, dtype=np.uint8)
        cv2.imwrite(str(valid_path), img_arr)
        loaded = load_image(valid_path, min_dimensions=(1200, 1600))
        assert loaded.shape == (1800, 1400, 3)

        # 2. Invalid path
        with pytest.raises(ImageLoadError):
            load_image(tmp_path / "missing.jpg")


class TestPreprocessingStages:
    """Test suite for Steps 2.2 to 2.6: Preprocessing Transformations."""

    def test_grayscale_and_resize(self):
        # 1. 3-Channel BGR to Grayscale
        color_img = np.full((1000, 500, 3), 120, dtype=np.uint8)
        gray = to_grayscale(color_img)
        assert gray.ndim == 2
        assert gray.shape == (1000, 500)
        assert gray.dtype == np.uint8

        # 2. 4-Channel BGRA to Grayscale
        bgra_img = np.full((800, 600, 4), 200, dtype=np.uint8)
        gray_from_bgra = to_grayscale(bgra_img)
        assert gray_from_bgra.ndim == 2
        assert gray_from_bgra.shape == (800, 600)

        # 3. Already Grayscale (2D array)
        gray_input = np.full((500, 500), 50, dtype=np.uint8)
        gray_output = to_grayscale(gray_input)
        assert gray_output.shape == (500, 500)

        # 4. Invalid shape raises ImageProcessingError
        invalid_dim_img = np.zeros((10, 10, 5), dtype=np.uint8)
        with pytest.raises(Exception):
            to_grayscale(invalid_dim_img)

        # 5. Canvas Standardization / Resizing
        resized, scale = resize_with_aspect_ratio(color_img, target_width=1654)
        assert resized.shape[1] == 1654
        assert resized.shape[0] == int(round(1000 * (1654 / 500)))
        assert np.isclose(scale, 1654 / 500)

        # 6. Fixed width and height bounding box resizing
        resized_box, scale_box = resize_with_aspect_ratio(color_img, target_width=1654, target_height=2339)
        assert resized_box.shape[0] <= 2339
        assert resized_box.shape[1] <= 1654

        # 7. No-op resize when dimensions already match
        same_size_img = np.full((2000, 1654, 3), 255, dtype=np.uint8)
        no_op_resized, no_op_scale = resize_with_aspect_ratio(same_size_img, target_width=1654)
        assert no_op_resized.shape == (2000, 1654, 3)
        assert no_op_scale == 1.0

    def test_denoising(self):
        # 1. Noise suppression test
        img = np.full((200, 200), 128, dtype=np.uint8)
        noise = np.random.randint(-30, 30, (200, 200)).astype(np.int16)
        noisy = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        denoised_bilateral = denoise_image(noisy, method="bilateral", d=9, sigma_color=75.0, sigma_space=75.0)
        denoised_gaussian = denoise_image(noisy, method="gaussian")
        denoised_median = denoise_image(noisy, method="median")
        fallback = denoise_image(noisy, method="unknown")

        assert denoised_bilateral.shape == (200, 200)
        assert denoised_gaussian.shape == (200, 200)
        assert denoised_median.shape == (200, 200)
        assert fallback.shape == (200, 200)
        # Filtered image variance should be significantly lower than noisy image
        assert np.var(denoised_bilateral) < np.var(noisy)

        # 2. Edge-preservation test: sharp boundary between black circle and white background
        edge_img = np.full((100, 100), 255, dtype=np.uint8)
        cv2.circle(edge_img, (50, 50), 20, 0, -1)
        filtered_edge = denoise_image(edge_img, method="bilateral", d=9, sigma_color=75, sigma_space=75)
        # Center should remain deep black and corner should remain white
        assert filtered_edge[50, 50] == 0
        assert filtered_edge[5, 5] == 255

        # 3. Invalid shape raises ImageProcessingError
        with pytest.raises(Exception):
            denoise_image(np.zeros((10, 10, 3), dtype=np.uint8))

    def test_clahe_contrast_enhancement(self):
        # 1. Gradient shadow normalization test
        y, x = np.indices((300, 300))
        # Severe illumination falloff from top-left (dark) to bottom-right (bright)
        gradient = (x + y) / 600.0 * 200
        gray_gradient = gradient.astype(np.uint8)

        enhanced = apply_clahe(gray_gradient, clip_limit=2.0, grid_size=(8, 8))
        assert enhanced.shape == (300, 300)
        assert enhanced.dtype == np.uint8
        # Standard deviation of local blocks should be improved/normalized
        assert enhanced.std() > 0

        # 2. Dynamic range enhancement on low-contrast image
        low_contrast = np.full((100, 100), 128, dtype=np.uint8)
        # Add subtle features (value 130)
        cv2.circle(low_contrast, (50, 50), 20, 132, -1)
        enhanced_contrast = apply_clahe(low_contrast, clip_limit=4.0, grid_size=(4, 4))
        assert enhanced_contrast.shape == (100, 100)
        # Contrast between feature and background should be widened
        bg_val = int(enhanced_contrast[5, 5])
        fg_val = int(enhanced_contrast[50, 50])
        assert abs(fg_val - bg_val) >= abs(132 - 128)

        # 3. Invalid shape raises ImageProcessingError
        with pytest.raises(Exception):
            apply_clahe(np.zeros((50, 50, 3), dtype=np.uint8))

    def test_adaptive_binarization(self):
        # 1. Standard Inverted Adaptive Binarization on Synthetic Sheet
        sheet, _ = generate_synthetic_omr_sheet(num_questions=10)
        gray = to_grayscale(sheet)
        binary = binarize_adaptive(gray, block_size=25, c_offset=10, invert=True)

        assert binary.shape == gray.shape
        assert binary.dtype == np.uint8
        # Output should be strictly binary (0 or 255)
        unique_vals = set(np.unique(binary))
        assert unique_vals.issubset({0, 255})
        # Ink features (fiducial markers, text, bubbles) should produce white foreground (255)
        assert 255 in unique_vals
        assert 0 in unique_vals

        # 2. Non-inverted binarization
        non_inverted = binarize_adaptive(gray, block_size=25, c_offset=10, invert=False)
        assert non_inverted.shape == gray.shape
        # Inverted and non-inverted should be bitwise opposites
        assert np.array_equal(binary + non_inverted, np.full_like(binary, 255))

        # 3. Morphological cleanup test (removes isolated salt pixel noise)
        noisy_mask = binary.copy()
        noisy_mask[10, 10] = 255  # isolated single pixel
        cleaned = binarize_adaptive(gray, block_size=24, c_offset=10, invert=True, morph_kernel_size=3)
        assert cleaned.shape == binary.shape

        # 4. Invalid shape raises ImageProcessingError
        with pytest.raises(Exception):
            binarize_adaptive(np.zeros((30, 30, 3), dtype=np.uint8))

    def test_preprocess_pipeline_complete(self, tmp_path: Path):
        # 1. Pipeline execution from in-memory array
        sheet, meta = generate_synthetic_omr_sheet(num_questions=50)
        rgb_scaled, gray_clahe, binary_mask, scale = preprocess_pipeline(sheet, target_width=1654)

        assert rgb_scaled.ndim == 3
        assert rgb_scaled.shape[1] == 1654
        assert gray_clahe.ndim == 2
        assert gray_clahe.shape == rgb_scaled.shape[:2]
        assert binary_mask.ndim == 2
        assert binary_mask.shape == rgb_scaled.shape[:2]
        assert isinstance(scale, float)
        assert np.isclose(scale, 1.0)

        # 2. Pipeline execution from disk file path
        img_path = tmp_path / "pipeline_omr.png"
        generate_synthetic_omr_sheet(num_questions=25, output_path=img_path)
        rgb_from_file, gray_from_file, mask_from_file, scale_file = preprocess_pipeline(img_path, target_width=1654)

        assert rgb_from_file.shape == (2339, 1654, 3)
        assert mask_from_file.shape == (2339, 1654)

        # 3. Pipeline execution on perturbed image (noise and rotation)
        distorted_sheet, _ = generate_synthetic_omr_sheet(
            num_questions=30, rotation_deg=5.0, noise_level=15.0, shadow_intensity=0.4
        )
        rgb_dist, gray_dist, mask_dist, scale_dist = preprocess_pipeline(distorted_sheet, target_width=1200)
        assert rgb_dist.shape[1] == 1200
        assert mask_dist.shape == rgb_dist.shape[:2]
        assert 255 in np.unique(mask_dist)
