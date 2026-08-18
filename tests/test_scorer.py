"""
Unit tests for Scoring Engine, Marking Schemes, and Answer Key Models (Phase 6).
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from src.models.answer_key import AnswerKey, MarkingRule, SectionConfig
from src.utils.exceptions import ScoringError


class TestScorer:
    """Test suite for Phase 6: Scoring Engine & Models."""

    def test_marking_rule_evaluation(self):
        """Step 6.1: Test MarkingRule score delta computation."""
        rule = MarkingRule(correct=4.0, incorrect=-1.0, unattempted=0.0, multi_mark=-1.0, bonus=4.0)

        # Correct
        assert rule.evaluate_mark(status="SINGLE_MARK", is_correct=True) == 4.0

        # Incorrect
        assert rule.evaluate_mark(status="SINGLE_MARK", is_correct=False) == -1.0

        # Blank / Unattempted
        assert rule.evaluate_mark(status="BLANK", is_correct=False) == 0.0

        # Multiple Marked
        assert rule.evaluate_mark(status="MULTIPLE_MARKED", is_correct=False) == -1.0

        # Bonus
        assert rule.evaluate_mark(status="BLANK", is_bonus=True) == 4.0
        assert rule.evaluate_mark(status="SINGLE_MARK", is_correct=False, is_bonus=True) == 4.0

    def test_section_config(self):
        """Step 6.1: Test SectionConfig boundaries and custom rules."""
        custom_rule = MarkingRule(correct=5.0, incorrect=-2.0)
        sec = SectionConfig(name="Mathematics", q_start=1, q_end=25, rule=custom_rule)

        assert sec.name == "Mathematics"
        assert sec.question_count == 25
        assert sec.contains(1) is True
        assert sec.contains(25) is True
        assert sec.contains(26) is False

        # Invalid range: q_start > q_end
        with pytest.raises(ValidationError):
            SectionConfig(name="Invalid", q_start=30, q_end=20)

    def test_answer_key_validation(self, tmp_path: Path):
        """Step 6.1: Test AnswerKey schema parsing, question overrides, and JSON serialization."""
        answers = {
            "1": "A",
            "2": ["B", "C"],
            "3": "BONUS",
            "4": "D",
        }
        sec1 = SectionConfig(name="Sec1", q_start=1, q_end=2, rule=MarkingRule(correct=3.0, incorrect=0.0))
        sec2 = SectionConfig(name="Sec2", q_start=3, q_end=4)

        ak = AnswerKey(
            exam_id="TEST_EXAM_01",
            exam_title="Test Exam",
            answers_map=answers,
            marking_rules=MarkingRule(correct=4.0, incorrect=-1.0),
            sections=[sec1, sec2],
        )

        assert ak.exam_id == "TEST_EXAM_01"
        assert ak.total_questions == 4
        assert ak.get_correct_answer(1) == "A"
        assert ak.get_correct_answer(2) == ["B", "C"]
        assert ak.get_correct_answer(3) == "BONUS"

        # Section rule resolution
        assert ak.get_rule_for_question(1).correct == 3.0
        assert ak.get_rule_for_question(1).incorrect == 0.0
        assert ak.get_rule_for_question(3).correct == 4.0  # Falls back to default

        # JSON roundtrip
        out_file = tmp_path / "test_ak.json"
        ak.save_to_json(out_file)
        assert out_file.exists()

        loaded_ak = AnswerKey.load_from_json(out_file)
        assert loaded_ak.exam_id == "TEST_EXAM_01"
        assert loaded_ak.get_correct_answer(2) == ["B", "C"]

    def test_standard_answer_key_file(self):
        """Step 6.1: Verify config/answer_key.json exists and parses correctly."""
        ak_path = Path("config/answer_key.json")
        assert ak_path.exists(), "config/answer_key.json must exist"

        ak = AnswerKey.load_from_json(ak_path)
        assert ak.total_questions == 100
        assert len(ak.sections) == 4
        assert ak.get_correct_answer(1) == "A"
        assert ak.get_correct_answer(50) == ["A", "B"]
        assert ak.get_correct_answer(100) == "BONUS"

        # Check section C custom negative marking rule (-2.0)
        rule_c = ak.get_rule_for_question(60)
        assert rule_c.incorrect == -2.0


def test_answer_key_validation(tmp_path: Path):
    """Standalone test entrypoint matching PROJECT.md Step 6.1 command."""
    TestScorer().test_answer_key_validation(tmp_path)
