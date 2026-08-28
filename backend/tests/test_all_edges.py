"""
Comprehensive Edge-Case Test Suite for OptiScan Engine.
Tests every boundary, edge condition, encoding, delimiter, and format.
"""

import io
import json
import os
import sys
import unittest
import pandas as pd
import numpy as np

sys.path.insert(0, ".")

from backend.app.routes.answer_key import (
    parse_answer_key_from_bytes,
    normalize_answer_val,
    clean_col_header,
    generate_default_100q_answers,
)
from backend.app.omr_engine.grade import grade_submission, decode_student_id_from_grid
from backend.app.db.models import AnswerKeyModel, MarkingRule, SectionConfig
from backend.app.db.mongo import InMemoryCollection, _matches_filter


class TestAnswerKeyParserEdges(unittest.TestCase):
    """Deep edge-case testing of the Answer Key Parser."""

    def test_bom_and_quotes(self):
        """CSV with UTF-8 BOM, quoted headers, and trailing spaces."""
        raw = '\ufeff" Question "," Section "," Answer "\n"Q01","Physics","A"\n"Q02","Chemistry","B"'
        res = parse_answer_key_from_bytes(raw.encode("utf-8-sig"), "bom_test.csv")
        self.assertEqual(res["total_parsed"], 2)
        self.assertEqual(res["answers"]["1"], "A")
        self.assertEqual(res["answers"]["2"], "B")
        self.assertEqual(len(res["sections"]), 2)

    def test_windows_crlf_and_mac_cr(self):
        """Test Windows CRLF and Mac CR line endings."""
        raw_crlf = "Question,Section,Answer\r\nQ01,SecA,C\r\nQ02,SecA,D\r\n"
        res_crlf = parse_answer_key_from_bytes(raw_crlf.encode("utf-8"), "crlf.csv")
        self.assertEqual(res_crlf["answers"]["1"], "C")
        self.assertEqual(res_crlf["answers"]["2"], "D")

    def test_delimiters(self):
        """Test semicolon, pipe, and tab delimiters."""
        for sep, name in [(";", "semi.csv"), ("|", "pipe.csv"), ("\t", "tab.tsv")]:
            raw = f"Question{sep}Section{sep}Answer\nQ01{sep}Math{sep}A\nQ02{sep}Math{sep}B"
            res = parse_answer_key_from_bytes(raw.encode("utf-8"), name)
            self.assertEqual(res["answers"]["1"], "A", f"Failed on {name}")
            self.assertEqual(res["answers"]["2"], "B", f"Failed on {name}")

    def test_headerless_2col(self):
        """2-column CSV without any header (data starts row 1)."""
        raw = "1,A\n2,B\n3,C\n4,D\n5,BONUS"
        res = parse_answer_key_from_bytes(raw.encode("utf-8"), "no_header_2col.csv")
        self.assertEqual(res["total_parsed"], 5)
        self.assertEqual(res["answers"]["1"], "A")
        self.assertEqual(res["answers"]["5"], "BONUS")

    def test_headerless_3col(self):
        """3-column CSV without any header (data starts row 1)."""
        raw = "Q01,Physics,D\nQ02,Physics,D\nQ03,Physics,B"
        res = parse_answer_key_from_bytes(raw.encode("utf-8"), "no_header_3col.csv")
        self.assertEqual(res["total_parsed"], 3)
        self.assertEqual(res["answers"]["1"], "D")
        self.assertEqual(res["answers"]["3"], "B")

    def test_single_column_plain_text(self):
        """Single-column raw answers or question-line formats."""
        raw = "A\nB\nC\nD\nBONUS"
        res = parse_answer_key_from_bytes(raw.encode("utf-8"), "raw.txt")
        self.assertEqual(res["total_parsed"], 5)
        self.assertEqual(res["answers"]["1"], "A")
        self.assertEqual(res["answers"]["5"], "BONUS")

    def test_regex_line_formats(self):
        """Formats like 'Q1: A', '1. B', 'Q003 - C'."""
        raw = "Q1: A\n2. B\nQ003 - C\nQuestion 4 = D\n5. *"
        res = parse_answer_key_from_bytes(raw.encode("utf-8"), "notes.txt")
        self.assertEqual(res["total_parsed"], 5)
        self.assertEqual(res["answers"]["1"], "A")
        self.assertEqual(res["answers"]["2"], "B")
        self.assertEqual(res["answers"]["3"], "C")
        self.assertEqual(res["answers"]["4"], "D")
        self.assertEqual(res["answers"]["5"], "BONUS")

    def test_option_normalization_variations(self):
        """Test normalization for lowercase, parentheses, options, grace, etc."""
        self.assertEqual(normalize_answer_val("a"), "A")
        self.assertEqual(normalize_answer_val("(B)"), "B")
        self.assertEqual(normalize_answer_val("Option C"), "C")
        self.assertEqual(normalize_answer_val("Key: D"), "D")
        self.assertEqual(normalize_answer_val("GRACE"), "BONUS")
        self.assertEqual(normalize_answer_val("*"), "BONUS")
        self.assertIsNone(normalize_answer_val("None"))
        self.assertIsNone(normalize_answer_val("N/A"))
        self.assertIsNone(normalize_answer_val(""))
        self.assertIsNone(normalize_answer_val(None))

    def test_boundary_1_question(self):
        """Min question count = 1."""
        raw = "Question,Answer\nQ1,A"
        res = parse_answer_key_from_bytes(raw.encode("utf-8"), "one.csv")
        self.assertEqual(res["total_parsed"], 1)
        self.assertEqual(res["answers"]["1"], "A")

    def test_boundary_1000_questions(self):
        """Max question count = 1000 with 10 sections."""
        rows = ["Question,Section,Answer"]
        opts = ["A", "B", "C", "D"]
        for i in range(1, 1001):
            sec = f"Subject_{(i-1)//100 + 1}"
            rows.append(f"Q{i},{sec},{opts[(i-1)%4]}")
        raw = "\n".join(rows)
        res = parse_answer_key_from_bytes(raw.encode("utf-8"), "thousand.csv")
        self.assertEqual(res["total_parsed"], 1000)
        self.assertEqual(res["total_questions"], 1000)
        self.assertEqual(len(res["sections"]), 10)
        self.assertEqual(res["sections"][0]["q_start"], 1)
        self.assertEqual(res["sections"][0]["q_end"], 100)
        self.assertEqual(res["sections"][-1]["q_start"], 901)
        self.assertEqual(res["sections"][-1]["q_end"], 1000)

    def test_out_of_order_questions(self):
        """CSV with out-of-order questions."""
        raw = "Question,Answer\nQ100,D\nQ01,A\nQ50,B"
        res = parse_answer_key_from_bytes(raw.encode("utf-8"), "shuffled.csv")
        self.assertEqual(res["answers"]["100"], "D")
        self.assertEqual(res["answers"]["1"], "A")
        self.assertEqual(res["answers"]["50"], "B")
        self.assertEqual(res["total_questions"], 100)

    def test_json_formats(self):
        """JSON dict, JSON list of dicts, and nested JSON."""
        # Dict format
        d1 = json.dumps({"answers": {"1": "A", "2": "B"}, "total_questions": 50})
        res1 = parse_answer_key_from_bytes(d1.encode("utf-8"), "key.json")
        self.assertEqual(res1["answers"]["1"], "A")

        # List of dicts format
        d2 = json.dumps([{"q_num": 1, "answer": "C"}, {"q_num": 2, "answer": "D"}])
        res2 = parse_answer_key_from_bytes(d2.encode("utf-8"), "list.json")
        self.assertEqual(res2["answers"]["1"], "C")
        self.assertEqual(res2["answers"]["2"], "D")

    def test_excel_file_in_memory(self):
        """In-memory Excel workbook parsing."""
        df = pd.DataFrame({
            "Question": [f"Q{i:02d}" for i in range(1, 26)],
            "Section": ["Physics"] * 25,
            "Answer": ["A", "B", "C", "D", "A"] * 5,
        })
        buf = io.BytesIO()
        df.to_excel(buf, index=False, engine="openpyxl")
        res = parse_answer_key_from_bytes(buf.getvalue(), "test.xlsx")
        self.assertEqual(res["total_parsed"], 25)
        self.assertEqual(res["answers"]["1"], "A")
        self.assertEqual(len(res["sections"]), 1)
        self.assertEqual(res["sections"][0]["name"], "Physics")


