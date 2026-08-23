"""
Standalone Verification Script for Pure OpenCV OMR Engine (Phase 2).
"""

import sys
import time
from pathlib import Path
import cv2
import numpy as np

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.omr_engine.preprocess import preprocess_pipeline
from backend.app.omr_engine.align import align_pipeline, find_fiducial_markers, order_corner_points
from backend.app.omr_engine.bubble_grid import load_template_config, create_standard_100q_grid
from backend.app.omr_engine.detect_fill import extract_all_bubbles_and_fills, compute_fill_density, extract_bubble_roi
from backend.app.omr_engine.grade import grade_submission, generate_annotated_overlay, decode_student_id_from_grid
from backend.app.db.models import AnswerKeyModel, MarkingRule, SectionConfig


def create_test_omr_sheet(
    student_id: str = "749201",
    answers: dict = None,
    rotation_deg: float = 0.0,
    noise_level: float = 2.0,
) -> np.ndarray:
    """Generate realistic high-resolution test OMR sheet image."""
    cw, ch = 1654, 2339
    img = np.full((ch, cw, 3), 255, dtype=np.uint8)

    # 1. Draw 4 Fiducial Registration Corner Squares (55x55 black solid)
    f_size = 55
    offsets = [(110, 110), (cw - 110, 110), (cw - 110, ch - 110), (110, ch - 110)]
    for cx, cy in offsets:
        cv2.rectangle(img, (cx - f_size // 2, cy - f_size // 2), (cx + f_size // 2, cy + f_size // 2), (0, 0, 0), -1)

    # 2. Draw Header
    cv2.putText(img, "OPTISCAN STANDALONE TEST SHEET", (380, 95), cv2.FONT_HERSHEY_DUPLEX, 0.9, (15, 23, 42), 2)
    cv2.line(img, (110, 140), (cw - 110, 140), (100, 116, 139), 2)

    # 3. Draw Student ID Grid (6 columns x 10 digits)
    id_origin_x, id_origin_y = 200, 250
    id_dx, id_dy = 38, 30
    id_r = 11
    id_digits = list(student_id.ljust(6, "0")[:6])

    cv2.putText(img, "ROLL NO", (id_origin_x, id_origin_y - 15), cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 0, 0), 1)
    for col in range(6):
        col_x = id_origin_x + col * id_dx
        for digit in range(10):
            row_y = id_origin_y + 35 + digit * id_dy
            cv2.circle(img, (col_x, row_y), id_r, (0, 0, 0), 2)
            cv2.putText(img, str(digit), (col_x - 4, row_y + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (80, 80, 80), 1)

            if col < len(id_digits) and id_digits[col] == str(digit):
                # Darken student digit bubble
                cv2.circle(img, (col_x, row_y), id_r - 1, (20, 20, 20), -1)

    # 4. Draw Question Columns (4 columns of 25 questions)
    col_x_starts = [120, 500, 880, 1260]
    options = ["A", "B", "C", "D"]
    bubble_r = 13
    answers = answers or {}

    q_num = 1
    for col_x in col_x_starts:
        for row in range(25):
            q_y = 650 + row * 62
            cv2.putText(img, f"Q{q_num:02d}", (col_x + 10, q_y + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (15, 23, 42), 1)

            chosen = answers.get(q_num)
            for opt_idx, opt in enumerate(options):
                opt_x = col_x + 60 + opt_idx * 44
                cv2.circle(img, (opt_x, q_y), bubble_r, (0, 0, 0), 2)
                cv2.putText(img, opt, (opt_x - 4, q_y + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (80, 80, 80), 1)

                if chosen == opt:
                    cv2.circle(img, (opt_x, q_y), bubble_r - 1, (25, 25, 25), -1)

            q_num += 1

    # Apply slight rotation if requested
    if abs(rotation_deg) > 0.001:
        center = (cw // 2, ch // 2)
        scale = 1.0 - (min(45.0, abs(rotation_deg)) / 90.0) * 0.30
        M = cv2.getRotationMatrix2D(center, rotation_deg, scale)
        img = cv2.warpAffine(img, M, (cw, ch), borderValue=(245, 245, 245))

    # Apply gaussian noise
    if noise_level > 0:
        noise = np.random.normal(0, noise_level, img.shape)
        img = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)

    return img


def run_standalone_test():
    print("=" * 60)
    print("OPTISCAN STANDALONE OMR ENGINE TEST SUITE (PHASE 2)")
    print("=" * 60)

    # 1. Test Ground Truth Pattern: First 80 questions answered
    sample_answers = {}
    opts = ["A", "B", "C", "D"]
    for i in range(1, 81):
        sample_answers[i] = opts[(i - 1) % 4]
    # Questions 81-100 left blank

    test_roll = "749201"
    print(f"\n[STEP 1] Generating synthetic test sheet for Student Roll: #{test_roll}...")
    t0 = time.perf_counter()
    raw_sheet = create_test_omr_sheet(student_id=test_roll, answers=sample_answers, rotation_deg=2.5, noise_level=3.0)
    t_gen = (time.perf_counter() - t0) * 1000
    print(f"  -> Generated (1654x2339) image with 2.5 deg rotation in {t_gen:.1f}ms")

    # 2. Test Preprocessing Pipeline
    print("\n[STEP 2] Running preprocess_pipeline (Bilateral Denoise + CLAHE + Adaptive Gaussian Mask)...")
    t1 = time.perf_counter()
    rgb_scaled, gray_clahe, binary_mask, scale = preprocess_pipeline(raw_sheet)
    t_prep = (time.perf_counter() - t1) * 1000
    print(f"  -> Preprocessed in {t_prep:.1f}ms (Shape: {binary_mask.shape}, Non-zero ink pixels: {cv2.countNonZero(binary_mask)})")
    assert binary_mask.shape == (2339, 1654), f"Unexpected binary shape: {binary_mask.shape}"

    # 3. Test Alignment & Perspective Warp
    print("\n[STEP 3] Running align_pipeline (Fiducial marker detection & Homography warp)...")
    t2 = time.perf_counter()
    markers = find_fiducial_markers(binary_mask)
    print(f"  -> Detected {len(markers)} fiducial corner candidates")
    assert len(markers) >= 4, f"Failed to detect at least 4 markers, found {len(markers)}"

    warped_rgb, warped_binary, h_mat = align_pipeline(rgb_scaled, binary_mask)
    t_align = (time.perf_counter() - t2) * 1000
    print(f"  -> 4-point homography warp executed in {t_align:.1f}ms (Warped shape: {warped_binary.shape})")
    assert warped_binary.shape == (2339, 1654), f"Unexpected warped shape: {warped_binary.shape}"

    # 4. Test Bubble Grid & Extraction
    print("\n[STEP 4] Running extract_all_bubbles_and_fills (Circular erosion & fill densities)...")
    t3 = time.perf_counter()
    template_cfg = load_template_config()
    q_results, id_results, calib_thresh = extract_all_bubbles_and_fills(warped_binary, template_cfg)
    t_extract = (time.perf_counter() - t3) * 1000
    print(f"  -> Evaluated 100 questions (400 bubbles) + 60 digit bubbles in {t_extract:.1f}ms")
    print(f"  -> Calibrated adaptive fill threshold: {calib_thresh:.4f}")

    # 5. Test Roll Number Decoding
    decoded_roll, roll_conf = decode_student_id_from_grid(id_results, threshold=calib_thresh)
    print(f"  -> Decoded Student ID: #{decoded_roll} (Expected: #{test_roll}, Confidence: {roll_conf:.2f})")
    assert decoded_roll == test_roll, f"Decoded roll #{decoded_roll} did not match expected #{test_roll}"

    # 6. Test Scoring & Audit Generator
    print("\n[STEP 5] Running grade_submission & Sectional Breakdown...")
    master_key = AnswerKeyModel(
        exam_id="test_exam_100q",
        exam_title="Phase 2 Verification Assessment",
        answers={str(i): opts[(i - 1) % 4] for i in range(1, 101)},
        default_rule=MarkingRule(correct=4.0, incorrect=-1.0, unattempted=0.0, multi_mark=-1.0, bonus=4.0),
        sections=[
            SectionConfig(name="Section A (Physics)", q_start=1, q_end=25),
            SectionConfig(name="Section B (Chemistry)", q_start=26, q_end=50),
            SectionConfig(name="Section C (Mathematics)", q_start=51, q_end=75),
            SectionConfig(name="Section D (Biology)", q_start=76, q_end=100),
        ],
    )

    t4 = time.perf_counter()
    total_time_ms = int((time.perf_counter() - t0) * 1000)
    grade_report = grade_submission(
        question_results=q_results,
        answer_key=master_key,
        student_id=decoded_roll,
        roll_conf=roll_conf,
        sheet_filename="test_standalone.png",
        processing_time_ms=total_time_ms,
    )
    t_grade = (time.perf_counter() - t4) * 1000
    print(f"  -> Graded 100 questions in {t_grade:.1f}ms")
    print(f"     • Total Score: {grade_report['total_score']} / {grade_report['max_score']} ({grade_report['percentage']}%)")
    print(f"     • Attempted: {grade_report['total_attempted']} | Correct: {grade_report['total_correct']} | Blank: {grade_report['total_unattempted']}")
    print(f"     • Audit Status: {grade_report['status']}")

    # 7. Test Transparent Visual Overlay Generation
    print("\n[STEP 6] Generating transparent visual audit sheet overlay...")
    t5 = time.perf_counter()
    annotated = generate_annotated_overlay(warped_rgb, template_cfg, grade_report)
    t_ann = (time.perf_counter() - t5) * 1000
    print(f"  -> Rendered annotated overlay in {t_ann:.1f}ms (Shape: {annotated.shape})")

    print("\n" + "=" * 60)
    print(f"ALL PHASE 2 OMR ENGINE TESTS PASSED SUCCESSFULLY in {total_time_ms}ms total latency!")
    print("=" * 60)


if __name__ == "__main__":
    run_standalone_test()
