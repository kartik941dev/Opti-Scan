"""
Master Answer Key & Marking Rules Endpoints with Multi-Format File Support.
Supports JSON, CSV, Excel (.xlsx, .xls), and Plain Text (.txt).
"""

from datetime import datetime
from io import BytesIO, StringIO
import json
import re
from typing import Any, Dict, List, Optional, Union
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
import pandas as pd
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


def normalize_answer_val(val: Any) -> Optional[str]:
    """Normalize any parsed answer value into uppercase standard format ('A', 'B', 'C', 'D', 'BONUS')."""
    if val is None:
        return None
    s = str(val).strip().upper()
    if s in ["A", "B", "C", "D"]:
        return s
    if s in ["BONUS", "*", "ALL", "GRACE"]:
        return "BONUS"
    # Match first valid option letter if surrounded by text e.g. "(A)", "Option B"
    match = re.search(r"\b([A-D]|BONUS)\b", s)
    if match:
        return match.group(1)
    if len(s) == 1 and s.isalpha():
        return s
    return s if s else None


def parse_answer_key_from_bytes(content: bytes, filename: str) -> Dict[str, Any]:
    """
    Universally parse answer key from multiple file formats:
    - JSON (.json)
    - CSV / TSV (.csv, .tsv)
    - Excel (.xlsx, .xls)
    - Text (.txt)
    """
    ext = filename.lower().split(".")[-1] if "." in filename else ""
    parsed_answers: Dict[str, str] = {}
    parsed_rules: Optional[Dict[str, float]] = None
    parsed_sections: Optional[List[dict]] = None
    title = f"Uploaded Key ({filename})"

    # 1. JSON Parsing
    if ext == "json" or content.strip().startswith(b"{") or content.strip().startswith(b"["):
        try:
            data = json.loads(content.decode("utf-8-sig"))
            if isinstance(data, dict):
                title = data.get("exam_title", title)
                # Check for explicit answers dict
                raw_ans = data.get("answers", data.get("answer_key", data.get("key", {})))
                if not raw_ans and not any(k in data for k in ["default_rule", "sections", "marking_rules"]):
                    # Dict itself might be { "1": "A", "2": "B" }
                    raw_ans = data

                if isinstance(raw_ans, dict):
                    for k, v in raw_ans.items():
                        clean_k = re.sub(r"[^\d]", "", str(k))
                        if clean_k:
                            norm_v = normalize_answer_val(v)
                            if norm_v:
                                parsed_answers[clean_k] = norm_v
                elif isinstance(raw_ans, list):
                    for idx, v in enumerate(raw_ans, start=1):
                        if isinstance(v, dict):
                            q_num = v.get("q_num", v.get("question", v.get("q", idx)))
                            ans_val = v.get("answer", v.get("correct", v.get("option", v.get("key"))))
                            clean_k = str(re.sub(r"[^\d]", "", str(q_num))) or str(idx)
                            norm_v = normalize_answer_val(ans_val)
                            if norm_v:
                                parsed_answers[clean_k] = norm_v
                        else:
                            norm_v = normalize_answer_val(v)
                            if norm_v:
                                parsed_answers[str(idx)] = norm_v

                parsed_rules = data.get("default_rule", data.get("marking_rules"))
                parsed_sections = data.get("sections")
            elif isinstance(data, list):
                for idx, v in enumerate(data, start=1):
                    if isinstance(v, dict):
                        q_num = v.get("q_num", v.get("question", v.get("q", idx)))
                        ans_val = v.get("answer", v.get("correct", v.get("option", v.get("key"))))
                        clean_k = str(re.sub(r"[^\d]", "", str(q_num))) or str(idx)
                        norm_v = normalize_answer_val(ans_val)
                        if norm_v:
                            parsed_answers[clean_k] = norm_v
                    else:
                        norm_v = normalize_answer_val(v)
                        if norm_v:
                            parsed_answers[str(idx)] = norm_v
        except Exception as e:
            raise ValueError(f"Error parsing JSON answer key: {e}")

    # 2. Excel Parsing (.xlsx, .xls)
    elif ext in ["xlsx", "xls"]:
        try:
            df = pd.read_excel(BytesIO(content))
            # Try to identify Question and Answer columns
            cols = [str(c).strip().lower() for c in df.columns]
            q_col_idx = None
            ans_col_idx = None

            for i, c in enumerate(cols):
                if any(kw in c for kw in ["q", "question", "s.no", "no", "item"]):
                    q_col_idx = i
                if any(kw in c for kw in ["ans", "key", "correct", "option"]):
                    ans_col_idx = i

            if q_col_idx is not None and ans_col_idx is not None and q_col_idx != ans_col_idx:
                for _, row in df.iterrows():
                    q_val = re.sub(r"[^\d]", "", str(row.iloc[q_col_idx]))
                    ans_val = normalize_answer_val(row.iloc[ans_col_idx])
                    if q_val and ans_val:
                        parsed_answers[q_val] = ans_val
            else:
                # Treat first 2 columns as (Question, Answer) or entire row as sequential answers
                if len(df.columns) >= 2:
                    for idx, row in df.iterrows():
                        q_val = re.sub(r"[^\d]", "", str(row.iloc[0])) or str(idx + 1)
                        ans_val = normalize_answer_val(row.iloc[1])
                        if ans_val:
                            parsed_answers[q_val] = ans_val
                elif len(df.columns) == 1:
                    for idx, val in enumerate(df.iloc[:, 0], start=1):
                        ans_val = normalize_answer_val(val)
                        if ans_val:
                            parsed_answers[str(idx)] = ans_val
        except Exception as e:
            raise ValueError(f"Error reading Excel sheet: {e}")

    # 3. CSV / TSV / TXT Parsing
    else:
        text = content.decode("utf-8-sig", errors="replace")
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        # Strategy A: Check for regex patterns like "1. A", "Q1: B", "1,C", "1 - D", "1\tA"
        for line in lines:
            # Pattern: (Q/Question optionally)(Number)(separator)(Option)
            m = re.search(r"^(?:Q(?:uestion)?)?\s*(\d+)[\.\:\,\-\t\s\=]+([A-D]|BONUS|\*)\b", line, re.IGNORECASE)
            if m:
                q_num = m.group(1)
                opt_val = normalize_answer_val(m.group(2))
                if opt_val:
                    parsed_answers[q_num] = opt_val
                continue

            # Pattern: CSV row "1,A"
            parts = [p.strip() for p in re.split(r"[,\t;]", line) if p.strip()]
            if len(parts) >= 2:
                clean_q = re.sub(r"[^\d]", "", parts[0])
                opt_val = normalize_answer_val(parts[1])
                if clean_q and opt_val:
                    parsed_answers[clean_q] = opt_val
            elif len(parts) == 1 and parts[0].upper() in ["A", "B", "C", "D", "BONUS"]:
                # Line-by-line single letters
                q_idx = str(len(parsed_answers) + 1)
                parsed_answers[q_idx] = parts[0].upper()

    if not parsed_answers:
        raise ValueError("Could not detect question-to-answer mappings in the uploaded file. Please ensure it contains question numbers (e.g. 1-100) and option keys (A, B, C, D, or BONUS).")

    return {
        "answers": parsed_answers,
        "default_rule": parsed_rules,
        "sections": parsed_sections,
        "exam_title": title,
        "total_parsed": len(parsed_answers),
    }


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
@router.post("/upload-file", response_model=dict)
async def upload_answer_key_file(
    exam_id: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Universal answer key file upload endpoint.
    Accepts JSON, CSV, Excel (.xlsx, .xls), and TXT files.
    """
    try:
        content = await file.read()
        parsed = parse_answer_key_from_bytes(content, file.filename or "uploaded_key.txt")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"File parsing error: {str(e)}")

    keys_col = get_collection("answer_keys")
    existing = await keys_col.find_one({"exam_id": exam_id})

    # Preserve existing rules/sections if not specified in file
    rules = parsed.get("default_rule")
    if not rules and existing and "default_rule" in existing:
        rules = existing["default_rule"]
    elif not rules:
        rules = {"correct": 4.0, "incorrect": -1.0, "unattempted": 0.0, "multi_mark": -1.0, "bonus": 4.0}

    sections = parsed.get("sections")
    if not sections and existing and "sections" in existing:
        sections = existing["sections"]
    elif not sections:
        sections = [
            {"name": "Section A (Physics)", "q_start": 1, "q_end": 25},
            {"name": "Section B (Chemistry)", "q_start": 26, "q_end": 50},
            {"name": "Section C (Mathematics)", "q_start": 51, "q_end": 75},
            {"name": "Section D (Biology)", "q_start": 76, "q_end": 100},
        ]

    doc_data = {
        "exam_id": exam_id,
        "exam_title": parsed.get("exam_title", "Uploaded Answer Key"),
        "answers": parsed["answers"],
        "default_rule": rules,
        "sections": sections,
        "updated_at": datetime.utcnow(),
    }

    if existing:
        await keys_col.update_one({"exam_id": exam_id}, {"$set": doc_data})
        doc_data["_id"] = existing["_id"]
    else:
        doc_data["_id"] = f"key_{exam_id}"
        doc_data["created_at"] = datetime.utcnow()
        await keys_col.insert_one(doc_data)

    doc_data["id"] = str(doc_data["_id"])
    doc_data["message"] = f"Successfully loaded and saved {parsed['total_parsed']} answers from {file.filename}"
    return doc_data
