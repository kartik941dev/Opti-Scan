"""
Data schemas and models for OptiScan backend (MongoDB & Pydantic).
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class User(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    email: str
    full_name: str
    hashed_password: str
    role: str = "teacher"  # teacher, admin
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(populate_by_name=True)


class MarkingRule(BaseModel):
    correct: float = 4.0
    incorrect: float = -1.0
    unattempted: float = 0.0
    multi_mark: float = 0.0
    bonus: float = 4.0


class SectionConfig(BaseModel):
    name: str
    q_start: int
    q_end: int
    rule: Optional[MarkingRule] = None


class AnswerKeyModel(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    exam_id: str
    exam_title: str = "Standard OMR Assessment"
    answers: Dict[str, Union[str, List[str], None]] = Field(default_factory=dict)
    default_rule: MarkingRule = Field(default_factory=MarkingRule)
    sections: List[SectionConfig] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(populate_by_name=True)


class Exam(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    title: str
    code: str
    description: Optional[str] = ""
    total_questions: int = 100
    template_name: str = "omr_template.json"
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(populate_by_name=True)


class QuestionAudit(BaseModel):
    question_number: int
    selected_option: Optional[str] = None
    correct_answer: Optional[Union[str, List[str]]] = None
    status: str = "SINGLE_MARK"  # SINGLE_MARK, BLANK, MULTIPLE_MARKED, FAINT_MARK, BONUS
    is_correct: bool = False
    is_bonus: bool = False
    score_delta: float = 0.0
    confidence: float = 1.0


class Submission(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    exam_id: str
    student_id: str  # Roll Number
    roll_number_confidence: float = 1.0
    sheet_filename: str
    raw_image_url: Optional[str] = None
    annotated_image_url: Optional[str] = None
    total_score: float = 0.0
    max_score: float = 0.0
    percentage: float = 0.0
    accuracy_pct: float = 0.0
    total_attempted: int = 0
    total_correct: int = 0
    total_incorrect: int = 0
    total_unattempted: int = 0
    total_flagged: int = 0
    confidence_score: float = 1.0
    status: str = "SUCCESS"  # SUCCESS, FLAGGED_FOR_REVIEW, MANUALLY_VERIFIED, FAILED
    sectional_scores: Dict[str, Any] = Field(default_factory=dict)
    questions_audit: List[QuestionAudit] = Field(default_factory=list)
    processing_time_ms: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(populate_by_name=True)
