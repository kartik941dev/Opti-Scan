"""
Scoring and Evaluation Engine for OptiScan (Phase 6).
Evaluates student bubble detections against answer keys with flexible marking rules.
"""

from typing import Any, Optional, Union

from src.models.answer_key import AnswerKey, MarkingRule, SectionConfig
from src.utils.exceptions import ScoringError
from src.utils.logger import get_logger

logger = get_logger("scorer")


def evaluate_question_response(
    q_num: int,
    detection: dict[str, Any],
    answer_key: AnswerKey,
) -> dict[str, Any]:
    """
    Evaluate a single question detection against the master answer key.

    Args:
        q_num: 1-indexed question number.
        detection: Detection result dictionary for this question.
        answer_key: AnswerKey containing ground truth and marking rules.

    Returns:
        Dictionary containing evaluation details and score delta.
    """
    selected_opt = detection.get("selected_option")
    status = detection.get("status", "BLANK")
    confidence = float(detection.get("confidence", 0.0))
    section_name = detection.get("section") or (
        answer_key.get_section_for_question(q_num).name
        if answer_key.get_section_for_question(q_num)
        else "General"
    )

    correct_ans = answer_key.get_correct_answer(q_num)
    rule: MarkingRule = answer_key.get_rule_for_question(q_num)

    # Check if question is marked as BONUS/DROPPED
    is_bonus = False
    if isinstance(correct_ans, str) and correct_ans.upper() in ["BONUS", "DROPPED", "ALL"]:
        is_bonus = True

    # Check correctness
    is_correct = False
    if is_bonus:
        is_correct = True
    elif selected_opt is not None:
        if isinstance(correct_ans, str):
            is_correct = selected_opt.upper() == correct_ans.upper()
        elif isinstance(correct_ans, list):
            is_correct = selected_opt.upper() in [str(x).upper() for x in correct_ans]

    # Calculate score delta
    score_delta = rule.evaluate_mark(
        status=status,
        is_correct=is_correct,
        is_bonus=is_bonus,
    )

    return {
        "question_number": q_num,
        "section": section_name,
        "selected_option": selected_opt,
        "correct_answer": correct_ans,
        "status": status,
        "confidence": round(confidence, 4),
        "is_correct": is_correct,
        "is_bonus": is_bonus,
        "score_delta": round(score_delta, 2),
        "max_marks": float(rule.correct),
    }


def score_student_sheet(
    detected_answers: dict[int, dict[str, Any]],
    answer_key: AnswerKey,
    student_id: Optional[str] = "UNKNOWN",
) -> dict[str, Any]:
    """
    Score all questions on a student OMR sheet and compute comprehensive exam metrics.

    Args:
        detected_answers: Map of question number (int) to detection result dict.
        answer_key: AnswerKey model instance.
        student_id: Student ID / roll number string.

    Returns:
        Comprehensive scoring report dictionary.

    Raises:
        ScoringError: If answer_key is invalid or detected_answers is empty.
    """
    if answer_key is None:
        raise ScoringError("AnswerKey cannot be None for scoring")

    if not detected_answers:
        raise ScoringError("detected_answers dictionary cannot be empty")

    questions_audit: list[dict[str, Any]] = []
    total_score = 0.0
    max_score = 0.0

    correct_count = 0
    incorrect_count = 0
    blank_count = 0
    multi_count = 0
    faint_count = 0
    bonus_count = 0

    sorted_q_nums = sorted(detected_answers.keys())

    for q_num in sorted_q_nums:
        detection = detected_answers[q_num]
        eval_item = evaluate_question_response(q_num, detection, answer_key)
        questions_audit.append(eval_item)

        score_delta = eval_item["score_delta"]
        total_score += score_delta
        max_score += eval_item["max_marks"]

        status = eval_item["status"]
        if eval_item["is_bonus"]:
            bonus_count += 1
        elif eval_item["is_correct"]:
            correct_count += 1
        elif status == "BLANK":
            blank_count += 1
        elif status == "MULTIPLE_MARKED":
            multi_count += 1
        elif status == "FAINT_MARK":
            faint_count += 1
        else:
            incorrect_count += 1

    total_q = len(questions_audit)
    attempted_q = total_q - blank_count
    accuracy_pct = (float(correct_count) / float(attempted_q) * 100.0) if attempted_q > 0 else 0.0
    percentage = (total_score / max_score * 100.0) if max_score > 0 else 0.0

    report = {
        "student_id": str(student_id or "UNKNOWN"),
        "exam_id": answer_key.exam_id,
        "exam_title": answer_key.exam_title,
        "total_score": round(total_score, 2),
        "max_score": round(max_score, 2),
        "percentage": round(percentage, 2),
        "accuracy_pct": round(accuracy_pct, 2),
        "counts": {
            "total_questions": total_q,
            "attempted": attempted_q,
            "correct": correct_count,
            "incorrect": incorrect_count,
            "blank": blank_count,
            "multiple_marked": multi_count,
            "faint_marked": faint_count,
            "bonus": bonus_count,
        },
        "questions_audit": questions_audit,
        "sectional_scores": compute_sectional_scores(questions_audit, answer_key.sections),
    }

    logger.info(
        "Scored Student '%s': %.2f / %.2f (%.1f%%) | Correct: %d, Wrong: %d, Blank: %d, Multi: %d, Bonus: %d",
        report["student_id"],
        report["total_score"],
        report["max_score"],
        report["percentage"],
        correct_count,
        incorrect_count,
        blank_count,
        multi_count,
        bonus_count,
    )

    return report


