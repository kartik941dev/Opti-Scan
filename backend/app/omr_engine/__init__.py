"""
OptiScan Pure Computer Vision OMR Engine Package.
"""

from backend.app.omr_engine.preprocess import load_image, preprocess_pipeline
from backend.app.omr_engine.align import align_pipeline, find_fiducial_markers, order_corner_points
from backend.app.omr_engine.bubble_grid import create_standard_100q_grid, load_template_config
from backend.app.omr_engine.detect_fill import (
    extract_bubble_roi,
    compute_fill_density,
    calibrate_threshold,
    classify_question_bubbles,
    extract_all_bubbles_and_fills,
)
from backend.app.omr_engine.grade import (
    decode_student_id_from_grid,
    grade_submission,
    generate_annotated_overlay,
)

__all__ = [
    "load_image",
    "preprocess_pipeline",
    "align_pipeline",
    "find_fiducial_markers",
    "order_corner_points",
    "create_standard_100q_grid",
    "load_template_config",
    "extract_bubble_roi",
    "compute_fill_density",
    "calibrate_threshold",
    "classify_question_bubbles",
    "extract_all_bubbles_and_fills",
    "decode_student_id_from_grid",
    "grade_submission",
    "generate_annotated_overlay",
]
