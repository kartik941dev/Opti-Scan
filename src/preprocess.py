"""
Image Ingestion & Preprocessing Pipeline for OptiScan (Phase 2).
Handles multi-format ingestion (JPG, PNG, TIFF, PDF), canvas standardization,
noise suppression, localized lighting normalization (CLAHE), and adaptive binarization.
"""

from pathlib import Path
from typing import Optional, Union

import cv2
import numpy as np

from src.utils.exceptions import (
    ImageLoadError,
    ImageProcessingError,
    InvalidImageDimensionsError,
)
from src.utils.logger import get_logger

logger = get_logger("preprocess")


def load_image(
    image_input: Union[str, Path, bytes, np.ndarray],
    min_dimensions: Optional[tuple[int, int]] = (1200, 1600),
    dpi_render: int = 200,
) -> np.ndarray:
    """
    Ingest and normalize image data from multiple formats (JPG, PNG, TIFF, BMP, PDF)
    or existing numpy arrays, verifying minimum resolution constraints.

    Args:
        image_input: File path (str/Path), raw bytes, or already loaded NumPy array.
        min_dimensions: Optional (min_width, min_height) tuple to validate minimum quality.
        dpi_render: Target rendering DPI if input is a PDF document.

    Returns:
        3-channel NumPy array (uint8) in standard BGR/RGB color representation.

    Raises:
        ImageLoadError: If the file cannot be found, is corrupted, or cannot be decoded.
        InvalidImageDimensionsError: If image resolution is lower than min_dimensions.
    """
    img: Optional[np.ndarray] = None

    if isinstance(image_input, np.ndarray):
        img = image_input.copy()
        if img.ndim == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        elif img.ndim == 3 and img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        elif img.ndim != 3 or img.shape[2] != 3:
            raise ImageLoadError(
                f"Invalid image array shape: {img.shape}",
                details={"shape": img.shape},
            )

    elif isinstance(image_input, bytes):
        try:
            file_bytes = np.frombuffer(image_input, dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        except Exception as e:
            raise ImageLoadError(f"Failed to decode image from byte buffer: {e}") from e
        if img is None:
            raise ImageLoadError("Failed to decode image from byte buffer: cv2.imdecode returned None")

    elif isinstance(image_input, (str, Path)):
        path = Path(image_input)
        if not path.exists() or not path.is_file():
            raise ImageLoadError(
                f"Image file does not exist or is not a file: {path}",
                file_path=str(path),
            )

        suffix = path.suffix.lower()

        # Handle PDF documents via pypdfium2
        if suffix == ".pdf":
            try:
                import pypdfium2 as pdfium

                pdf = pdfium.PdfDocument(str(path))
                if len(pdf) == 0:
                    raise ImageLoadError(f"PDF document '{path}' contains no pages.", file_path=str(path))

                # Standard PDF point is 1/72 inch; scale to target DPI (e.g. 200 DPI -> 200/72)
                scale_factor = dpi_render / 72.0
                page = pdf[0]
                bitmap = page.render(scale=scale_factor)
                pil_img = bitmap.to_pil()
                img = cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)
            except ImageLoadError:
                raise
            except Exception as e:
                raise ImageLoadError(
                    f"Failed to render PDF page from '{path}': {e}",
                    file_path=str(path),
                ) from e

        # Handle raster images (JPG, PNG, TIFF, BMP, WebP)
        else:
            try:
                with open(path, "rb") as f:
                    file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
                img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                if img is None:
                    # Fallback to PIL in case OpenCV codec fails
                    from PIL import Image

                    with Image.open(path) as pil_img:
                        img = cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)
            except Exception as e:
                raise ImageLoadError(
                    f"Failed to load or parse image file '{path}': {e}",
                    file_path=str(path),
                ) from e

        if img is None:
            raise ImageLoadError(
                f"Failed to decode image from '{path}'. File may be corrupt or format unsupported.",
                file_path=str(path),
            )

    else:
        raise ImageLoadError(
            f"Unsupported input type for load_image: {type(image_input).__name__}",
        )

    # Validate resolution constraints
    if min_dimensions is not None:
        min_w, min_h = min_dimensions
        h, w = img.shape[:2]
        # Orientation-agnostic check: compare min/max bounds
        img_min_dim = min(w, h)
        img_max_dim = max(w, h)
        req_min_dim = min(min_w, min_h)
        req_max_dim = max(min_w, min_h)

        if img_min_dim < req_min_dim or img_max_dim < req_max_dim:
            raise InvalidImageDimensionsError(
                f"Image resolution ({w}x{h}) is below minimum requirement ({min_w}x{min_h}).",
                shape=(h, w),
                details={"width": w, "height": h, "min_width": min_w, "min_height": min_h},
            )

    logger.debug("Successfully loaded image of shape %s", img.shape)
    return img