def compute_sectional_scores(
    q_evaluations: list[dict[str, Any]],
    sections: Optional[list[SectionConfig]] = None,
) -> dict[str, dict[str, Any]]:
    """
    Aggregate question-by-question evaluations into subject section performance breakdowns.

    Args:
        q_evaluations: List of question evaluation audit dictionaries from score_student_sheet.
        sections: List of SectionConfig objects defining subject section boundaries.

    Returns:
        Dictionary mapping section name to its breakdown summary:
            - section_name: str
            - q_start: int
            - q_end: int
            - score: float
            - max_score: float
            - percentage: float
            - accuracy_pct: float
            - counts: dict of response status counts
    """
    if not q_evaluations:
        return {}

    eval_by_q = {item["question_number"]: item for item in q_evaluations}
    all_q_nums = sorted(eval_by_q.keys())

    # Fallback to single section if none provided
    if not sections:
        min_q = all_q_nums[0] if all_q_nums else 1
        max_q = all_q_nums[-1] if all_q_nums else 1
        sections = [SectionConfig(name="General", q_start=min_q, q_end=max_q)]

    sectional_breakdowns: dict[str, dict[str, Any]] = {}

    for sec in sections:
        sec_name = sec.name
        sec_evals = [eval_by_q[q] for q in all_q_nums if sec.contains(q)]

        sec_score = 0.0
        sec_max_score = 0.0
        sec_correct = 0
        sec_incorrect = 0
        sec_blank = 0
        sec_multi = 0
        sec_faint = 0
        sec_bonus = 0

        for item in sec_evals:
            sec_score += item["score_delta"]
            sec_max_score += item["max_marks"]
            status = item["status"]

            if item["is_bonus"]:
                sec_bonus += 1
            elif item["is_correct"]:
                sec_correct += 1
            elif status == "BLANK":
                sec_blank += 1
            elif status == "MULTIPLE_MARKED":
                sec_multi += 1
            elif status == "FAINT_MARK":
                sec_faint += 1
            else:
                sec_incorrect += 1

        total_in_sec = len(sec_evals)
        attempted_in_sec = total_in_sec - sec_blank
        sec_accuracy = (float(sec_correct) / float(attempted_in_sec) * 100.0) if attempted_in_sec > 0 else 0.0
        sec_percentage = (sec_score / sec_max_score * 100.0) if sec_max_score > 0 else 0.0

        sectional_breakdowns[sec_name] = {
            "section_name": sec_name,
            "q_start": sec.q_start,
            "q_end": sec.q_end,
            "score": round(sec_score, 2),
            "max_score": round(sec_max_score, 2),
            "percentage": round(sec_percentage, 2),
            "accuracy_pct": round(sec_accuracy, 2),
            "counts": {
                "total_questions": total_in_sec,
                "attempted": attempted_in_sec,
                "correct": sec_correct,
                "incorrect": sec_incorrect,
                "blank": sec_blank,
                "multiple_marked": sec_multi,
                "faint_marked": sec_faint,
                "bonus": sec_bonus,
            },
        }

    return sectional_breakdowns