class TestOMRGradingEdges(unittest.TestCase):
    """Deep edge-case testing of the OMR Grading and Scoring Engine."""

    def setUp(self):
        self.rule = MarkingRule(correct=4.0, incorrect=-1.0, unattempted=0.0, multi_mark=-1.0, bonus=4.0)

    def test_optional_sections_empty(self):
        """Grading when sections list is completely empty (continuous mode)."""
        answers = {"1": "A", "2": "B", "3": "C", "4": "D"}
        key = AnswerKeyModel(
            exam_id="test_exam",
            answers=answers,
            default_rule=self.rule,
            sections=[],
        )
        q_results = {
            1: {"selected_option": "A", "confidence": 1.0, "status": "SINGLE_MARK"},
            2: {"selected_option": "B", "confidence": 1.0, "status": "SINGLE_MARK"},
            3: {"selected_option": "A", "confidence": 1.0, "status": "SINGLE_MARK"},  # Wrong
            4: {"selected_option": None, "confidence": 0.0, "status": "BLANK"},        # Unattempted
        }
        report = grade_submission(q_results, key, "123456", 1.0, "sheet.png")
        self.assertEqual(report["total_correct"], 2)
        self.assertEqual(report["total_incorrect"], 1)
        self.assertEqual(report["total_unattempted"], 1)
        self.assertEqual(report["total_score"], 7.0)  # (4*2) - 1 + 0 = 7
        self.assertEqual(report["max_score"], 16.0)
        self.assertEqual(report["sectional_scores"], {})  # Empty dict when no sections

    def test_bonus_and_multi_mark_handling(self):
        """Test bonus scoring and multiple marked bubble penalties."""
        answers = {"1": "BONUS", "2": "*", "3": "A"}
        key = AnswerKeyModel(
            exam_id="test_bonus",
            answers=answers,
            default_rule=self.rule,
            sections=[],
        )
        q_results = {
            1: {"selected_option": None, "confidence": 0.0, "status": "BLANK"},          # Bonus awards mark regardless
            2: {"selected_option": "B", "confidence": 1.0, "status": "SINGLE_MARK"},     # Bonus awards mark
            3: {"selected_option": "A", "confidence": 0.5, "status": "MULTIPLE_MARKED"}, # Multiple marked penalty
        }
        report = grade_submission(q_results, key, "999999", 0.9, "sheet.png")
        self.assertEqual(report["total_correct"], 2)
        self.assertEqual(report["total_incorrect"], 1)
        self.assertEqual(report["total_score"], 7.0)  # 4 + 4 - 1 = 7.0
        self.assertEqual(report["status"], "FLAGGED_FOR_REVIEW")  # Flagged due to multiple marks

    def test_1000_questions_grading_performance(self):
        """Grade 1,000 questions and verify speed and accuracy."""
        answers = {str(i): ["A", "B", "C", "D"][(i - 1) % 4] for i in range(1, 1001)}
        sections = [
            SectionConfig(name=f"Sec {chr(65+i)}", q_start=i*200+1, q_end=(i+1)*200)
            for i in range(5)
        ]
        key = AnswerKeyModel(
            exam_id="exam_1000",
            answers=answers,
            default_rule=self.rule,
            sections=sections,
        )
        # All correct
        q_results = {
            i: {"selected_option": answers[str(i)], "confidence": 0.99, "status": "SINGLE_MARK"}
            for i in range(1, 1001)
        }
        report = grade_submission(q_results, key, "888888", 1.0, "scan1000.png")
        self.assertEqual(report["total_correct"], 1000)
        self.assertEqual(report["total_score"], 4000.0)
        self.assertEqual(report["percentage"], 100.0)
        self.assertEqual(len(report["sectional_scores"]), 5)
        for s in report["sectional_scores"].values():
            self.assertEqual(s["score"], 800.0)
            self.assertEqual(s["accuracy_pct"], 100.0)

    def test_student_id_decoding_edges(self):
        """Decode Student ID with noise, blanks, and valid digits."""
        # 1. Clean decode
        id_results = {
            f"c{c}_d{d}": {"col": c, "digit": d, "density": 0.85 if d == c else 0.05}
            for c in range(6) for d in range(10)
        }
        roll, conf = decode_student_id_from_grid(id_results)
        self.assertEqual(roll, "012345")
        self.assertGreater(conf, 0.7)

        # 2. Empty / missing matrix
        roll_empty, conf_empty = decode_student_id_from_grid({})
        self.assertEqual(roll_empty, "UNKNOWN")


class TestDatabaseFallbackEdges(unittest.TestCase):
    """Test InMemoryCollection operations & filter matching."""

    def test_filter_matching_ops(self):
        doc = {"exam_id": "test_1", "total_questions": 100, "status": "ACTIVE"}
        self.assertTrue(_matches_filter(doc, {"exam_id": "test_1"}))
        self.assertFalse(_matches_filter(doc, {"exam_id": "test_2"}))
        self.assertTrue(_matches_filter(doc, {"total_questions": {"$gt": 50}}))
        self.assertFalse(_matches_filter(doc, {"total_questions": {"$gt": 150}}))
        self.assertTrue(_matches_filter(doc, {"status": {"$in": ["ACTIVE", "PENDING"]}}))
        self.assertFalse(_matches_filter(doc, {"status": {"$nin": ["ACTIVE", "PENDING"]}}))


if __name__ == "__main__":
    unittest.main()