def to_grayscale(image: np.ndarray) -> np.ndarray:
    """
    Convert an input color or multi-channel image to single-channel 8-bit grayscale.

    Args:
        image: Input image array (2D grayscale, 3-channel BGR/RGB, or 4-channel BGRA/RGBA).

    Returns:
        2D single-channel uint8 array.
    """
    if image.ndim == 2:
        return image.copy()
    if image.ndim == 3:
        if image.shape[2] == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        elif image.shape[2] == 4:
            return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    raise ImageProcessingError(
        f"Unsupported image shape for grayscale conversion: {image.shape}",
        details={"shape": image.shape},
    )


def resize_with_aspect_ratio(
    image: np.ndarray,
    target_width: int = 1654,
    target_height: Optional[int] = None,
    interpolation: int = cv2.INTER_AREA,
) -> tuple[np.ndarray, float]:
    """
    Resize an image maintaining aspect ratio to a target canvas width.

    Args:
        image: Input image array.
        target_width: Desired width in pixels (e.g. 1654 for A4 at 200 DPI).
        target_height: Optional fixed target height. If None, computed from aspect ratio.
        interpolation: OpenCV interpolation algorithm.

    Returns:
        tuple of (resized_image, scale_factor)
    """
    h, w = image.shape[:2]
    if target_height is None:
        scale = float(target_width) / float(w)
        new_h = int(round(h * scale))
        new_w = target_width
    else:
        scale_w = float(target_width) / float(w)
        scale_h = float(target_height) / float(h)
        scale = min(scale_w, scale_h)
        new_w = int(round(w * scale))
        new_h = int(round(h * scale))

    if new_w == w and new_h == h:
        return image.copy(), 1.0

    resized = cv2.resize(image, (new_w, new_h), interpolation=interpolation)
    return resized, scale


def denoise_image(
    gray_image: np.ndarray,
    method: str = "bilateral",
    d: int = 9,
    sigma_color: float = 75.0,
    sigma_space: float = 75.0,
) -> np.ndarray:
    """
    Apply edge-preserving smoothing to remove scanner/sensor noise without blurring bubble borders.

    Args:
        gray_image: 2D single-channel grayscale image.
        method: Denoising technique ('bilateral', 'gaussian', or 'median').
        d: Diameter of each pixel neighborhood for bilateral filtering.
        sigma_color: Filter sigma in the color space.
        sigma_space: Filter sigma in the coordinate space.

    Returns:
        Filtered 2D grayscale image.
    """
    if gray_image.ndim != 2:
        raise ImageProcessingError(f"denoise_image requires 2D grayscale image, got {gray_image.shape}")

    if method == "bilateral":
        return cv2.bilateralFilter(gray_image, d=d, sigmaColor=sigma_color, sigmaSpace=sigma_space)
    elif method == "gaussian":
        return cv2.GaussianBlur(gray_image, (5, 5), 0)
    elif method == "median":
        return cv2.medianBlur(gray_image, 3)
    else:
        logger.warning("Unrecognized denoising method '%s', returning original image.", method)
        return gray_image.copy()


