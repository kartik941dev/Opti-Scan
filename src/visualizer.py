"""
Visual Audit Overlays & Annotation Renderer for OptiScan (Phase 7).
Renders color-coded indicators, transparency blends, and scorecard banners.
"""

from typing import Any, Optional, Union

import cv2
import numpy as np

from src.utils.logger import get_logger

logger = get_logger("visualizer")

# Standard BGR color palette
COLOR_CORRECT = (34, 177, 76)       # Green
COLOR_INCORRECT = (36, 28, 237)     # Red
COLOR_KEY = (232, 162, 0)           # Cyan/Blue (correct key hint)
COLOR_AMBER = (0, 140, 255)         # Amber/Orange (ambiguity / faint / multi-mark)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)


def overlay_transparent_circle(
    image: np.ndarray,
    cx: int,
    cy: int,
    radius: int,
    color_bgr: tuple[int, int, int],
    alpha: float = 0.40,
    outline_thickness: int = 2,
) -> np.ndarray:
    """
    Draw a semi-transparent filled circle with a crisp solid outline.

    Args:
        image: BGR canvas array (modified in-place or returned).
        cx: Center X coordinate.
        cy: Center Y coordinate.
        radius: Circle radius in pixels.
        color_bgr: BGR tuple (e.g. (34, 177, 76)).
        alpha: Transparency weight (0.0 to 1.0).
        outline_thickness: Thickness of outer solid boundary ring.

    Returns:
        Annotated BGR image array.
    """
    if image is None or image.size == 0:
        raise ValueError("Image array cannot be None or empty")

    img_bgr = image if image.ndim == 3 else cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    overlay = img_bgr.copy()

    # Draw solid fill on overlay layer
    cv2.circle(overlay, (cx, cy), radius, color_bgr, -1, lineType=cv2.LINE_AA)
    # Blend overlay with base image
    cv2.addWeighted(overlay, alpha, img_bgr, 1.0 - alpha, 0, img_bgr)

    # Draw crisp solid boundary outline
    if outline_thickness > 0:
        cv2.circle(img_bgr, (cx, cy), radius + 1, color_bgr, outline_thickness, lineType=cv2.LINE_AA)

    return img_bgr


def draw_correct_indicator(
    img: np.ndarray,
    cx: int,
    cy: int,
    r: int,
    alpha: float = 0.45,
) -> np.ndarray:
    """
    Draw green check / green semi-transparent indicator for a correct answer bubble.
    """
    img = overlay_transparent_circle(img, cx, cy, r, COLOR_CORRECT, alpha=alpha, outline_thickness=2)
    # Draw small green check mark in center
    pts = np.array([
        [cx - int(r * 0.4), cy],
        [cx - int(r * 0.1), cy + int(r * 0.35)],
        [cx + int(r * 0.45), cy - int(r * 0.35)],
    ], dtype=np.int32)
    cv2.polylines(img, [pts], isClosed=False, color=COLOR_CORRECT, thickness=2, lineType=cv2.LINE_AA)
    return img


def draw_incorrect_indicator(
    img: np.ndarray,
    cx: int,
    cy: int,
    r: int,
    alpha: float = 0.45,
) -> np.ndarray:
    """
    Draw red cross / red semi-transparent indicator for an incorrect answer bubble.
    """
    img = overlay_transparent_circle(img, cx, cy, r, COLOR_INCORRECT, alpha=alpha, outline_thickness=2)
    # Draw red 'X'
    offset = int(r * 0.35)
    cv2.line(img, (cx - offset, cy - offset), (cx + offset, cy + offset), COLOR_INCORRECT, 2, cv2.LINE_AA)
    cv2.line(img, (cx - offset, cy + offset), (cx + offset, cy - offset), COLOR_INCORRECT, 2, cv2.LINE_AA)
    return img


def draw_key_indicator(
    img: np.ndarray,
    cx: int,
    cy: int,
    r: int,
    alpha: float = 0.35,
) -> np.ndarray:
    """
    Draw cyan / blue target outline showing the ground-truth correct bubble.
    """
    img = overlay_transparent_circle(img, cx, cy, r + 2, COLOR_KEY, alpha=alpha, outline_thickness=2)
    # Draw central target dot
    cv2.circle(img, (cx, cy), 3, COLOR_KEY, -1, cv2.LINE_AA)
    return img


