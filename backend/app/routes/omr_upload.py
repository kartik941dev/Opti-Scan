"""
OMR Upload & High-Throughput Live Evaluation Endpoints.
"""

from datetime import datetime
import os
from pathlib import Path
import time
import uuid
from typing import List, Optional
import cv2
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
import numpy as np

from backend.app.config import settings
from backend.app.db.models import AnswerKeyModel, MarkingRule, SectionConfig
from backend.app.db.mongo import get_collection
from backend.app.omr_engine.align import align_pipeline
from backend.app.omr_engine.bubble_grid import load_template_config
from backend.app.omr_engine.detect_fill import extract_all_bubbles_and_fills
from backend.app.omr_engine.grade import decode_student_id_from_grid, generate_annotated_overlay, grade_submission
from backend.app.omr_engine.preprocess import load_image, preprocess_pipeline

router = APIRouter(prefix="/omr", tags=["OMR Evaluation"])


async def get_or_create_answer_key_model(exam_id: str) -> AnswerKeyModel:
    keys_col = get_collection("answer_keys")
    doc = await keys_col.find_one({"exam_id": exam_id})
    if not doc:
        answers = {
            # Section A (Physics) Q1 - Q25
            "1": "C", "2": "B", "3": "D", "4": "A", "5": "A", "6": "A", "7": "C", "8": "A", "9": "B", "10": "A",
            "11": "A", "12": "D", "13": "D", "14": "A", "15": "B", "16": "A", "17": "D", "18": "A", "19": "A", "20": "B",
            "21": "A", "22": "D", "23": "A", "24": "B", "25": "A",
            # Section B (Chemistry) Q26 - Q50
            "26": "B", "27": "C", "28": "D", "29": "B", "30": "A", "31": "C", "32": "B", "33": "A", "34": "B", "35": "C",
            "36": "A", "37": "A", "38": "A", "39": "B", "40": "D", "41": "D", "42": "C", "43": "D", "44": "D", "45": "C",
            "46": "C", "47": "B", "48": "B", "49": "B", "50": "A",
            # Section C (Mathematics) Q51 - Q75
            "51": "C", "52": "D", "53": "C", "54": "D", "55": "C", "56": "A", "57": "A", "58": "D", "59": "B", "60": "C",
            "61": "B", "62": "D", "63": "D", "64": "A", "65": "A", "66": "C", "67": "C", "68": "C", "69": "D", "70": "D",
            "71": "A", "72": "A", "73": "C", "74": "D", "75": "A",
            # Section D (Biology) Q76 - Q100
            "76": "A", "77": "C", "78": "D", "79": "C", "80": "D", "81": "C", "82": "A", "83": "D", "84": "C", "85": "B",
            "86": "A", "87": "D", "88": "A", "89": "B", "90": "C", "91": "B", "92": "B", "93": "D", "94": "D", "95": "D",
            "96": "A", "97": "B", "98": "D", "99": "D", "100": "C",
        }
        doc = {
            "_id": f"key_{exam_id}",
            "exam_id": exam_id,
            "exam_title": "Standard OMR Assessment",
            "answers": answers,
            "default_rule": {"correct": 4.0, "incorrect": -1.0, "unattempted": 0.0, "multi_mark": 0.0, "bonus": 4.0},
            "sections": [
                {"name": "Section A (Physics)", "q_start": 1, "q_end": 25},
                {"name": "Section B (Chemistry)", "q_start": 26, "q_end": 50},
                {"name": "Section C (Mathematics)", "q_start": 51, "q_end": 75},
                {"name": "Section D (Biology)", "q_start": 76, "q_end": 100},
            ],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        await keys_col.insert_one(doc)

    return AnswerKeyModel(
        exam_id=doc["exam_id"],
        exam_title=doc.get("exam_title", "Standard OMR Assessment"),
        answers=doc.get("answers", {}),
        default_rule=MarkingRule(**doc.get("default_rule", {})),
        sections=[SectionConfig(**s) for s in doc.get("sections", [])],
    )


def process_omr_image(
    image_bytes: bytes,
    filename: str,
    answer_key: AnswerKeyModel,
    template_config: dict,
    exam_id: str,
) -> dict:
    """Core Pure-CV processing function for single OMR sheet."""
    t_start = time.perf_counter()

    # 1. Preprocessing
    rgb_scaled, gray_clahe, binary_mask, scale = preprocess_pipeline(image_bytes)

    # 2. Alignment & Homography Warp
    warped_rgb, warped_binary, _ = align_pipeline(rgb_scaled, binary_mask)

    # 3. Bubble Fill Extraction
    warped_gray = cv2.cvtColor(warped_rgb, cv2.COLOR_BGR2GRAY)
    q_results, id_results, thresh = extract_all_bubbles_and_fills(
        warped_binary, template_config, warped_gray=warped_gray
    )

    # 4. Decode Roll Number
    roll_num, roll_conf = decode_student_id_from_grid(id_results, threshold=thresh)

    # 5. Grade & Compute Section Breakdown
    t_elapsed_ms = int(round((time.perf_counter() - t_start) * 1000))
    report = grade_submission(
        question_results=q_results,
        answer_key=answer_key,
        student_id=roll_num,
        roll_conf=roll_conf,
        sheet_filename=filename,
        processing_time_ms=t_elapsed_ms,
    )

    # 6. Generate Annotated Overlay
    annotated = generate_annotated_overlay(warped_rgb, template_config, report)

    # 7. Save Annotated Image to Disk
    ann_filename = f"ann_{uuid.uuid4().hex[:12]}_{Path(filename).stem}.jpg"
    ann_path = settings.ANNOTATED_DIR / ann_filename
    cv2.imwrite(str(ann_path), annotated)

    sub_id = f"sub_{uuid.uuid4().hex[:10]}"
    submission_doc = {
        "_id": sub_id,
        "id": sub_id,
        "exam_id": exam_id,
        "student_id": report["student_id"],
        "roll_number_confidence": report["roll_number_confidence"],
        "sheet_filename": filename,
        "annotated_image_url": f"/static/annotated/{ann_filename}",
        "total_score": report["total_score"],
        "max_score": report["max_score"],
        "percentage": report["percentage"],
        "accuracy_pct": report["accuracy_pct"],
        "total_attempted": report["total_attempted"],
        "total_correct": report["total_correct"],
        "total_incorrect": report["total_incorrect"],
        "total_unattempted": report["total_unattempted"],
        "total_flagged": report["total_flagged"],
        "confidence_score": report["confidence_score"],
        "status": report["status"],
        "sectional_scores": report["sectional_scores"],
        "questions_audit": report["questions_audit"],
        "processing_time_ms": report["processing_time_ms"],
        "created_at": datetime.utcnow(),
    }

    return submission_doc


@router.post("/upload-single", response_model=dict)
async def upload_single_omr(
    exam_id: str = Form(...),
    file: UploadFile = File(...),
):
    try:
        content = await file.read()
        answer_key = await get_or_create_answer_key_model(exam_id)
        template_cfg = load_template_config()

        result = process_omr_image(
            image_bytes=content,
            filename=file.filename or "uploaded_sheet.png",
            answer_key=answer_key,
            template_config=template_cfg,
            exam_id=exam_id,
        )

        # Store in DB
        submissions_col = get_collection("submissions")
        await submissions_col.insert_one(result)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OMR Evaluation Failed: {str(e)}")


@router.post("/upload-batch", response_model=List[dict])
async def upload_batch_omr(
    exam_id: str = Form(...),
    files: List[UploadFile] = File(...),
):
    answer_key = await get_or_create_answer_key_model(exam_id)
    template_cfg = load_template_config()
    submissions_col = get_collection("submissions")

    results = []
    for f in files:
        try:
            content = await f.read()
            sub = process_omr_image(
                image_bytes=content,
                filename=f.filename or "batch_sheet.png",
                answer_key=answer_key,
                template_config=template_cfg,
                exam_id=exam_id,
            )
            await submissions_col.insert_one(sub)
            results.append(sub)
        except Exception as e:
            # Add quarantine/failed record
            failed_sub = {
                "_id": f"sub_fail_{uuid.uuid4().hex[:8]}",
                "exam_id": exam_id,
                "student_id": "ERROR",
                "sheet_filename": f.filename or "unknown.png",
                "total_score": 0.0,
                "max_score": 0.0,
                "status": "FAILED",
                "error": str(e),
                "created_at": datetime.utcnow(),
            }
            results.append(failed_sub)

    return results


def draw_synthetic_omr_for_demo(
    student_id: str,
    filled_answers: dict,
    template_config: dict,
) -> np.ndarray:
    """Helper to draw synthetic OMR sheet for quick live demo."""
    cw = template_config.get("canvas_width", 1654)
    ch = template_config.get("canvas_height", 2339)
    img = np.full((ch, cw, 3), 255, dtype=np.uint8)

    # 1. Draw 4 Fiducial Registration Corner Squares (63x63 black solid)
    f_size = 63
    offsets = [(126, 126), (cw - 126, 126), (cw - 126, ch - 126), (126, ch - 126)]
    for cx, cy in offsets:
        cv2.rectangle(img, (cx - f_size // 2, cy - f_size // 2), (cx + f_size // 2, cy + f_size // 2), (0, 0, 0), -1)

    # 2. Draw Header Titles & Layout
    cv2.putText(img, "OPTISCAN HIGH-PRECISION ASSESSMENT SHEET", (260, 95), cv2.FONT_HERSHEY_DUPLEX, 1.0, (15, 23, 42), 2)
    cv2.line(img, (220, 150), (cw - 220, 150), (100, 116, 139), 2)

    # 3. Draw Student ID Matrix
    id_grid = template_config.get("student_id_grid", {})
    id_digits = list(student_id.ljust(6, "0")[:6])

    if id_grid:
        first_id_item = list(id_grid.values())[0]
        cv2.putText(img, "ROLL NUMBER", (first_id_item["cx"] - 10, first_id_item["cy"] - 45), cv2.FONT_HERSHEY_DUPLEX, 0.7, (0, 0, 0), 2)

    for key, coord in id_grid.items():
        cx, cy, r = coord["cx"], coord["cy"], coord["r"]
        col, digit = coord["col"], coord["digit"]

        # Outer bubble ring
        cv2.circle(img, (cx, cy), r, (0, 0, 0), 2)
        cv2.putText(img, str(digit), (cx - 4, cy + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (70, 70, 70), 1)

        # Fill if digit matches
        if col < len(id_digits) and id_digits[col] == str(digit):
            cv2.circle(img, (cx, cy), r - 1, (20, 20, 20), -1)

    # 4. Draw Question Bubbles
    for q in template_config.get("questions_layout", []):
        q_num = q["q_num"]
        opts = q["options"]

        # Column Header / Question label
        first_opt = list(opts.values())[0]
        lbl_x = first_opt["cx"] - 50
        lbl_y = first_opt["cy"] + 4
        cv2.putText(img, f"Q{q_num:02d}", (lbl_x, lbl_y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (15, 23, 42), 1)

        chosen = filled_answers.get(str(q_num), filled_answers.get(q_num))

        for opt_key, coord in opts.items():
            cx, cy, r = coord["cx"], coord["cy"], coord["r"]
            cv2.circle(img, (cx, cy), r, (0, 0, 0), 2)
            cv2.putText(img, opt_key, (cx - 4, cy + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (70, 70, 70), 1)

            if chosen == opt_key:
                cv2.circle(img, (cx, cy), r - 1, (25, 25, 25), -1)

    # Slight realistic noise
    noise = np.random.normal(0, 3, img.shape)
    img = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    return img


@router.post("/demo-sheets", response_model=List[dict])
async def load_demo_sheets(exam_id: str = Form(...)):
    """Generate 5 demo student sheets, evaluate and store them."""
    answer_key = await get_or_create_answer_key_model(exam_id)
    template_cfg = load_template_config()
    submissions_col = get_collection("submissions")

    demo_students = [
        {"id": "104928", "bias": 0.95, "name": "Elena Rostova (Top Scorer)"},
        {"id": "205819", "bias": 0.80, "name": "Marcus Vance (High Performer)"},
        {"id": "319402", "bias": 0.65, "name": "Sophia Chen (Average)"},
        {"id": "420195", "bias": 0.45, "name": "Liam Patel (Needs Improvement)"},
        {"id": "583017", "bias": 0.30, "name": "Noah Davis (Flagged / Smudged)"},
    ]

    opts = ["A", "B", "C", "D"]
    created_subs = []

    for item in demo_students:
        s_id = item["id"]
        bias = item["bias"]

        student_answers = {}
        for q_idx in range(1, 101):
            correct_ans = answer_key.answers.get(str(q_idx), "A")
            r_val = np.random.rand()
            if r_val < bias:
                student_answers[q_idx] = correct_ans
            elif r_val < 0.90:
                # Random wrong answer
                wrong_pool = [o for o in opts if o != correct_ans]
                student_answers[q_idx] = np.random.choice(wrong_pool)
            # Else blank

        # Generate and encode synthetic sheet
        synthetic_img = draw_synthetic_omr_for_demo(s_id, student_answers, template_cfg)
        _, buf = cv2.imencode(".png", synthetic_img)
        bytes_data = buf.tobytes()

        sub = process_omr_image(
            image_bytes=bytes_data,
            filename=f"student_{s_id}_scan.png",
            answer_key=answer_key,
            template_config=template_cfg,
            exam_id=exam_id,
        )
        await submissions_col.insert_one(sub)
        created_subs.append(sub)

    return created_subs
