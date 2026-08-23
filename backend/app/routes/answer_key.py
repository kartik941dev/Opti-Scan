"""
Master Answer Key & Marking Rules Endpoints.
"""

from datetime import datetime
import json
from typing import Any, Dict, List, Optional, Union
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from backend.app.db.models import AnswerKeyModel, MarkingRule, SectionConfig
from backend.app.db.mongo import get_collection

router = APIRouter(prefix="/answer-keys", tags=["Answer Key"])


class AnswerKeyUpdate(BaseModel):
    exam_id: str
    exam_title: Optional[str] = "Standard OMR Assessment"
    answers: Dict[str, Union[str, List[str], None]]
    default_rule: Optional[MarkingRule] = None
    sections: Optional[List[SectionConfig]] = None


def generate_default_100q_answers() -> Dict[str, str]:
    """Pattern generator for 100 questions (A, B, C, D cyclic)."""
    opts = ["A", "B", "C", "D"]
    return {str(i): opts[(i - 1) % 4] for i in range(1, 101)}


@router.get("/{exam_id}", response_model=dict)
async def get_answer_key(exam_id: str):
    keys_col = get_collection("answer_keys")
    key_doc = await keys_col.find_one({"exam_id": exam_id})

    # Default auto-seed if not created yet
    if not key_doc:
        key_doc = {
            "_id": f"key_{exam_id}",
            "exam_id": exam_id,
            "exam_title": "Standard OMR Assessment",
            "answers": generate_default_100q_answers(),
            "default_rule": {
                "correct": 4.0,
                "incorrect": -1.0,
                "unattempted": 0.0,
                "multi_mark": -1.0,
                "bonus": 4.0,
            },
            "sections": [
                {"name": "Section A (Physics)", "q_start": 1, "q_end": 25},
                {"name": "Section B (Chemistry)", "q_start": 26, "q_end": 50},
                {"name": "Section C (Mathematics)", "q_start": 51, "q_end": 75},
                {"name": "Section D (Biology)", "q_start": 76, "q_end": 100},
            ],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        await keys_col.insert_one(key_doc)

    key_doc["id"] = str(key_doc.get("_id"))
    return key_doc


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_or_update_answer_key(key_in: AnswerKeyUpdate):
    keys_col = get_collection("answer_keys")
    existing = await keys_col.find_one({"exam_id": key_in.exam_id})

    doc_data = {
        "exam_id": key_in.exam_id,
        "exam_title": key_in.exam_title or "Standard OMR Assessment",
        "answers": key_in.answers,
        "default_rule": key_in.default_rule.model_dump() if key_in.default_rule else MarkingRule().model_dump(),
        "sections": [s.model_dump() for s in key_in.sections] if key_in.sections else [],
        "updated_at": datetime.utcnow(),
    }

    if existing:
        await keys_col.update_one({"exam_id": key_in.exam_id}, {"$set": doc_data})
        doc_data["_id"] = existing["_id"]
    else:
        doc_data["_id"] = f"key_{key_in.exam_id}"
        doc_data["created_at"] = datetime.utcnow()
        await keys_col.insert_one(doc_data)

    doc_data["id"] = str(doc_data["_id"])
    return doc_data


@router.post("/upload-json", response_model=dict)
async def upload_answer_key_json(
    exam_id: str = Form(...),
    file: UploadFile = File(...),
):
    """Upload answer key directly from JSON file."""
    try:
        content = await file.read()
        data = json.loads(content.decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON file: {e}")

    keys_col = get_collection("answer_keys")
    answers = data.get("answers", {})
    rules = data.get("default_rule", data.get("marking_rules", {"correct": 4.0, "incorrect": -1.0, "unattempted": 0.0, "multi_mark": -1.0, "bonus": 4.0}))
    sections = data.get("sections", [])

    doc_data = {
        "exam_id": exam_id,
        "exam_title": data.get("exam_title", "Uploaded Assessment Key"),
        "answers": answers,
        "default_rule": rules,
        "sections": sections,
        "updated_at": datetime.utcnow(),
    }

    existing = await keys_col.find_one({"exam_id": exam_id})
    if existing:
        await keys_col.update_one({"exam_id": exam_id}, {"$set": doc_data})
        doc_data["_id"] = existing["_id"]
    else:
        doc_data["_id"] = f"key_{exam_id}"
        doc_data["created_at"] = datetime.utcnow()
        await keys_col.insert_one(doc_data)

    doc_data["id"] = str(doc_data["_id"])
    return doc_data
