"""
Scoring Engine & Annotated Visual Audit Sheet Generator.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import cv2
import numpy as np

from app.db.models import AnswerKeyModel, MarkingRule, QuestionAudit, Submission


def decode_student_id_from_grid(
    id_results: Dict[str, Dict[str, Any]],
    threshold: float = 0.35,
) -> Tuple[str, float]:
    """
    Decode 6-digit roll number from Student ID bubble matrix.
    """
    if not id_results:
        return "UNKNOWN", 0.5

    # Group by column (0-5)
    cols: Dict[int, List[Tuple[int, float]]] = {}
    for item in id_results.values():
        c = item["col"]
        d = item["digit"]
        dens = item["density"]
        if c not in cols:
            cols[c] = []
        cols[c].append((d, dens))

    digits = []
    confs = []

    for col_idx in sorted(cols.keys()):
        col_items = sorted(cols[col_idx], key=lambda x: x[1], reverse=True)
        top_digit, top_dens = col_items[0]
        sec_digit, sec_dens = col_items[1] if len(col_items) > 1 else (0, 0.0)
        separation = top_dens - sec_dens

        if (top_dens >= threshold and separation > 0.08) or (top_dens >= 0.30 and separation > 0.12):
            digits.append(str(top_digit))
            confs.append(float(min(1.0, 0.75 + separation)))
        elif top_dens >= 0.20 and separation > 0.08:
            digits.append(str(top_digit))
            confs.append(0.70)
        else:
            digits.append("X")
            confs.append(0.30)

    roll_num = "".join(digits) if digits else "UNKNOWN"
    mean_conf = float(np.mean(confs)) if confs else 0.5
    return roll_num, mean_conf


def grade_submission(
    question_results: Dict[int, Dict[str, Any]],
    answer_key: AnswerKeyModel,
    student_id: str,
    roll_conf: float,
    sheet_filename: str,
    processing_time_ms: int = 0,
) -> Dict[str, Any]:
    """
    Grade student choices against Master Answer Key and compute sectional breakdown.
    """
    answers_map = answer_key.answers
    default_rule = answer_key.default_rule
    sections = answer_key.sections

    total_score = 0.0
    max_score = 0.0
    total_attempted = 0
    total_correct = 0
    total_incorrect = 0
    total_unattempted = 0
    total_flagged = 0

    questions_audit: List[Dict[str, Any]] = []

    # Initialize sectional counters
    sec_stats: Dict[str, Dict[str, Any]] = {}
    for sec in sections:
        sec_stats[sec.name] = {
            "name": sec.name,
            "q_start": sec.q_start,
            "q_end": sec.q_end,
            "score": 0.0,
            "max_score": 0.0,
            "correct": 0,
            "incorrect": 0,
            "attempted": 0,
            "total_questions": sec.q_end - sec.q_start + 1,
            "accuracy_pct": 0.0,
        }

    # Grade each question in layout or answer key
    all_q_keys = sorted(list(set([int(k) for k in question_results.keys()] + [int(k) for k in answers_map.keys() if k.isdigit()])))

    for q_num in all_q_keys:
        detected = question_results.get(q_num, {"selected_option": None, "confidence": 0.0, "status": "BLANK"})
        selected_opt = detected.get("selected_option")
        det_status = detected.get("status", "BLANK")
        conf = detected.get("confidence", 1.0)

        correct_key = answers_map.get(str(q_num))

        # Find applicable marking rule
        active_rule = default_rule
        sec_name = None
        for sec in sections:
            if sec.q_start <= q_num <= sec.q_end:
                sec_name = sec.name
                if sec.rule:
                    active_rule = sec.rule
                break

        is_bonus = False
        is_correct = False
        score_delta = 0.0

        if correct_key == "BONUS" or correct_key == "*":
            is_bonus = True
            score_delta = active_rule.bonus
            total_correct += 1
            if selected_opt:
                total_attempted += 1
        elif det_status == "BLANK" or selected_opt is None:
            score_delta = active_rule.unattempted
            total_unattempted += 1
        elif det_status == "MULTIPLE_MARKED":
            score_delta = active_rule.multi_mark
            total_flagged += 1
            if active_rule.multi_mark < 0:
                total_attempted += 1
                total_incorrect += 1
            else:
                total_unattempted += 1
        else:
            total_attempted += 1
            # Check correctness (single or list of acceptable options)
            if isinstance(correct_key, list):
                if selected_opt in correct_key:
                    is_correct = True
            elif isinstance(correct_key, str):
                if selected_opt.upper() == correct_key.upper():
                    is_correct = True

            if is_correct:
                score_delta = active_rule.correct
                total_correct += 1
            else:
                score_delta = active_rule.incorrect
                total_incorrect += 1

            if det_status == "FAINT_MARK":
                total_flagged += 1

        total_score += score_delta
        max_score += active_rule.correct

        # Update Section Breakdown
        if sec_name and sec_name in sec_stats:
            sec_stats[sec_name]["score"] += score_delta
            sec_stats[sec_name]["max_score"] += active_rule.correct
            if is_correct or is_bonus:
                sec_stats[sec_name]["correct"] += 1
            elif selected_opt is not None:
                sec_stats[sec_name]["incorrect"] += 1
            if selected_opt is not None:
                sec_stats[sec_name]["attempted"] += 1

        questions_audit.append({
            "question_number": q_num,
            "selected_option": selected_opt,
            "correct_answer": correct_key,
            "status": det_status,
            "is_correct": is_correct,
            "is_bonus": is_bonus,
            "score_delta": float(score_delta),
            "confidence": float(conf),
            "bubble_coords": detected.get("bubble_coords", {}),
        })

    # Compute Section Accuracy Percentages
    for s in sec_stats.values():
        if s["max_score"] > 0:
            s["accuracy_pct"] = round(float(max(0.0, s["score"]) / s["max_score"]) * 100.0, 1)

    pct = round((total_score / max_score * 100.0), 2) if max_score > 0 else 0.0
    accuracy_pct = round((total_correct / max(1, total_attempted) * 100.0), 2)

    status = "SUCCESS"
    if total_flagged > 0 or roll_conf < 0.70 or "X" in student_id:
        status = "FLAGGED_FOR_REVIEW"

    return {
        "student_id": student_id,
        "roll_number_confidence": round(roll_conf, 3),
        "sheet_filename": sheet_filename,
        "total_score": round(total_score, 2),
        "max_score": round(max_score, 2),
        "percentage": pct,
        "accuracy_pct": accuracy_pct,
        "total_attempted": total_attempted,
        "total_correct": total_correct,
        "total_incorrect": total_incorrect,
        "total_unattempted": total_unattempted,
        "total_flagged": total_flagged,
        "confidence_score": round(roll_conf, 3),
        "status": status,
        "sectional_scores": sec_stats,
        "questions_audit": questions_audit,
        "processing_time_ms": processing_time_ms,
    }


def generate_annotated_overlay(
    warped_bgr: np.ndarray,
    template_config: Dict[str, Any],
    grade_report: Dict[str, Any],
) -> np.ndarray:
    """
    Render transparent colored audit overlays on top of the warped sheet:
    - Green circle = Correct answer selected
    - Red circle = Wrong answer selected
    - Amber circle = Flagged / Multiple marks / Faint mark
    - Blue circle = Ground truth correct key (when candidate answered wrong)
    """
    annotated = warped_bgr.copy()
    overlay = warped_bgr.copy()

    q_layout = {q["q_num"]: q for q in template_config.get("questions_layout", [])}
    audit_map = {item["question_number"]: item for item in grade_report.get("questions_audit", [])}

    for q_num, q_data in q_layout.items():
        audit_item = audit_map.get(q_num)
        if not audit_item:
            continue

        selected_opt = audit_item.get("selected_option")
        correct_key = audit_item.get("correct_answer")
        is_correct = audit_item.get("is_correct", False)
        is_bonus = audit_item.get("is_bonus", False)
        status = audit_item.get("status")

        options = q_data.get("options", {})
        coords_map = audit_item.get("bubble_coords") or options

        # Draw Candidate's selection
        if selected_opt and selected_opt in coords_map:
            coord = coords_map[selected_opt]
            cx, cy, r = int(coord["cx"]), int(coord["cy"]), int(coord["r"])

            if is_correct or is_bonus:
                # Green
                cv2.circle(overlay, (cx, cy), r + 4, (34, 197, 94), -1)
            elif status in ["MULTIPLE_MARKED", "FAINT_MARK"]:
                # Amber
                cv2.circle(overlay, (cx, cy), r + 4, (245, 158, 11), -1)
            else:
                # Red
                cv2.circle(overlay, (cx, cy), r + 4, (239, 68, 68), -1)

        # Highlight ground-truth correct option if candidate was wrong
        if not is_correct and not is_bonus and correct_key and correct_key in coords_map:
            corr_coord = coords_map[correct_key]
            ccx, ccy, cr = int(corr_coord["cx"]), int(corr_coord["cy"]), int(corr_coord["r"])
            cv2.circle(annotated, (ccx, ccy), cr + 4, (37, 99, 235), 3)

    # Blend overlay with 45% transparency
    cv2.addWeighted(overlay, 0.45, annotated, 0.55, 0, annotated)

    # Draw Header Score Badge
    score_txt = f"Candidate: {grade_report['student_id']} | Score: {grade_report['total_score']}/{grade_report['max_score']} ({grade_report['percentage']}%)"
    cv2.rectangle(annotated, (120, 20), (1530, 80), (15, 23, 42), -1)
    cv2.putText(annotated, score_txt, (140, 60), cv2.FONT_HERSHEY_DUPLEX, 0.9, (255, 255, 255), 2)

    return annotated