def apply_clahe(
    gray_image: np.ndarray,
    clip_limit: float = 2.0,
    grid_size: tuple[int, int] = (8, 8),
) -> np.ndarray:
    """
    Apply Contrast Limited Adaptive Histogram Equalization (CLAHE) to normalize
    mobile camera flash gradients and localized shadows across the sheet.

    Args:
        gray_image: 2D single-channel grayscale image.
        clip_limit: Threshold for contrast limiting.
        grid_size: Size of grid for histogram equalization (tileGridSize).

    Returns:
        Contrast-equalized 2D grayscale image.
    """
    if gray_image.ndim != 2:
        raise ImageProcessingError(f"apply_clahe requires 2D grayscale image, got {gray_image.shape}")

    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=grid_size)
    return clahe.apply(gray_image)


def binarize_adaptive(
    gray_image: np.ndarray,
    block_size: int = 25,
    c_offset: int = 10,
    invert: bool = True,
    morph_kernel_size: Optional[int] = None,
) -> np.ndarray:
    """
    Convert grayscale image into a high-contrast binary mask using adaptive Gaussian thresholding,
    with optional morphological cleanup.
    By default, inverts the output so foreground ink/bubbles are 255 and background paper is 0.

    Args:
        gray_image: 2D single-channel grayscale image.
        block_size: Size of pixel neighborhood used to calculate threshold value (must be odd > 1).
        c_offset: Constant subtracted from the mean or weighted mean.
        invert: If True, uses cv2.THRESH_BINARY_INV; if False, uses cv2.THRESH_BINARY.
        morph_kernel_size: Optional integer kernel size for morphological opening to remove salt noise.

    Returns:
        Binary image mask (uint8, values 0 or 255).
    """
    if gray_image.ndim != 2:
        raise ImageProcessingError(f"binarize_adaptive requires 2D grayscale image, got {gray_image.shape}")

    # Block size must be odd and > 1
    if block_size % 2 == 0:
        block_size += 1
    if block_size < 3:
        block_size = 3

    thresh_type = cv2.THRESH_BINARY_INV if invert else cv2.THRESH_BINARY
    binary = cv2.adaptiveThreshold(
        gray_image,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        thresh_type,
        block_size,
        c_offset,
    )

    if morph_kernel_size and morph_kernel_size > 1:
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (morph_kernel_size, morph_kernel_size))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

    return binary


def preprocess_pipeline(
    image_input: Union[str, Path, np.ndarray],
    target_width: int = 1654,
    min_dimensions: Optional[tuple[int, int]] = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """
    Full end-to-end preprocessing pipeline:
    1. Ingest image from file or array (with resolution check).
    2. Resize to canonical width maintaining aspect ratio.
    3. Convert to grayscale.
    4. Apply bilateral noise filtering.
    5. Enhance localized contrast via CLAHE.
    6. Generate inverted high-contrast binary mask via adaptive thresholding.

    Args:
        image_input: File path or NumPy image array.
        target_width: Canonical standard width in pixels (default 1654 for A4 @ 200 DPI).
        min_dimensions: Optional minimum resolution constraint.

    Returns:
        tuple of:
        - resized_color_image: Standardized 3-channel image (np.ndarray)
        - clahe_enhanced_gray: Contrast-normalized grayscale image (np.ndarray)
        - binary_mask: Inverted adaptive binary mask (np.ndarray)
        - scale_factor: Rescaling ratio applied (float)
    """
    raw_img = load_image(image_input, min_dimensions=min_dimensions)
    resized_img, scale_factor = resize_with_aspect_ratio(raw_img, target_width=target_width)
    gray = to_grayscale(resized_img)
    denoised = denoise_image(gray, method="bilateral")
    clahe_gray = apply_clahe(denoised)
    binary_mask = binarize_adaptive(clahe_gray)

    logger.debug(
        "Preprocessing complete. Resized shape: %s, Scale factor: %.4f",
        resized_img.shape,
        scale_factor,
    )
    return resized_img, clahe_gray, binary_mask, scale_factor
