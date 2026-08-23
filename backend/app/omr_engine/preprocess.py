"""
Image Ingestion & Preprocessing Pipeline for OptiScan OMR Engine.
"""

from pathlib import Path
from typing import Tuple, Union
import cv2
import numpy as np


def load_image(image_input: Union[str, Path, bytes, np.ndarray]) -> np.ndarray:
    """
    Load image from file path, raw bytes, or numpy array into 3-channel BGR image.
    """
    if isinstance(image_input, np.ndarray):
        if image_input.ndim == 2:
            return cv2.cvtColor(image_input, cv2.COLOR_GRAY2BGR)
        return image_input.copy()

    if isinstance(image_input, (str, Path)):
        path_str = str(image_input)
        img = cv2.imread(path_str)
        if img is None:
            raise ValueError(f"Failed to load image from path: {path_str}")
        return img

    if isinstance(image_input, bytes):
        nparr = np.frombuffer(image_input, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Failed to decode image from bytes buffer")
        return img

    raise TypeError(f"Unsupported image input type: {type(image_input)}")


def preprocess_pipeline(
    image_input: Union[str, Path, bytes, np.ndarray],
    target_width: int = 1654,
    clahe_clip_limit: float = 2.5,
    clahe_grid_size: Tuple[int, int] = (8, 8),
    adaptive_block_size: int = 25,
    adaptive_c: int = 10,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """
    Execute full preprocessing pipeline:
    1. Ingest image and convert to BGR.
    2. Normalize scale to standard target width.
    3. Convert to Grayscale & apply Bilateral Denoising.
    4. Apply CLAHE contrast enhancement.
    5. Generate inverted binary mask (Ink/Marks = 255, Paper = 0).

    Returns:
        tuple of (bgr_scaled, gray_clahe, binary_mask, scale_factor)
    """
    bgr_raw = load_image(image_input)
    orig_h, orig_w = bgr_raw.shape[:2]

    # Calculate uniform scale factor
    scale = float(target_width) / float(orig_w)
    target_height = int(round(orig_h * scale))
    bgr_scaled = cv2.resize(bgr_raw, (target_width, target_height), interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR)

    # Convert to Grayscale
    gray = cv2.cvtColor(bgr_scaled, cv2.COLOR_BGR2GRAY)

    # Edge-preserving Bilateral Filter
    denoised = cv2.bilateralFilter(gray, d=7, sigmaColor=50, sigmaSpace=50)

    # Contrast Limited Adaptive Histogram Equalization (CLAHE)
    clahe = cv2.createCLAHE(clipLimit=clahe_clip_limit, tileGridSize=clahe_grid_size)
    gray_clahe = clahe.apply(denoised)

    # Localized Adaptive Gaussian Thresholding (Inverted: ink=255, background=0)
    binary_mask = cv2.adaptiveThreshold(
        gray_clahe,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        adaptive_block_size if adaptive_block_size % 2 == 1 else adaptive_block_size + 1,
        adaptive_c,
    )

    return bgr_scaled, gray_clahe, binary_mask, scale
