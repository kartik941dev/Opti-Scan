"""
Pydantic data models for Answer Keys, Section Configurations, and Marking Schemes (Phase 6).
"""

import json
from pathlib import Path
from typing import Any, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.utils.exceptions import ScoringError
from src.utils.logger import get_logger

logger = get_logger("models.answer_key")


class MarkingRule(BaseModel):
    """
    Grading scheme specifying positive, negative, unattempted, and penalty weights.
    """
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    correct: float = Field(default=4.0, description="Marks awarded for correct answer")
    incorrect: float = Field(default=-1.0, description="Marks deducted for incorrect answer")
    unattempted: float = Field(default=0.0, description="Marks awarded for blank/unattempted question")
    multi_mark: float = Field(default=-1.0, description="Marks for ambiguous multiple marked question")
    bonus: float = Field(default=4.0, description="Marks awarded for dropped/bonus questions")

    def evaluate_mark(
        self,
        status: str,
        is_correct: bool = False,
        is_bonus: bool = False,
    ) -> float:
        """
        Evaluate score delta for a single question based on outcome status.
        """
        if is_bonus:
            return float(self.bonus)
        if status == "BLANK":
            return float(self.unattempted)
        if status == "MULTIPLE_MARKED":
            return float(self.multi_mark)
        if is_correct:
            return float(self.correct)
        return float(self.incorrect)


class SectionConfig(BaseModel):
    """
    Subject/section boundary definition with optional per-section marking rule overrides.
    """
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    name: str = Field(..., description="Section name (e.g. 'Physics', 'Mathematics')")
    q_start: int = Field(..., ge=1, description="Start question number (inclusive)")
    q_end: int = Field(..., ge=1, description="End question number (inclusive)")
    rule: Optional[MarkingRule] = Field(default=None, description="Optional custom marking rule for this section")

    @model_validator(mode="after")
    def validate_range(self) -> "SectionConfig":
        if self.q_start > self.q_end:
            raise ValueError(f"Section '{self.name}' q_start ({self.q_start}) cannot exceed q_end ({self.q_end})")
        return self

    def contains(self, q_num: int) -> bool:
        return self.q_start <= q_num <= self.q_end

    @property
    def question_count(self) -> int:
        return self.q_end - self.q_start + 1


class AnswerKey(BaseModel):
    """
    Master answer key schema containing ground-truth answers, marking rules, and section layouts.
    """
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    exam_id: str = Field(default="EXAM_STANDARD_100Q", description="Unique exam/test identifier")
    exam_title: str = Field(default="Standard OMR Assessment", description="Descriptive exam title")
    answers_map: dict[str, Union[str, list[str], None]] = Field(
        default_factory=dict,
        alias="answers",
        description="Map of question numbers (as strings) to correct option(s) (e.g. 'A', ['B', 'C'], or 'BONUS')",
    )
    marking_rules: MarkingRule = Field(
        default_factory=MarkingRule,
        alias="default_rule",
        description="Default exam marking rule",
    )
    sections: list[SectionConfig] = Field(
        default_factory=list,
        description="List of section configurations",
    )

    @field_validator("answers_map", mode="before")
    @classmethod
    def normalize_answers_map(cls, v: Any) -> dict[str, Any]:
        if not isinstance(v, dict):
            raise ValueError(f"answers_map must be a dictionary, got {type(v).__name__}")
        normalized = {}
        for q_key, ans_val in v.items():
            str_key = str(q_key)
            if isinstance(ans_val, str):
                normalized[str_key] = ans_val.strip().upper()
            elif isinstance(ans_val, list):
                normalized[str_key] = [str(x).strip().upper() for x in ans_val]
            elif ans_val is None:
                normalized[str_key] = None
            else:
                normalized[str_key] = str(ans_val).strip().upper()
        return normalized

    @property
    def total_questions(self) -> int:
        if self.answers_map:
            try:
                keys = [int(k) for k in self.answers_map.keys() if k.isdigit()]
                return max(keys) if keys else len(self.answers_map)
            except Exception:
                return len(self.answers_map)
        return sum(s.question_count for s in self.sections) if self.sections else 0

    def get_correct_answer(self, q_num: int) -> Optional[Union[str, list[str]]]:
        """Lookup correct answer for a 1-indexed question number."""
        return self.answers_map.get(str(q_num))

    def get_rule_for_question(self, q_num: int) -> MarkingRule:
        """Lookup applicable marking rule for a question, checking section overrides first."""
        for sec in self.sections:
            if sec.contains(q_num) and sec.rule is not None:
                return sec.rule
        return self.marking_rules

    def get_section_for_question(self, q_num: int) -> Optional[SectionConfig]:
        """Lookup section containing the specified question number."""
        for sec in self.sections:
            if sec.contains(q_num):
                return sec
        return None

    def save_to_json(self, output_path: Union[str, Path]) -> None:
        """Serialize AnswerKey configuration to a JSON file."""
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2, by_alias=True))
        logger.info("Saved answer key '%s' (%d answers) to %s", self.exam_id, len(self.answers_map), out_p)

    @classmethod
    def load_from_json(cls, file_path: Union[str, Path]) -> "AnswerKey":
        """Load and parse AnswerKey configuration from a JSON file."""
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            raise ScoringError(f"Answer key JSON file does not exist: {path}", details={"file_path": str(path)})
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(**data)
        except Exception as e:
            if isinstance(e, ScoringError):
                raise
            raise ScoringError(f"Failed to load answer key from '{path}': {e}", details={"error": str(e)}) from e
