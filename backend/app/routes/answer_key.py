"""
Master Answer Key & Marking Rules Endpoints with Multi-Format File Support.
Supports JSON, CSV, Excel (.xlsx, .xls), and Plain Text (.txt) up to 1000 Questions.
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
    total_questions: Optional[int] = 100
    answers: Dict[str, Union[str, List[str], None]]
    default_rule: Optional[MarkingRule] = None
    sections: Optional[List[SectionConfig]] = None


class RawTextKeyUpdate(BaseModel):
    exam_id: str
    raw_text: str
    exam_title: Optional[str] = None
    total_questions: Optional[int] = None


def generate_default_100q_answers() -> Dict[str, str]:
    """100-Question ground truth answer key matching user's assessment dataset."""
    return {
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


def normalize_answer_val(val: Any) -> Optional[str]:
    """Normalize any parsed answer value into uppercase standard format ('A', 'B', 'C', 'D', 'BONUS')."""
    if val is None or pd.isna(val):
        return None
    s = str(val).strip().strip('"\'').upper()
    if not s or s in ["NAN", "NONE", "NULL", "EMPTY", "-", "N/A"]:
        return None
    if s in ["A", "B", "C", "D"]:
        return s
    if s in ["BONUS", "*", "ALL", "GRACE", "FREE"]:
        return "BONUS"
    # Match standalone options like "(A)", "Option B", "[C]", "D.", "Key: A", "Q1: A"
    m = re.search(r"\b([A-D]|BONUS|\*)\b", s)
    if m:
        ans = m.group(1)
        return "BONUS" if ans == "*" else ans
    return None


def clean_col_header(name: Any) -> str:
    """Clean header text by stripping BOM, quotes, and whitespace."""
    s = str(name).strip().lstrip("\ufeff").strip('"\'')
    return s.lower()


def parse_answer_key_from_bytes(content: bytes, filename: str) -> Dict[str, Any]:
    """
    Universally parse answer key from multiple file formats (up to 1000 questions):
    - JSON (.json)
    - CSV / TSV (.csv, .tsv)
    - Excel (.xlsx, .xls)
    - Text (.txt)
    Extracts Question numbers (e.g. Q01, 1), Options (A, B, C, D, BONUS), and optional Sections.
    """
    ext = filename.lower().split(".")[-1] if "." in filename else ""
    parsed_answers: Dict[str, str] = {}
    parsed_rules: Optional[Dict[str, float]] = None
    parsed_sections: Optional[List[dict]] = None
    title = f"Uploaded Key ({filename})"
    detected_sections_map: Dict[str, List[int]] = {}

    # 1. JSON Parsing
    if ext == "json" or content.strip().startswith(b"{") or content.strip().startswith(b"["):
        try:
            data = json.loads(content.decode("utf-8-sig", errors="replace"))
            if isinstance(data, dict):
                title = data.get("exam_title", data.get("exam", title))
                raw_ans = data.get("answers", data.get("answer_key", data.get("key", {})))
                if not raw_ans and not any(k in data for k in ["default_rule", "sections", "marking_rules", "scoring"]):
                    raw_ans = data

                json_sections_map: Dict[str, List[int]] = {}

                if isinstance(raw_ans, dict):
                    for k, v in raw_ans.items():
                        digits = re.sub(r"[^\d]", "", str(k))
                        if digits:
                            clean_k = str(int(digits))
                            norm_v = normalize_answer_val(v)
                            if norm_v:
                                parsed_answers[clean_k] = norm_v
                elif isinstance(raw_ans, list):
                    for idx, v in enumerate(raw_ans, start=1):
                        if isinstance(v, dict):
                            q_num = v.get("q_num", v.get("question", v.get("q", idx)))
                            ans_val = v.get("answer", v.get("correct", v.get("option", v.get("key"))))
                            digits = re.sub(r"[^\d]", "", str(q_num))
                            clean_k = str(int(digits)) if digits else str(idx)
                            norm_v = normalize_answer_val(ans_val)
                            if norm_v:
                                parsed_answers[clean_k] = norm_v
                                sec_name = v.get("section", v.get("sec", v.get("subject")))
                                if sec_name and str(sec_name).strip():
                                    sec_clean = str(sec_name).strip()
                                    if sec_clean not in json_sections_map:
                                        json_sections_map[sec_clean] = []
                                    json_sections_map[sec_clean].append(int(clean_k))
                        else:
                            norm_v = normalize_answer_val(v)
                            if norm_v:
                                parsed_answers[str(idx)] = norm_v

                raw_rule = data.get("default_rule", data.get("marking_rules", data.get("scoring")))
                if isinstance(raw_rule, dict):
                    parsed_rules = {
                        "correct": float(raw_rule.get("correct", 4.0)),
                        "incorrect": float(raw_rule.get("incorrect", -1.0)),
                        "unattempted": float(raw_rule.get("unattempted", 0.0)),
                        "multi_mark": float(raw_rule.get("multi_mark", 0.0)),
                        "bonus": float(raw_rule.get("bonus", 4.0)),
                    }

                parsed_sections = data.get("sections")
                if not parsed_sections and json_sections_map:
                    parsed_sections = []
                    for s_name, q_list in json_sections_map.items():
                        parsed_sections.append({
                            "name": s_name,
                            "q_start": min(q_list),
                            "q_end": max(q_list),
                        })
                    parsed_sections.sort(key=lambda s: s["q_start"])
            elif isinstance(data, list):
                for idx, v in enumerate(data, start=1):
                    if isinstance(v, dict):
                        q_num = v.get("q_num", v.get("question", v.get("q", idx)))
                        ans_val = v.get("answer", v.get("correct", v.get("option", v.get("key"))))
                        digits = re.sub(r"[^\d]", "", str(q_num))
                        clean_k = str(int(digits)) if digits else str(idx)
                        norm_v = normalize_answer_val(ans_val)
                        if norm_v:
                            parsed_answers[clean_k] = norm_v
                    else:
                        norm_v = normalize_answer_val(v)
                        if norm_v:
                            parsed_answers[str(idx)] = norm_v

            max_q = max([int(k) for k in parsed_answers.keys()]) if parsed_answers else 100
            return {
                "answers": parsed_answers,
                "default_rule": parsed_rules,
                "sections": parsed_sections,
                "exam_title": title,
                "total_parsed": len(parsed_answers),
                "total_questions": min(1000, max(max_q, len(parsed_answers))),
            }
        except Exception as e:
            if ext == "json":
                raise ValueError(f"Error parsing JSON answer key: {e}")

    # 2. Plain Text Line-by-Line Parsing Pass (for text/csv/tsv files, not binary excel)
    text_pass_answers: Dict[str, str] = {}
    text_pass_sections: Dict[str, List[int]] = {}

    if ext not in ["xlsx", "xls"]:
        text_decoded = content.decode("utf-8-sig", errors="replace")
        text_lines = [line.strip() for line in text_decoded.splitlines() if line.strip()]

        for idx, line in enumerate(text_lines, start=1):
            if idx == 1 and any(h in line.lower() for h in ["question", "section", "answer", "option", "choice"]):
                continue

            # Regex format: e.g. "Q1: A", "2. B", "Q003 - C", "Question 4 = D", "5. *", "6. (A)", "7 = [B]"
            m = re.search(r"^(?:q(?:uestion)?)?\s*(\d+)[\.\:\,\-\t\s\=\|\/]+(?:option|key|ans|answer)?\s*[\(\[\{]?\s*([a-d]|bonus|\*)\s*[\)\]\}]?\.?\s*$", line, re.IGNORECASE)
            if m:
                q_num = str(int(m.group(1)))
                opt_val = normalize_answer_val(m.group(2))
                if opt_val:
                    text_pass_answers[q_num] = opt_val
                continue

            # Delimiter split
            parts = [p.strip().strip('"\'') for p in re.split(r"[,\t;:|]", line) if p.strip()]
            if len(parts) >= 2:
                found_q = None
                found_ans = None
                found_sec = None

                for p in reversed(parts):
                    norm = normalize_answer_val(p)
                    if norm:
                        found_ans = norm
                        break

                for p in parts:
                    digits = re.sub(r"[^\d]", "", p)
                    if digits:
                        found_q = str(int(digits))
                        break

                if len(parts) >= 3 and parts[1]:
                    found_sec = parts[1]

                if not found_q:
                    found_q = str(idx)

                if found_ans:
                    text_pass_answers[found_q] = found_ans
                    if found_sec and found_sec.lower() not in ["nan", "none", "null", "section", "sec"]:
                        if found_sec not in text_pass_sections:
                            text_pass_sections[found_sec] = []
                        text_pass_sections[found_sec].append(int(found_q))
                    continue

            # Single option line (A, B, C, D, BONUS, *)
            single_opt = normalize_answer_val(line)
            if single_opt:
                q_idx = str(len(text_pass_answers) + 1)
                text_pass_answers[q_idx] = single_opt

    # 3. Tabular Parsing (CSV, TSV, Excel)
    df = None
    if ext in ["xlsx", "xls"]:
        try:
            df = pd.read_excel(BytesIO(content))
        except Exception as e:
            raise ValueError(f"Error reading Excel file: {e}")
    elif ext != "txt":
        encodings = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]
        for enc in encodings:
            try:
                text = content.decode(enc, errors="replace")
                for sep in [",", "\t", ";", "|", None]:
                    try:
                        temp_df = pd.read_csv(
                            StringIO(text),
                            sep=sep,
                            engine="python",
                            on_bad_lines="skip",
                            skipinitialspace=True,
                        )
                        if temp_df is not None and not temp_df.empty and len(temp_df.columns) >= 2:
                            df = temp_df
                            break
                        elif temp_df is not None and not temp_df.empty and df is None:
                            df = temp_df
                    except Exception:
                        continue
                if df is not None and len(df.columns) >= 2:
                    break
            except Exception:
                continue

    if df is not None and not df.empty:
        col_names = [str(c) for c in df.columns]
        cols_lower = [clean_col_header(c) for c in col_names]

        header_has_answer = any(normalize_answer_val(c) is not None for c in col_names)
        header_has_qnum = any(bool(re.match(r"^(?:q(?:uestion)?)?\s*\d+$", str(c).strip(), re.I)) for c in col_names)
        is_data_row = header_has_answer or (header_has_qnum and not any(k in str(c).lower() for c in col_names for k in ["section", "subject", "item", "answer"]))

        if is_data_row:
            header_row = pd.DataFrame([col_names], columns=df.columns)
            df = pd.concat([header_row, df], ignore_index=True)
            cols_lower = [f"col_{i}" for i in range(len(df.columns))]

        q_col_idx = None
        ans_col_idx = None
        sec_col_idx = None

        for i, c in enumerate(cols_lower):
            if q_col_idx is None and any(kw == c or c.startswith(kw) for kw in ["question", "q_no", "qnum", "q.", "item", "s.no", "sno", "number", "q"]):
                q_col_idx = i
                break

        for i, c in enumerate(cols_lower):
            if i != q_col_idx and sec_col_idx is None and any(kw == c or kw in c for kw in ["section", "sec", "subject", "topic", "part", "domain"]):
                sec_col_idx = i
                break

        for i, c in enumerate(cols_lower):
            if i != q_col_idx and i != sec_col_idx and ans_col_idx is None and any(kw == c or kw in c for kw in ["answer", "ans", "key", "correct", "option", "opt", "choice"]):
                ans_col_idx = i
                break

        if ans_col_idx is None:
            best_ans_idx = None
            best_ans_score = 0
            for i in range(len(df.columns)):
                if i in [q_col_idx, sec_col_idx]:
                    continue
                valid_count = sum(1 for val in df.iloc[:, i] if normalize_answer_val(val) is not None)
                if valid_count > best_ans_score:
                    best_ans_score = valid_count
                    best_ans_idx = i
            if best_ans_score > 0:
                ans_col_idx = best_ans_idx

        if q_col_idx is None:
            for i in range(len(df.columns)):
                if i in [ans_col_idx, sec_col_idx]:
                    continue
                has_digits = sum(1 for val in df.iloc[:, i] if bool(re.search(r"\d+", str(val))))
                if has_digits >= len(df) * 0.3:
                    q_col_idx = i
                    break

        if ans_col_idx is None:
            if len(df.columns) >= 3:
                q_col_idx = 0
                sec_col_idx = 1
                ans_col_idx = 2
            elif len(df.columns) == 2:
                q_col_idx = 0
                ans_col_idx = 1
            elif len(df.columns) == 1:
                ans_col_idx = 0

        if ans_col_idx is not None:
            for idx, row in df.iterrows():
                q_num_str = None
                q_num_int = idx + 1

                if q_col_idx is not None:
                    raw_q = str(row.iloc[q_col_idx])
                    digits = re.sub(r"[^\d]", "", raw_q)
                    if digits:
                        q_num_int = int(digits)
                        q_num_str = str(q_num_int)

                if not q_num_str:
                    q_num_str = str(q_num_int)

                ans_val = normalize_answer_val(row.iloc[ans_col_idx])
                if ans_val and q_num_str:
                    parsed_answers[q_num_str] = ans_val

                    if sec_col_idx is not None:
                        sec_raw = str(row.iloc[sec_col_idx]).strip().strip('"\'')
                        if sec_raw and sec_raw.lower() not in ["nan", "none", "null", "", "section", "sec"]:
                            if sec_raw not in detected_sections_map:
                                detected_sections_map[sec_raw] = []
                            detected_sections_map[sec_raw].append(q_num_int)

    # Use whichever pass yielded more answers
    if len(text_pass_answers) > len(parsed_answers):
        parsed_answers = text_pass_answers
        detected_sections_map = text_pass_sections


    if not parsed_answers:
        raise ValueError(
            f"Could not extract question answers from \"{filename}\". "
            "Please ensure the file has question numbers (e.g. Q01..Q1000) and option keys (A, B, C, D, or BONUS)."
        )

    # Build sections list if sections were detected
    if detected_sections_map:
        parsed_sections = []
        for sec_name, q_list in detected_sections_map.items():
            if q_list:
                parsed_sections.append({
                    "name": sec_name,
                    "q_start": min(q_list),
                    "q_end": max(q_list),
                })
        # Sort sections by starting question
        parsed_sections.sort(key=lambda s: s["q_start"])

    max_q = max([int(k) for k in parsed_answers.keys()]) if parsed_answers else 100
    calc_total = min(1000, max(max_q, len(parsed_answers)))

    return {
        "answers": parsed_answers,
        "default_rule": parsed_rules,
        "sections": parsed_sections,
        "exam_title": title,
        "total_parsed": len(parsed_answers),
        "total_questions": calc_total,
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
            "total_questions": 100,
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
    if "total_questions" not in key_doc:
        key_doc["total_questions"] = max(100, len(key_doc.get("answers", {})))
    return key_doc


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_or_update_answer_key(key_in: AnswerKeyUpdate):
    keys_col = get_collection("answer_keys")
    exams_col = get_collection("exams")
    existing = await keys_col.find_one({"exam_id": key_in.exam_id})

    # Determine total questions dynamically
    max_q_in_answers = max([int(k) for k in key_in.answers.keys() if k.isdigit()] or [100])
    total_q = max(key_in.total_questions or 100, max_q_in_answers, len(key_in.answers))

    doc_data = {
        "exam_id": key_in.exam_id,
        "exam_title": key_in.exam_title or "Standard OMR Assessment",
        "total_questions": total_q,
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

    # Sync total questions with exams table
    await exams_col.update_one({"_id": key_in.exam_id}, {"$set": {"total_questions": total_q, "updated_at": datetime.utcnow()}})

    doc_data["id"] = str(doc_data["_id"])
    return doc_data


@router.post("/upload-json", response_model=dict)
@router.post("/upload-file", response_model=dict)
async def upload_answer_key_file(
    exam_id: Optional[str] = Form("exam_standard_100q"),
    file: UploadFile = File(...),
):
    """
    Universal answer key file upload endpoint.
    Accepts JSON, CSV, Excel (.xlsx, .xls), and TXT files up to 1000 questions.
    """
    try:
        content = await file.read()
        parsed = parse_answer_key_from_bytes(content, file.filename or "uploaded_key.csv")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"File parsing error: {str(e)}")

    keys_col = get_collection("answer_keys")
    exams_col = get_collection("exams")
    target_exam_id = exam_id or "exam_standard_100q"
    existing = await keys_col.find_one({"exam_id": target_exam_id})

    # Preserve or update rules
    rules = parsed.get("default_rule")
    if not rules and existing and "default_rule" in existing:
        rules = existing["default_rule"]
    elif not rules:
        rules = {"correct": 4.0, "incorrect": -1.0, "unattempted": 0.0, "multi_mark": -1.0, "bonus": 4.0}

    # Use parsed sections or existing sections
    sections = parsed.get("sections")
    if not sections and existing and "sections" in existing:
        sections = existing["sections"]
    elif not sections and parsed["total_questions"] == 100:
        sections = [
            {"name": "Section A (Physics)", "q_start": 1, "q_end": 25},
            {"name": "Section B (Chemistry)", "q_start": 26, "q_end": 50},
            {"name": "Section C (Mathematics)", "q_start": 51, "q_end": 75},
            {"name": "Section D (Biology)", "q_start": 76, "q_end": 100},
        ]
    elif not sections:
        sections = []

    total_q = max(parsed.get("total_questions", 100), len(parsed["answers"]))

    doc_data = {
        "exam_id": target_exam_id,
        "exam_title": parsed.get("exam_title", "Uploaded Answer Key"),
        "total_questions": total_q,
        "answers": parsed["answers"],
        "default_rule": rules,
        "sections": sections,
        "updated_at": datetime.utcnow(),
    }

    if existing:
        await keys_col.update_one({"exam_id": target_exam_id}, {"$set": doc_data})
        doc_data["_id"] = existing["_id"]
    else:
        doc_data["_id"] = f"key_{target_exam_id}"
        doc_data["created_at"] = datetime.utcnow()
        await keys_col.insert_one(doc_data)

    # Sync exam total_questions
    await exams_col.update_one({"_id": target_exam_id}, {"$set": {"total_questions": total_q, "updated_at": datetime.utcnow()}})

    doc_data["id"] = str(doc_data["_id"])
    doc_data["message"] = f"Successfully loaded and saved {parsed['total_parsed']} answers from {file.filename}"
    return doc_data


@router.post("/paste-text", response_model=dict)
async def paste_answer_key_text(payload: RawTextKeyUpdate):
    """
    Directly parse pasted CSV / TSV / JSON / Key text and update the Master Answer Key.
    """
    if not payload.raw_text.strip():
        raise HTTPException(status_code=400, detail="Pasted text cannot be empty.")

    try:
        content = payload.raw_text.encode("utf-8")
        parsed = parse_answer_key_from_bytes(content, "pasted_key.csv")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse text: {str(e)}")

    keys_col = get_collection("answer_keys")
    exams_col = get_collection("exams")
    target_exam_id = payload.exam_id or "exam_standard_100q"
    existing = await keys_col.find_one({"exam_id": target_exam_id})

    rules = parsed.get("default_rule")
    if not rules and existing and "default_rule" in existing:
        rules = existing["default_rule"]
    elif not rules:
        rules = {"correct": 4.0, "incorrect": -1.0, "unattempted": 0.0, "multi_mark": -1.0, "bonus": 4.0}

    sections = parsed.get("sections")
    if not sections and existing and "sections" in existing:
        sections = existing["sections"]
    elif not sections and parsed["total_questions"] == 100:
        sections = [
            {"name": "Section A (Physics)", "q_start": 1, "q_end": 25},
            {"name": "Section B (Chemistry)", "q_start": 26, "q_end": 50},
            {"name": "Section C (Mathematics)", "q_start": 51, "q_end": 75},
            {"name": "Section D (Biology)", "q_start": 76, "q_end": 100},
        ]
    elif not sections:
        sections = []

    total_q = max(payload.total_questions or parsed.get("total_questions", 100), len(parsed["answers"]))

    doc_data = {
        "exam_id": target_exam_id,
        "exam_title": payload.exam_title or (existing.get("exam_title") if existing else "Standard OMR Assessment"),
        "total_questions": total_q,
        "answers": parsed["answers"],
        "default_rule": rules,
        "sections": sections,
        "updated_at": datetime.utcnow(),
    }

    if existing:
        await keys_col.update_one({"exam_id": target_exam_id}, {"$set": doc_data})
        doc_data["_id"] = existing["_id"]
    else:
        doc_data["_id"] = f"key_{target_exam_id}"
        doc_data["created_at"] = datetime.utcnow()
        await keys_col.insert_one(doc_data)

    await exams_col.update_one({"_id": target_exam_id}, {"$set": {"total_questions": total_q, "updated_at": datetime.utcnow()}})

    doc_data["id"] = str(doc_data["_id"])
    doc_data["message"] = f"Successfully parsed and applied {parsed['total_parsed']} question answers!"
    return doc_data


@router.get("/{exam_id}/export-csv")
async def export_answer_key_csv(exam_id: str):
    """Export the Master Answer Key as a clean 3-column CSV (Question, Section, Answer)."""
    keys_col = get_collection("answer_keys")
    doc = await keys_col.find_one({"exam_id": exam_id})

    answers = doc.get("answers", {}) if doc else generate_default_100q_answers()
    total_q = doc.get("total_questions", 100) if doc else 100
    sections = doc.get("sections", []) if doc else []

    output = StringIO()
    output.write("Question,Section,Answer\n")

    for i in range(1, total_q + 1):
        q_label = f"Q{i:02d}" if i < 100 else f"Q{i}"
        ans = answers.get(str(i), answers.get(f"{i:02d}", answers.get(f"Q{i:02d}", "A")))

        sec_name = "General"
        for s in sections:
            if s.get("q_start", 0) <= i <= s.get("q_end", 0):
                sec_name = s.get("name", "General")
                break

        output.write(f"{q_label},{sec_name},{ans}\n")

    from fastapi.responses import Response
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="Answer_Key_{exam_id}_{total_q}Q.csv"'},
    )

