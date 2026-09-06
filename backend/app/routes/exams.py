"""
Exams Management Endpoints.
"""

from datetime import datetime
import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.db.models import Exam
from app.db.mongo import get_collection

router = APIRouter(prefix="/exams", tags=["Exams"])


class ExamCreate(BaseModel):
    title: str
    code: str
    description: Optional[str] = ""
    total_questions: int = 100
    template_name: Optional[str] = "omr_template.json"


class ExamUpdate(BaseModel):
    title: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    total_questions: Optional[int] = None
    template_name: Optional[str] = None


@router.get("", response_model=List[dict])
async def list_exams():
    exams_col = get_collection("exams")
    cursor = exams_col.find()
    exams = await cursor.to_list(100)

    # Seed standard initial assessment if empty
    if not exams:
        demo_exam = {
            "_id": "exam_standard_100q",
            "title": "National Engineering & Science Assessment 2026",
            "code": "NESA-2026-100Q",
            "description": "Standard 100-Question Multi-Subject Assessment (Physics, Chemistry, Math, Biology)",
            "total_questions": 100,
            "template_name": "omr_template.json",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        await exams_col.insert_one(demo_exam)
        exams = [demo_exam]

    # Convert _id to id for API consistency
    result = []
    for e in exams:
        item = dict(e)
        item["id"] = str(item.get("_id"))
        result.append(item)

    return result


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_exam(exam_in: ExamCreate):
    exams_col = get_collection("exams")
    keys_col = get_collection("answer_keys")
    exam_id = f"exam_{uuid.uuid4().hex[:8]}"

    total_q = min(1000, max(1, exam_in.total_questions))

    exam_dict = {
        "_id": exam_id,
        "title": exam_in.title,
        "code": exam_in.code,
        "description": exam_in.description or "",
        "total_questions": total_q,
        "template_name": exam_in.template_name or "omr_template.json",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await exams_col.insert_one(exam_dict)

    # Initialize default answer key for new exam
    from app.routes.answer_key import generate_default_100q_answers
    if total_q == 100:
        default_answers = generate_default_100q_answers()
        sections = [
            {"name": "Section A (Physics)", "q_start": 1, "q_end": 25},
            {"name": "Section B (Chemistry)", "q_start": 26, "q_end": 50},
            {"name": "Section C (Mathematics)", "q_start": 51, "q_end": 75},
            {"name": "Section D (Biology)", "q_start": 76, "q_end": 100},
        ]
    else:
        default_answers = {}
        opts = ["A", "B", "C", "D"]
        for i in range(1, total_q + 1):
            default_answers[str(i)] = opts[(i - 1) % 4]
        sections = []

    key_doc = {
        "_id": f"key_{exam_id}",
        "exam_id": exam_id,
        "exam_title": exam_in.title,
        "total_questions": total_q,
        "answers": default_answers,
        "default_rule": {"correct": 4.0, "incorrect": -1.0, "unattempted": 0.0, "multi_mark": 0.0, "bonus": 4.0},
        "sections": sections,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await keys_col.insert_one(key_doc)

    exam_dict["id"] = exam_id
    return exam_dict



@router.get("/{exam_id}", response_model=dict)
async def get_exam(exam_id: str):
    exams_col = get_collection("exams")
    exam = await exams_col.find_one({"_id": exam_id})
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    exam["id"] = str(exam.get("_id"))
    return exam


@router.put("/{exam_id}", response_model=dict)
async def update_exam(exam_id: str, exam_in: ExamUpdate):
    exams_col = get_collection("exams")
    exam = await exams_col.find_one({"_id": exam_id})
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    update_data = {k: v for k, v in exam_in.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()

    await exams_col.update_one({"_id": exam_id}, {"$set": update_data})
    updated = await exams_col.find_one({"_id": exam_id})
    updated["id"] = str(updated.get("_id"))
    return updated


@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exam(exam_id: str):
    exams_col = get_collection("exams")
    submissions_col = get_collection("submissions")
    keys_col = get_collection("answer_keys")

    await exams_col.delete_one({"_id": exam_id})
    await submissions_col.delete_many({"exam_id": exam_id})
    await keys_col.delete_one({"exam_id": exam_id})
    return None
