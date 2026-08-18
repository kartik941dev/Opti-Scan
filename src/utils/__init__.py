"""
Utility modules for logging, exceptions, and helpers.
"""

from src.utils.exceptions import (
    AlignmentError,
    BubbleDetectionError,
    EvaluationError,
    FiducialMarkerNotFoundError,
    ImageLoadError,
    ImageProcessingError,
    InvalidImageDimensionsError,
    MaskGenerationError,
    OptiScanException,
    PerspectiveWarpError,
    ScoringError,
    StudentIdParsingError,
    TemplateError,
    TemplateMismatchError,
)
from src.utils.logger import OptiScanFormatter, get_logger

__all__ = [
    "OptiScanException",
    "ImageProcessingError",
    "ImageLoadError",
    "InvalidImageDimensionsError",
    "AlignmentError",
    "FiducialMarkerNotFoundError",
    "PerspectiveWarpError",
    "TemplateError",
    "TemplateMismatchError",
    "BubbleDetectionError",
    "MaskGenerationError",
    "EvaluationError",
    "ScoringError",
    "StudentIdParsingError",
    "OptiScanFormatter",
    "get_logger",
]