def draw_amber_flag(
    img: np.ndarray,
    cx: int,
    cy: int,
    r: int,
    alpha: float = 0.45,
) -> np.ndarray:
    """
    Draw amber / orange warning indicator for ambiguous multi-marks or faint marks.
    """
    img = overlay_transparent_circle(img, cx, cy, r, COLOR_AMBER, alpha=alpha, outline_thickness=2)
    # Draw '!' exclamation mark
    cv2.line(img, (cx, cy - int(r * 0.4)), (cx, cy + int(r * 0.1)), COLOR_AMBER, 2, cv2.LINE_AA)
    cv2.circle(img, (cx, cy + int(r * 0.35)), 1, COLOR_AMBER, -1, cv2.LINE_AA)
    return img


def draw_header_scorecard(
    image: np.ndarray,
    evaluation_result: dict[str, Any],
    pos: Optional[tuple[int, int, int, int]] = None,
) -> np.ndarray:
    """
    Render a sleek, semi-transparent scorecard banner on the canvas header.

    Args:
        image: BGR canvas image array.
        evaluation_result: Comprehensive scoring report dictionary.
        pos: Optional bounding box (x, y, w, h). If None, computes optimal default placement.

    Returns:
        Annotated BGR canvas with scorecard banner.
    """
    if image is None or image.size == 0:
        raise ValueError("Image array cannot be None or empty")

    img = image if image.ndim == 3 else cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    canvas_h, canvas_w = img.shape[:2]

    # Calculate scorecard box bounds
    if pos is not None:
        bx, by, bw, bh = pos
    else:
        # Optimal positioning for canonical A4 (1654x2339) or proportional
        bw = min(880, int(canvas_w * 0.54))
        bh = min(350, int(canvas_h * 0.155))
        bx = max(20, canvas_w - bw - int(canvas_w * 0.07))
        by = int(canvas_h * 0.098)

    # Extract score details
    student_id = str(evaluation_result.get("student_id", "UNKNOWN"))
    exam_id = str(evaluation_result.get("exam_id", evaluation_result.get("exam_title", "OMR EXAM")))
    total_score = float(evaluation_result.get("total_score", 0.0))
    max_score = float(evaluation_result.get("max_score", 0.0))
    percentage = float(evaluation_result.get("percentage", 0.0))
    accuracy_pct = float(evaluation_result.get("accuracy_pct", 0.0))
    counts = evaluation_result.get("counts", {})

    correct_cnt = counts.get("correct", 0)
    incorrect_cnt = counts.get("incorrect", 0)
    blank_cnt = counts.get("blank", 0)
    multi_cnt = counts.get("multiple_marked", 0)
    faint_cnt = counts.get("faint_marked", 0)
    flagged_cnt = multi_cnt + faint_cnt

    # Accent color based on percentage performance
    if percentage >= 75.0:
        accent_color = COLOR_CORRECT
        grade_label = "EXCELLENT"
    elif percentage >= 50.0:
        accent_color = (0, 180, 255)  # Gold/Amber
        grade_label = "GOOD"
    elif percentage >= 35.0:
        accent_color = COLOR_AMBER
        grade_label = "QUALIFIED"
    else:
        accent_color = COLOR_INCORRECT
        grade_label = "NEEDS IMPROVEMENT"

    # 1. Dark frosted glass background card
    overlay = img.copy()
    bg_color = (25, 30, 40)  # Sleek dark navy slate
    cv2.rectangle(overlay, (bx, by), (bx + bw, by + bh), bg_color, -1)
    cv2.addWeighted(overlay, 0.88, img, 0.12, 0, img)

    # 2. Border and Top Accent Strip
    cv2.rectangle(img, (bx, by), (bx + bw, by + bh), (60, 70, 90), 2, lineType=cv2.LINE_AA)
    cv2.rectangle(img, (bx, by), (bx + bw, by + 10), accent_color, -1)

    # 3. Card Title & Student ID
    title_text = "OPTISCAN AUDIT SCORECARD"
    cv2.putText(img, title_text, (bx + 25, by + 40), cv2.FONT_HERSHEY_DUPLEX, 0.75, COLOR_WHITE, 2, cv2.LINE_AA)

    # Grade Badge Pill
    badge_text = f"[{grade_label}]"
    cv2.putText(img, badge_text, (bx + bw - 200, by + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.65, accent_color, 2, cv2.LINE_AA)

    # Divider line
    cv2.line(img, (bx + 25, by + 55), (bx + bw - 25, by + 55), (70, 80, 100), 1, cv2.LINE_AA)

    # 4. Student & Exam Info
    id_line = f"Student ID: {student_id}   |   Exam: {exam_id[:24]}"
    cv2.putText(img, id_line, (bx + 25, by + 85), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (200, 210, 225), 1, cv2.LINE_AA)

    # 5. Score Highlight Banner
    score_str = f"Score: {total_score:+.1f} / {max_score:.1f}"
    pct_str = f"({percentage:.1f}%)"
    cv2.putText(img, score_str, (bx + 25, by + 135), cv2.FONT_HERSHEY_DUPLEX, 1.05, COLOR_WHITE, 2, cv2.LINE_AA)
    cv2.putText(img, pct_str, (bx + 370, by + 135), cv2.FONT_HERSHEY_DUPLEX, 0.9, accent_color, 2, cv2.LINE_AA)

    # 6. Metric Badges Box
    badge_y = by + 185
    col_w = (bw - 50) // 4

    # Correct Badge
    cv2.rectangle(img, (bx + 25, badge_y - 25), (bx + 25 + col_w - 10, badge_y + 35), (35, 45, 55), -1)
    cv2.rectangle(img, (bx + 25, badge_y - 25), (bx + 25 + col_w - 10, badge_y + 35), COLOR_CORRECT, 1, cv2.LINE_AA)
    cv2.putText(img, "CORRECT", (bx + 35, badge_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (160, 175, 190), 1, cv2.LINE_AA)
    cv2.putText(img, str(correct_cnt), (bx + 35, badge_y + 25), cv2.FONT_HERSHEY_DUPLEX, 0.8, COLOR_CORRECT, 2, cv2.LINE_AA)

    # Incorrect Badge
    c2_x = bx + 25 + col_w
    cv2.rectangle(img, (c2_x, badge_y - 25), (c2_x + col_w - 10, badge_y + 35), (35, 45, 55), -1)
    cv2.rectangle(img, (c2_x, badge_y - 25), (c2_x + col_w - 10, badge_y + 35), COLOR_INCORRECT, 1, cv2.LINE_AA)
    cv2.putText(img, "INCORRECT", (c2_x + 10, badge_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (160, 175, 190), 1, cv2.LINE_AA)
    cv2.putText(img, str(incorrect_cnt), (c2_x + 10, badge_y + 25), cv2.FONT_HERSHEY_DUPLEX, 0.8, COLOR_INCORRECT, 2, cv2.LINE_AA)

    # Blank Badge
    c3_x = bx + 25 + 2 * col_w
    cv2.rectangle(img, (c3_x, badge_y - 25), (c3_x + col_w - 10, badge_y + 35), (35, 45, 55), -1)
    cv2.rectangle(img, (c3_x, badge_y - 25), (c3_x + col_w - 10, badge_y + 35), (140, 150, 165), 1, cv2.LINE_AA)
    cv2.putText(img, "BLANK", (c3_x + 10, badge_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (160, 175, 190), 1, cv2.LINE_AA)
    cv2.putText(img, str(blank_cnt), (c3_x + 10, badge_y + 25), cv2.FONT_HERSHEY_DUPLEX, 0.8, (210, 220, 230), 2, cv2.LINE_AA)

    # Flagged Badge
    c4_x = bx + 25 + 3 * col_w
    cv2.rectangle(img, (c4_x, badge_y - 25), (c4_x + col_w - 10, badge_y + 35), (35, 45, 55), -1)
    cv2.rectangle(img, (c4_x, badge_y - 25), (c4_x + col_w - 10, badge_y + 35), COLOR_AMBER, 1, cv2.LINE_AA)
    cv2.putText(img, "FLAGGED", (c4_x + 10, badge_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (160, 175, 190), 1, cv2.LINE_AA)
    cv2.putText(img, str(flagged_cnt), (c4_x + 10, badge_y + 25), cv2.FONT_HERSHEY_DUPLEX, 0.8, COLOR_AMBER, 2, cv2.LINE_AA)

    # 7. Sectional Summary / Accuracy Footer
    footer_y = by + bh - 25
    accuracy_str = f"Accuracy: {accuracy_pct:.1f}%"
    sec_scores = evaluation_result.get("sectional_scores", {})
    if sec_scores and isinstance(sec_scores, dict):
        sec_parts = [f"{s_name[:12]}: {s_data.get('score', 0):.0f}/{s_data.get('max_score', 0):.0f}" for s_name, s_data in list(sec_scores.items())[:2]]
        footer_str = f"{accuracy_str}   |   " + "  ".join(sec_parts)
    else:
        attempted_cnt = counts.get("attempted", correct_cnt + incorrect_cnt)
        footer_str = f"{accuracy_str}   |   Attempted: {attempted_cnt} / {counts.get('total_questions', correct_cnt + incorrect_cnt + blank_cnt)}"

    cv2.putText(img, footer_str, (bx + 25, footer_y), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (170, 185, 205), 1, cv2.LINE_AA)

    return img


def generate_annotated_sheet(
    warped_rgb: np.ndarray,
    evaluation_result: dict[str, Any],
    template: Any,
    draw_scorecard: bool = True,
    alpha: float = 0.45,
) -> np.ndarray:
    """
    Generate a full-sheet visual audit overlay with color-coded bubble annotations
    and an executive header scorecard.

    Args:
        warped_rgb: Aligned canonical sheet image (RGB or BGR numpy array, or grayscale).
        evaluation_result: Output report dictionary from scorer.score_student_sheet.
        template: TemplateConfig instance defining question bubble coordinates.
        draw_scorecard: Whether to stamp the top executive scorecard banner.
        alpha: Transparency blend weight for bubble overlays (0.0 to 1.0).

    Returns:
        Annotated BGR numpy image array with all overlays stamped.
    """
    if warped_rgb is None or warped_rgb.size == 0:
        raise ValueError("warped_rgb image cannot be None or empty")

    if template is None:
        raise ValueError("Template configuration cannot be None")

    if evaluation_result is None or not isinstance(evaluation_result, dict):
        raise ValueError("evaluation_result must be a valid dictionary")

    # Ensure 3-channel BGR format
    if warped_rgb.ndim == 2:
        annotated = cv2.cvtColor(warped_rgb, cv2.COLOR_GRAY2BGR)
    elif warped_rgb.ndim == 3:
        annotated = warped_rgb.copy()
    else:
        raise ValueError(f"Unsupported image dimensions: {warped_rgb.ndim}")

    # Extract questions audit list
    questions_audit = evaluation_result.get("questions_audit", [])
    if isinstance(questions_audit, dict):
        # Support dict mapping q_num -> audit dict
        questions_audit = list(questions_audit.values())

    # Map question number to layout for fast lookup
    for item in questions_audit:
        q_num = item.get("question_number")
        if q_num is None:
            continue

        q_layout = template.get_question(q_num)
        if q_layout is None:
            continue

        selected_opt = item.get("selected_option")
        correct_ans = item.get("correct_answer")
        status = str(item.get("status", "BLANK")).upper()
        is_correct = bool(item.get("is_correct", False))
        is_bonus = bool(item.get("is_bonus", False))

        bubbles = q_layout.bubbles

        # 1. Handle Multiple Marked or Faint Mark
        if status in ["MULTIPLE_MARKED", "FAINT_MARK"]:
            if selected_opt and str(selected_opt).upper() in bubbles:
                b = bubbles[str(selected_opt).upper()]
                draw_amber_flag(annotated, b.cx, b.cy, b.radius, alpha=alpha)

            # Highlight the ground truth correct answer if defined
            _draw_correct_key_hints(annotated, correct_ans, bubbles, alpha)

        # 2. Handle Blank (Unattempted) Question
        elif status == "BLANK" or selected_opt is None:
            # Highlight what the correct answer was
            _draw_correct_key_hints(annotated, correct_ans, bubbles, alpha)

        # 3. Handle Correct Response
        elif is_correct or is_bonus:
            if selected_opt and str(selected_opt).upper() in bubbles:
                b = bubbles[str(selected_opt).upper()]
                draw_correct_indicator(annotated, b.cx, b.cy, b.radius, alpha=alpha)

        # 4. Handle Incorrect Response
        else:
            if selected_opt and str(selected_opt).upper() in bubbles:
                b = bubbles[str(selected_opt).upper()]
                draw_incorrect_indicator(annotated, b.cx, b.cy, b.radius, alpha=alpha)

            # Overlay ground truth correct answer indicator
            _draw_correct_key_hints(annotated, correct_ans, bubbles, alpha)

    # Draw Header Scorecard Banner
    if draw_scorecard:
        annotated = draw_header_scorecard(annotated, evaluation_result)

    logger.info(
        "Rendered annotated audit sheet for student '%s' with %d question overlays",
        evaluation_result.get("student_id", "UNKNOWN"),
        len(questions_audit),
    )

    return annotated


def _draw_correct_key_hints(
    img: np.ndarray,
    correct_ans: Any,
    bubbles: dict[str, Any],
    alpha: float = 0.35,
) -> None:
    """Helper to draw key indicators for ground truth options."""
    if isinstance(correct_ans, str) and correct_ans.upper() in bubbles:
        kb = bubbles[correct_ans.upper()]
        draw_key_indicator(img, kb.cx, kb.cy, kb.radius, alpha=alpha)
    elif isinstance(correct_ans, list):
        for c in correct_ans:
            if str(c).upper() in bubbles:
                kb = bubbles[str(c).upper()]
                draw_key_indicator(img, kb.cx, kb.cy, kb.radius, alpha=alpha)

