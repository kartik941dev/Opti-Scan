import React, { useState, useEffect, useMemo } from 'react';
import {
  KeyRound,
  Save,
  Upload,
  Download,
  Sparkles,
  Check,
  RefreshCw,
  Trash2,
  FileText,
  CheckCircle2,
  AlertCircle,
  ClipboardPaste,
  X,
  Layers,
  Search,
  Sliders,
  ChevronLeft,
  ChevronRight,
  Plus,
  Edit2,
  HelpCircle,
  FileSpreadsheet,
} from 'lucide-react';
import { examsAPI, answerKeyAPI } from '../api/endpoints';

// Exact ground-truth dataset from the user's Excel screenshots
const SCREENSHOT_BENCHMARK_KEY = {
  // Section A (Physics) Q1 - Q25
  "1": "D", "2": "D", "3": "B", "4": "C", "5": "B", "6": "B", "7": "D", "8": "D", "9": "D", "10": "A",
  "11": "A", "12": "C", "13": "B", "14": "B", "15": "B", "16": "A", "17": "A", "18": "B", "19": "D", "20": "B",
  "21": "B", "22": "D", "23": "A", "24": "A", "25": "D",
  // Section B (Chemistry) Q26 - Q50
  "26": "D", "27": "C", "28": "C", "29": "B", "30": "A", "31": "B", "32": "B", "33": "B", "34": "C", "35": "C",
  "36": "A", "37": "C", "38": "D", "39": "D", "40": "D", "41": "A", "42": "C", "43": "C", "44": "B", "45": "B",
  "46": "B", "47": "D", "48": "D", "49": "A", "50": "A",
  // Section C (Mathematics) Q51 - Q75
  "51": "A", "52": "B", "53": "B", "54": "A", "55": "A", "56": "B", "57": "A", "58": "B", "59": "D", "60": "B",
  "61": "A", "62": "C", "63": "C", "64": "D", "65": "B", "66": "C", "67": "B", "68": "D", "69": "D", "70": "D",
  "71": "C", "72": "C", "73": "D", "74": "B", "75": "D",
  // Section D (Biology) Q76 - Q100
  "76": "B", "77": "A", "78": "A", "79": "D", "80": "D", "81": "D", "82": "B", "83": "C", "84": "C", "85": "D",
  "86": "D", "87": "D", "88": "B", "89": "A", "90": "A", "91": "C", "92": "A", "93": "C", "94": "B", "95": "A",
  "96": "A", "97": "D", "98": "C", "99": "B", "100": "C",
};

const DEFAULT_SECTIONS = [
  { name: 'Section A (Physics)', q_start: 1, q_end: 25 },
  { name: 'Section B (Chemistry)', q_start: 26, q_end: 50 },
  { name: 'Section C (Mathematics)', q_start: 51, q_end: 75 },
  { name: 'Section D (Biology)', q_start: 76, q_end: 100 },
];

const AnswerKeyPage = () => {
  const [exams, setExams] = useState([]);
  const [selectedExamId, setSelectedExamId] = useState('');
  const [totalQuestions, setTotalQuestions] = useState(100);
  const [enableSections, setEnableSections] = useState(true);
  const [sections, setSections] = useState(DEFAULT_SECTIONS);
  const [answers, setAnswers] = useState({});
  const [markingRule, setMarkingRule] = useState({
    correct: 4.0,
    incorrect: -1.0,
    unattempted: 0.0,
    multi_mark: -1.0,
    bonus: 4.0,
  });
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [notification, setNotification] = useState(null);
  const [pasteModalOpen, setPasteModalOpen] = useState(false);
  const [sectionsModalOpen, setSectionsModalOpen] = useState(false);
  const [pastedText, setPastedText] = useState('');
  const [activeTabRange, setActiveTabRange] = useState(0); // 0 = Q1-100, 1 = Q101-200, etc.
  const [searchQ, setSearchQ] = useState('');

  // Editing single section state
  const [newSecName, setNewSecName] = useState('');
  const [newSecStart, setNewSecStart] = useState(1);
  const [newSecEnd, setNewSecEnd] = useState(25);

  const options = ['A', 'B', 'C', 'D', 'BONUS'];
  const questionsPerPage = 100;

  useEffect(() => {
    loadExams();
  }, []);

  useEffect(() => {
    if (selectedExamId) {
      loadAnswerKey(selectedExamId);
    }
  }, [selectedExamId]);

  const loadExams = async () => {
    try {
      const res = await examsAPI.list();
      setExams(res.data);
      if (res.data.length > 0) {
        setSelectedExamId(res.data[0].id);
      }
    } catch (err) {
      console.error('Failed to load exams:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadAnswerKey = async (examId) => {
    try {
      const res = await answerKeyAPI.get(examId);
      const data = res.data;
      setAnswers(data.answers || {});
      if (data.default_rule) {
        setMarkingRule(data.default_rule);
      }
      if (data.total_questions) {
        setTotalQuestions(data.total_questions);
      }
      if (data.sections && data.sections.length > 0) {
        setSections(data.sections);
        setEnableSections(true);
      }
    } catch (err) {
      console.error('Failed to load answer key:', err);
    }
  };

  const getSelectedAnswer = (answersMap, qNum) => {
    if (!answersMap) return '';
    const numStr = String(qNum);
    const pad2 = String(qNum).padStart(2, '0');
    const pad3 = String(qNum).padStart(3, '0');
    return (
      answersMap[numStr] ||
      answersMap[pad2] ||
      answersMap[pad3] ||
      answersMap[qNum] ||
      answersMap[`Q${pad2}`] ||
      answersMap[`Q${numStr}`] ||
      answersMap[`q${pad2}`] ||
      answersMap[`q${numStr}`] ||
      ''
    );
  };

  const handleSelectOption = (qNum, opt) => {
    setAnswers((prev) => {
      const current = getSelectedAnswer(prev, qNum);
      const newMap = { ...prev };

      // Clear legacy keys for this question
      const numStr = String(qNum);
      const pad2 = String(qNum).padStart(2, '0');
      const pad3 = String(qNum).padStart(3, '0');
      delete newMap[numStr];
      delete newMap[pad2];
      delete newMap[pad3];
      delete newMap[qNum];
      delete newMap[`Q${pad2}`];
      delete newMap[`Q${numStr}`];
      delete newMap[`q${pad2}`];
      delete newMap[`q${numStr}`];

      // Toggle off if already selected, otherwise set option
      if (current !== opt) {
        newMap[numStr] = opt;
      }
      return newMap;
    });
  };

  // Ultra-robust client-side CSV/text parser
  const parseClientSideText = (text) => {
    const lines = text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
    const parsed = {};
    const detectedSecs = {};

    lines.forEach((line, idx) => {
      // Skip header lines
      if (idx === 0 && (line.toLowerCase().includes('question') || line.toLowerCase().includes('answer'))) {
        return;
      }

      // Split by comma, tab, semicolon, or pipe
      const parts = line.split(/[,\t;|]/).map((p) => p.trim().replace(/^["']|["']$/g, ''));
      if (parts.length >= 2) {
        let qNum = null;
        let ans = null;
        let sec = null;

        // Extract option from end
        for (let i = parts.length - 1; i >= 0; i--) {
          const val = parts[i].toUpperCase();
          if (['A', 'B', 'C', 'D', 'BONUS', '*'].includes(val)) {
            ans = val === '*' ? 'BONUS' : val;
            break;
          }
        }

        // Extract question number from start
        for (let i = 0; i < parts.length; i++) {
          const digits = parts[i].replace(/[^\d]/g, '');
          if (digits) {
            qNum = parseInt(digits, 10);
            break;
          }
        }

        // Extract section from middle
        if (parts.length >= 3 && parts[1]) {
          sec = parts[1];
        }

        if (!qNum) qNum = idx;

        if (qNum && ans) {
          parsed[String(qNum)] = ans;
          if (sec && !['section', 'sec', 'nan', 'none', 'null'].includes(sec.toLowerCase())) {
            if (!detectedSecs[sec]) detectedSecs[sec] = [];
            detectedSecs[sec].push(qNum);
          }
        }
      } else {
        // Regex format: Q1: A or 1. B
        const m = line.match(/^(?:Q(?:uestion)?)?\s*(\d+)[\.\:\,\-\t\s\=]+([A-D]|BONUS|\*)\b/i);
        if (m) {
          const qNum = parseInt(m[1], 10);
          const opt = m[2].toUpperCase() === '*' ? 'BONUS' : m[2].toUpperCase();
          parsed[String(qNum)] = opt;
        }
      }
    });

    const newSections = [];
    Object.entries(detectedSecs).forEach(([sName, qList]) => {
      newSections.push({
        name: sName,
        q_start: Math.min(...qList),
        q_end: Math.max(...qList),
      });
    });
    newSections.sort((a, b) => a.q_start - b.q_start);

    return { parsed, newSections };
  };

  const handleSave = async () => {
    try {
      await answerKeyAPI.save({
        exam_id: selectedExamId,
        total_questions: totalQuestions,
        answers,
        default_rule: markingRule,
        sections: enableSections ? sections : [],
      });
      setNotification({
        type: 'success',
        text: `Answer Key saved successfully with ${Object.keys(answers).length} questions configured (Total: ${totalQuestions} Qs).`,
      });
      setTimeout(() => setNotification(null), 4000);
    } catch (err) {
      setNotification({ type: 'error', text: `Failed to save answer key: ${err.message}` });
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    const inputElement = e.target;
    if (!file) return;

    setUploading(true);

    // Read client-side first for immediate responsive preview
    const reader = new FileReader();
    reader.onload = async (event) => {
      const fileText = event.target?.result;
      let clientParsedCount = 0;

      if (typeof fileText === 'string') {
        const { parsed, newSections } = parseClientSideText(fileText);
        clientParsedCount = Object.keys(parsed).length;
        if (clientParsedCount > 0) {
          setAnswers(parsed);
          const maxQ = Math.max(...Object.keys(parsed).map((k) => parseInt(k, 10)));
          if (maxQ > totalQuestions) {
            setTotalQuestions(Math.min(1000, maxQ));
          }
          if (newSections.length > 0) {
            setSections(newSections);
            setEnableSections(true);
          }
        }
      }

      // Also send to backend
      const formData = new FormData();
      formData.append('exam_id', selectedExamId || 'exam_standard_100q');
      formData.append('file', file);

      try {
        const res = await answerKeyAPI.uploadJson(formData);
        const newAnswers = res.data.answers || {};
        setAnswers(newAnswers);
        if (res.data.total_questions) {
          setTotalQuestions(res.data.total_questions);
        }
        if (res.data.sections && res.data.sections.length > 0) {
          setSections(res.data.sections);
          setEnableSections(true);
        }
        if (res.data.default_rule) {
          setMarkingRule(res.data.default_rule);
        }

        const secCount = res.data.sections?.length || 0;
        setNotification({
          type: 'success',
          text: `Successfully parsed & loaded ${Object.keys(newAnswers).length} questions${secCount > 0 ? ` across ${secCount} sections` : ''} from "${file.name}"!`,
        });
        setTimeout(() => setNotification(null), 5000);
      } catch (err) {
        if (clientParsedCount > 0) {
          setNotification({
            type: 'success',
            text: `Successfully loaded ${clientParsedCount} question answers from "${file.name}"!`,
          });
        } else {
          setNotification({
            type: 'error',
            text: `Could not parse file "${file.name}". Please ensure it has question numbers and options (A, B, C, D, BONUS).`,
          });
        }
        setTimeout(() => setNotification(null), 6000);
      } finally {
        setUploading(false);
        if (inputElement) inputElement.value = '';
      }
    };
    reader.readAsText(file);
  };

  const handleApplyPastedText = async () => {
    if (!pastedText.trim()) return;
    setUploading(true);

    const { parsed, newSections } = parseClientSideText(pastedText);
    const parsedCount = Object.keys(parsed).length;

    if (parsedCount > 0) {
      setAnswers(parsed);
      const maxQ = Math.max(...Object.keys(parsed).map((k) => parseInt(k, 10)));
      if (maxQ > totalQuestions) {
        setTotalQuestions(Math.min(1000, maxQ));
      }
      if (newSections.length > 0) {
        setSections(newSections);
        setEnableSections(true);
      }
    }

    try {
      const res = await answerKeyAPI.pasteText({
        exam_id: selectedExamId || 'exam_standard_100q',
        raw_text: pastedText,
        total_questions: totalQuestions,
      });
      const newAnswers = res.data.answers || {};
      setAnswers(newAnswers);
      if (res.data.total_questions) {
        setTotalQuestions(res.data.total_questions);
      }
      if (res.data.sections && res.data.sections.length > 0) {
        setSections(res.data.sections);
        setEnableSections(true);
      }
      setPasteModalOpen(false);
      setPastedText('');
      setNotification({
        type: 'success',
        text: `Successfully applied ${Object.keys(newAnswers).length} question answers from pasted CSV/Text!`,
      });
      setTimeout(() => setNotification(null), 5000);
    } catch (err) {
      setPasteModalOpen(false);
      if (parsedCount > 0) {
        setNotification({
          type: 'success',
          text: `Applied ${parsedCount} answers from pasted text.`,
        });
      } else {
        setNotification({
          type: 'error',
          text: `Failed to parse pasted text: ${err.message}`,
        });
      }
      setTimeout(() => setNotification(null), 5000);
    } finally {
      setUploading(false);
    }
  };

  const handleLoadScreenshotDemoKey = () => {
    setAnswers(SCREENSHOT_BENCHMARK_KEY);
    setTotalQuestions(100);
    setSections(DEFAULT_SECTIONS);
    setEnableSections(true);
    setActiveTabRange(0);
    setNotification({
      type: 'success',
      text: '✨ Loaded exact 100-Question dataset from screenshots (Physics Q1-25, Chemistry Q26-50, Math Q51-75, Biology Q76-100)!',
    });
    setTimeout(() => setNotification(null), 5000);
  };

  const handleCycleFill = () => {
    const opts = ['A', 'B', 'C', 'D'];
    const newAnswers = {};
    for (let i = 1; i <= totalQuestions; i++) {
      newAnswers[String(i)] = opts[(i - 1) % 4];
    }
    setAnswers(newAnswers);
    setNotification({ type: 'info', text: `Filled all ${totalQuestions} questions with cyclic ABCD pattern.` });
    setTimeout(() => setNotification(null), 3000);
  };

  const handleSetAll = (opt) => {
    const newAnswers = {};
    for (let i = 1; i <= totalQuestions; i++) {
      newAnswers[String(i)] = opt;
    }
    setAnswers(newAnswers);
    setNotification({ type: 'info', text: `Set all ${totalQuestions} questions to Option ${opt}.` });
    setTimeout(() => setNotification(null), 3000);
  };

  const handleClearAll = () => {
    setAnswers({});
    setNotification({ type: 'info', text: 'Cleared all question answer selections.' });
    setTimeout(() => setNotification(null), 3000);
  };

  const handleDownloadCsvTemplate = () => {
    let csvContent = 'Question,Section,Answer\n';
    for (let i = 1; i <= totalQuestions; i++) {
      const qNumStr = i < 100 ? `Q${String(i).padStart(2, '0')}` : `Q${i}`;
      let secName = '';
      if (enableSections && sections.length > 0) {
        const found = sections.find((s) => i >= s.q_start && i <= s.q_end);
        if (found) secName = found.name;
      }
      const ans = getSelectedAnswer(answers, i) || 'A';
      csvContent += `${qNumStr},${secName || 'General'},${ans}\n`;
    }

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `Answer_Key_${selectedExamId || 'exam'}_${totalQuestions}Q.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleAddSection = () => {
    if (!newSecName.trim()) return;
    const start = Math.max(1, parseInt(newSecStart, 10) || 1);
    const end = Math.min(totalQuestions, Math.max(start, parseInt(newSecEnd, 10) || start));

    const updated = [...sections, { name: newSecName.trim(), q_start: start, q_end: end }];
    updated.sort((a, b) => a.q_start - b.q_start);
    setSections(updated);
    setNewSecName('');
    setNewSecStart(end + 1);
    setNewSecEnd(Math.min(totalQuestions, end + 25));
  };

  const handleDeleteSection = (index) => {
    setSections(sections.filter((_, i) => i !== index));
  };

  const handleAutoSplitSections = (count) => {
    const perSec = Math.floor(totalQuestions / count);
    const names = ['Physics', 'Chemistry', 'Mathematics', 'Biology', 'General Knowledge', 'Aptitude'];
    const newSecs = [];

    for (let i = 0; i < count; i++) {
      const start = i * perSec + 1;
      const end = i === count - 1 ? totalQuestions : (i + 1) * perSec;
      const label = names[i] || `Section ${String.fromCharCode(65 + i)}`;
      newSecs.push({
        name: `Section ${String.fromCharCode(65 + i)} (${label})`,
        q_start: start,
        q_end: end,
      });
    }
    setSections(newSecs);
    setEnableSections(true);
  };

  const totalAnsweredCount = Array.from({ length: totalQuestions }, (_, i) => i + 1).filter((q) =>
    Boolean(getSelectedAnswer(answers, q))
  ).length;

  const totalPages = Math.ceil(totalQuestions / questionsPerPage);

  // Filter or paginate questions
  const displayedQuestionNumbers = useMemo(() => {
    if (searchQ.trim()) {
      const qNumSearch = parseInt(searchQ.trim(), 10);
      if (!isNaN(qNumSearch) && qNumSearch >= 1 && qNumSearch <= totalQuestions) {
        return [qNumSearch];
      }
    }
    const start = activeTabRange * questionsPerPage + 1;
    const end = Math.min(totalQuestions, (activeTabRange + 1) * questionsPerPage);
    return Array.from({ length: end - start + 1 }, (_, i) => start + i);
  }, [activeTabRange, totalQuestions, searchQ]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '14px',
        }}
      >
        <div>
          <h1 style={{ fontSize: '24px', margin: '0 0 4px 0', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <KeyRound size={24} color="var(--accent-cyan)" /> Master Answer Key & Assessment Config
          </h1>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: 0 }}>
            Configurable question limits (up to 1,000 Qs), optional subject sections, CSV & Excel upload
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            onClick={handleLoadScreenshotDemoKey}
            className="btn btn-secondary"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              border: '1px solid rgba(245, 158, 11, 0.4)',
              background: 'rgba(245, 158, 11, 0.1)',
              color: '#f59e0b',
            }}
            title="Load the exact 100-Question answer key from uploaded screenshots"
          >
            <Sparkles size={15} /> ✨ Screenshot Demo Key
          </button>

          <button
            onClick={() => setPasteModalOpen(true)}
            className="btn btn-secondary"
            style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            <ClipboardPaste size={15} /> Paste CSV / Text
          </button>

          <label
            className="btn btn-secondary"
            style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            <Upload size={15} /> {uploading ? 'Parsing...' : 'Upload File (CSV / JSON / Excel / TXT)'}
            <input
              type="file"
              accept=".json,.csv,.tsv,.xlsx,.xls,.txt"
              onChange={handleFileUpload}
              style={{ display: 'none' }}
              disabled={uploading}
            />
          </label>

          <button
            onClick={handleDownloadCsvTemplate}
            className="btn btn-secondary"
            style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
            title="Download CSV Template matching Screenshot format"
          >
            <Download size={15} /> Export CSV
          </button>

          <button onClick={handleSave} className="btn btn-primary" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Save size={16} /> Save Answer Key
          </button>
        </div>
      </div>

      {/* Notification Banner */}
      {notification && (
        <div
          style={{
            padding: '12px 16px',
            borderRadius: 'var(--radius-sm)',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            fontSize: '13px',
            fontWeight: 600,
            background:
              notification.type === 'success'
                ? 'rgba(16, 185, 129, 0.15)'
                : notification.type === 'error'
                ? 'rgba(239, 68, 68, 0.15)'
                : 'rgba(99, 102, 241, 0.15)',
            border: `1px solid ${
              notification.type === 'success'
                ? 'rgba(16, 185, 129, 0.3)'
                : notification.type === 'error'
                ? 'rgba(239, 68, 68, 0.3)'
                : 'rgba(99, 102, 241, 0.3)'
            }`,
            color:
              notification.type === 'success'
                ? '#10b981'
                : notification.type === 'error'
                ? '#ef4444'
                : '#6366f1',
          }}
        >
          {notification.type === 'success' ? (
            <CheckCircle2 size={18} />
          ) : notification.type === 'error' ? (
            <AlertCircle size={18} />
          ) : (
            <Sparkles size={18} />
          )}
          <span>{notification.text}</span>
        </div>
      )}

      {/* Settings Grid: Assessment, Question Limit, Optional Sections & Scoring Rules */}
      <div className="glass-card" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(290px, 1fr))', gap: '20px' }}>
        {/* Assessment & Total Questions */}
        <div>
          <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
            Active Assessment:
          </label>
          <select
            value={selectedExamId}
            onChange={(e) => setSelectedExamId(e.target.value)}
            className="input-field"
          >
            {exams.map((ex) => (
              <option key={ex.id} value={ex.id}>
                {ex.title} ({ex.code})
              </option>
            ))}
          </select>

          <div style={{ marginTop: '14px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)' }}>
                Total Questions Limit (1 - 1,000):
              </label>
              <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--accent-cyan)' }}>
                {totalQuestions} Questions
              </span>
            </div>

            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', alignItems: 'center' }}>
              {[25, 50, 100, 180, 200, 300, 500, 1000].map((preset) => (
                <button
                  key={preset}
                  type="button"
                  onClick={() => {
                    setTotalQuestions(preset);
                    setActiveTabRange(0);
                  }}
                  style={{
                    padding: '4px 8px',
                    borderRadius: '4px',
                    fontSize: '11px',
                    fontWeight: 600,
                    border: totalQuestions === preset ? '1px solid #6366f1' : '1px solid rgba(255, 255, 255, 0.1)',
                    background: totalQuestions === preset ? 'rgba(99, 102, 241, 0.2)' : 'rgba(255, 255, 255, 0.03)',
                    color: totalQuestions === preset ? '#ffffff' : 'var(--text-secondary)',
                    cursor: 'pointer',
                  }}
                >
                  {preset}Q
                </button>
              ))}
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <input
                  type="number"
                  min="1"
                  max="1000"
                  value={totalQuestions}
                  onChange={(e) => {
                    const val = parseInt(e.target.value, 10) || 1;
                    setTotalQuestions(Math.min(1000, Math.max(1, val)));
                  }}
                  className="input-field"
                  style={{ width: '70px', padding: '3px 6px', fontSize: '11px', height: '26px' }}
                  title="Custom question limit (up to 1,000)"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Section Management & Status */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Layers size={14} color="var(--accent-cyan)" /> Subject Sections:
            </label>
            <div style={{ display: 'flex', gap: '6px' }}>
              <button
                type="button"
                onClick={() => setEnableSections(!enableSections)}
                style={{
                  background: enableSections ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                  border: enableSections ? '1px solid #10b981' : '1px solid rgba(255, 255, 255, 0.1)',
                  color: enableSections ? '#10b981' : 'var(--text-muted)',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                {enableSections ? 'Sections: ON' : 'Sections: OPTIONAL (OFF)'}
              </button>

              <button
                type="button"
                onClick={() => setSectionsModalOpen(true)}
                className="btn btn-secondary"
                style={{ padding: '2px 8px', fontSize: '11px', height: '22px' }}
                title="Manage and configure subject sections"
              >
                <Sliders size={12} /> Configure
              </button>
            </div>
          </div>

          <div style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: '1.4' }}>
            {enableSections ? (
              <span>
                Configured with <b>{sections.length} Sections</b> (e.g. Physics, Chemistry, Math, Biology). Sections break down student scores and analytics.
              </span>
            ) : (
              <span>
                Continuous numbering mode active (Q1 to Q{totalQuestions}). Clean, unified grid layout without section boundaries.
              </span>
            )}
          </div>

          <div style={{ marginTop: '16px', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Configured Answers:</span>
            <span
              style={{
                fontSize: '13px',
                color: totalAnsweredCount === totalQuestions ? '#10b981' : 'var(--accent-cyan)',
                fontWeight: 700,
                background: 'rgba(255, 255, 255, 0.05)',
                padding: '3px 10px',
                borderRadius: '4px',
              }}
            >
              {totalAnsweredCount} / {totalQuestions} Questions Set
            </span>
          </div>
        </div>

        {/* Scoring Scheme Controls */}
        <div>
          <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
            Scoring Rules (+Correct / -Negative / Bonus):
          </label>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' }}>
            <div>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Correct (+Pts)</span>
              <input
                type="number"
                step="0.5"
                className="input-field"
                value={markingRule.correct}
                onChange={(e) => setMarkingRule({ ...markingRule, correct: parseFloat(e.target.value) || 0 })}
                style={{ height: '32px', fontSize: '12px' }}
              />
            </div>
            <div>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Incorrect (-Pts)</span>
              <input
                type="number"
                step="0.5"
                className="input-field"
                value={markingRule.incorrect}
                onChange={(e) => setMarkingRule({ ...markingRule, incorrect: parseFloat(e.target.value) || 0 })}
                style={{ height: '32px', fontSize: '12px' }}
              />
            </div>
            <div>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Unattempted</span>
              <input
                type="number"
                step="0.5"
                className="input-field"
                value={markingRule.unattempted}
                onChange={(e) => setMarkingRule({ ...markingRule, unattempted: parseFloat(e.target.value) || 0 })}
                style={{ height: '32px', fontSize: '12px' }}
              />
            </div>
            <div>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Bonus Mark</span>
              <input
                type="number"
                step="0.5"
                className="input-field"
                value={markingRule.bonus}
                onChange={(e) => setMarkingRule({ ...markingRule, bonus: parseFloat(e.target.value) || 0 })}
                style={{ height: '32px', fontSize: '12px' }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions & Navigation Toolbar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 18px',
          background: 'rgba(15, 23, 42, 0.6)',
          borderRadius: 'var(--radius-sm)',
          border: '1px solid var(--border-subtle)',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)' }}>Quick Fill:</span>
          <button onClick={handleCycleFill} className="btn btn-secondary" style={{ fontSize: '12px', padding: '5px 10px' }}>
            <RefreshCw size={12} /> Cyclic (A B C D)
          </button>
          <button onClick={() => handleSetAll('A')} className="btn btn-secondary" style={{ fontSize: '12px', padding: '5px 8px' }}>
            All A
          </button>
          <button onClick={() => handleSetAll('B')} className="btn btn-secondary" style={{ fontSize: '12px', padding: '5px 8px' }}>
            All B
          </button>
          <button onClick={() => handleSetAll('C')} className="btn btn-secondary" style={{ fontSize: '12px', padding: '5px 8px' }}>
            All C
          </button>
          <button onClick={() => handleSetAll('D')} className="btn btn-secondary" style={{ fontSize: '12px', padding: '5px 8px' }}>
            All D
          </button>
          <button onClick={handleClearAll} className="btn btn-danger" style={{ fontSize: '12px', padding: '5px 10px' }}>
            <Trash2 size={12} /> Clear
          </button>
        </div>

        {/* Jump / Search Box & Pagination if > 100 Qs */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ position: 'relative', width: '150px' }}>
            <Search size={13} style={{ position: 'absolute', left: '8px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Jump to Q#..."
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              className="input-field"
              style={{ paddingLeft: '26px', height: '28px', fontSize: '11px' }}
            />
          </div>

          {totalPages > 1 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <button
                disabled={activeTabRange === 0}
                onClick={() => setActiveTabRange((prev) => Math.max(0, prev - 1))}
                className="btn btn-secondary"
                style={{ padding: '4px 6px', height: '28px' }}
              >
                <ChevronLeft size={14} />
              </button>

              <span style={{ fontSize: '11px', color: 'var(--text-secondary)', padding: '0 4px' }}>
                Page {activeTabRange + 1} of {totalPages} (Q{activeTabRange * questionsPerPage + 1}–{Math.min(totalQuestions, (activeTabRange + 1) * questionsPerPage)})
              </span>

              <button
                disabled={activeTabRange >= totalPages - 1}
                onClick={() => setActiveTabRange((prev) => Math.min(totalPages - 1, prev + 1))}
                className="btn btn-secondary"
                style={{ padding: '4px 6px', height: '28px' }}
              >
                <ChevronRight size={14} />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Interactive Matrix Grid */}
      <div className="glass-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
          <h3 style={{ fontSize: '16px', margin: 0 }}>
            Master Answer Key Matrix ({totalQuestions} Questions Total)
          </h3>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            Showing Questions {displayedQuestionNumbers[0]} to {displayedQuestionNumbers[displayedQuestionNumbers.length - 1]}
          </span>
        </div>

        {/* Dynamic Multi-Column Grid */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))',
            gap: '16px',
          }}
        >
          {/* Chunk into columns of 25 */}
          {Array.from({ length: Math.ceil(displayedQuestionNumbers.length / 25) }, (_, colIndex) => {
            const colQuestions = displayedQuestionNumbers.slice(colIndex * 25, (colIndex + 1) * 25);
            if (colQuestions.length === 0) return null;

            const startQ = colQuestions[0];
            const endQ = colQuestions[colQuestions.length - 1];

            // Determine section header if enabled
            let secLabel = `Questions Q${startQ} - Q${endQ}`;
            if (enableSections && sections.length > 0) {
              const matchedSec = sections.find((s) => startQ >= s.q_start && startQ <= s.q_end);
              if (matchedSec) {
                secLabel = `${matchedSec.name} (Q${startQ}–Q${endQ})`;
              }
            }

            const colAnswered = colQuestions.filter((q) => Boolean(getSelectedAnswer(answers, q))).length;

            return (
              <div
                key={colIndex}
                style={{
                  background: 'rgba(15, 23, 42, 0.5)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '14px',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginBottom: '10px',
                    borderBottom: '1px solid var(--border-subtle)',
                    paddingBottom: '6px',
                  }}
                >
                  <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--accent-cyan)' }}>
                    {secLabel}
                  </span>
                  <span style={{ fontSize: '11px', fontWeight: 600, color: colAnswered === colQuestions.length ? '#10b981' : 'var(--text-muted)' }}>
                    {colAnswered}/{colQuestions.length} Set
                  </span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {colQuestions.map((qNum) => {
                    const selected = getSelectedAnswer(answers, qNum);
                    return (
                      <div
                        key={qNum}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '2px 4px',
                          borderRadius: '4px',
                          background: selected ? 'rgba(255, 255, 255, 0.03)' : 'transparent',
                        }}
                      >
                        <span
                          style={{
                            fontSize: '11px',
                            fontWeight: 600,
                            color: selected ? 'var(--text-primary)' : 'var(--text-muted)',
                            width: '40px',
                          }}
                        >
                          Q{qNum < 100 ? String(qNum).padStart(2, '0') : qNum}
                        </span>

                        <div style={{ display: 'flex', gap: '3px' }}>
                          {options.map((opt) => {
                            const isSelected =
                              selected === opt ||
                              (opt === 'BONUS' && (selected === '*' || selected === 'BONUS'));
                            return (
                              <button
                                key={opt}
                                type="button"
                                onClick={() => handleSelectOption(qNum, opt)}
                                style={{
                                  width: opt === 'BONUS' ? '44px' : '25px',
                                  height: '24px',
                                  borderRadius: '4px',
                                  fontSize: '10px',
                                  fontWeight: 700,
                                  border: isSelected
                                    ? '1px solid #6366f1'
                                    : '1px solid rgba(255, 255, 255, 0.08)',
                                  background: isSelected
                                    ? 'linear-gradient(135deg, #6366f1, #06b6d4)'
                                    : 'rgba(255, 255, 255, 0.03)',
                                  color: isSelected ? '#ffffff' : 'var(--text-secondary)',
                                  boxShadow: isSelected ? '0 0 8px rgba(99, 102, 241, 0.4)' : 'none',
                                  cursor: 'pointer',
                                  transition: 'all 0.12s ease',
                                }}
                              >
                                {opt}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Paste CSV / Text Modal */}
      {pasteModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 9999,
            backgroundColor: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(6px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px',
          }}
        >
          <div
            className="glass-card"
            style={{
              width: '100%',
              maxWidth: '680px',
              maxHeight: '90vh',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
              padding: '24px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <ClipboardPaste size={20} color="var(--accent-cyan)" />
                <h2 style={{ fontSize: '18px', margin: 0 }}>Paste Answer Key (CSV / Text / JSON up to 1000 Qs)</h2>
              </div>
              <button
                onClick={() => setPasteModalOpen(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  padding: '4px',
                }}
              >
                <X size={20} />
              </button>
            </div>

            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0 }}>
              Paste your question keys in any format (e.g., 3-column CSV with <code>Question,Section,Answer</code>, simple <code>Q01,D</code>, or <code>1: A</code>).
            </p>

            <textarea
              className="input-field"
              rows={12}
              value={pastedText}
              onChange={(e) => setPastedText(e.target.value)}
              placeholder="Question,Section,Answer&#10;Q01,Section A (Physics),D&#10;Q02,Section A (Physics),D&#10;Q03,Section A (Physics),B&#10;...&#10;Q100,Section D (Biology),C"
              style={{
                fontFamily: 'monospace',
                fontSize: '12px',
                resize: 'vertical',
                lineHeight: '1.5',
                whiteSpace: 'pre',
              }}
            />

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button
                onClick={() => setPasteModalOpen(false)}
                className="btn btn-secondary"
                disabled={uploading}
              >
                Cancel
              </button>
              <button
                onClick={handleApplyPastedText}
                className="btn btn-primary"
                disabled={uploading || !pastedText.trim()}
              >
                {uploading ? 'Parsing & Saving...' : 'Apply Answer Key'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Sections Configurator Modal */}
      {sectionsModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 9999,
            backgroundColor: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(6px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px',
          }}
        >
          <div
            className="glass-card"
            style={{
              width: '100%',
              maxWidth: '650px',
              maxHeight: '90vh',
              overflowY: 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
              padding: '24px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Layers size={20} color="var(--accent-cyan)" />
                <h2 style={{ fontSize: '18px', margin: 0 }}>Subject Sections & Breakdown Config</h2>
              </div>
              <button
                onClick={() => setSectionsModalOpen(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  padding: '4px',
                }}
              >
                <X size={20} />
              </button>
            </div>

            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0 }}>
              Configure subject sections for candidate sectional analysis (e.g. Physics, Chemistry, Math). Sections are optional.
            </p>

            {/* Quick Presets */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>Quick Split:</span>
              <button
                type="button"
                onClick={() => handleAutoSplitSections(2)}
                className="btn btn-secondary"
                style={{ fontSize: '11px', padding: '3px 8px' }}
              >
                Split in 2 Sections
              </button>
              <button
                type="button"
                onClick={() => handleAutoSplitSections(4)}
                className="btn btn-secondary"
                style={{ fontSize: '11px', padding: '3px 8px' }}
              >
                Split in 4 (PCB/M)
              </button>
              <button
                type="button"
                onClick={() => {
                  setSections(DEFAULT_SECTIONS);
                  setEnableSections(true);
                }}
                className="btn btn-secondary"
                style={{ fontSize: '11px', padding: '3px 8px' }}
              >
                Reset Default (4 Secs)
              </button>
            </div>

            {/* Sections List */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '8px' }}>
              {sections.length === 0 ? (
                <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>
                  No sections defined. All questions are graded continuously (Q1 to Q{totalQuestions}).
                </div>
              ) : (
                sections.map((sec, idx) => (
                  <div
                    key={idx}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '10px 14px',
                      background: 'rgba(255, 255, 255, 0.03)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-sm)',
                    }}
                  >
                    <div>
                      <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {sec.name}
                      </span>
                      <span style={{ marginLeft: '10px', fontSize: '11px', color: 'var(--accent-cyan)' }}>
                        Q{sec.q_start} – Q{sec.q_end} ({sec.q_end - sec.q_start + 1} Qs)
                      </span>
                    </div>

                    <button
                      type="button"
                      onClick={() => handleDeleteSection(idx)}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: 'var(--accent-danger)',
                        cursor: 'pointer',
                        padding: '4px',
                      }}
                      title="Delete section"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                ))
              )}
            </div>

            {/* Add Section Form */}
            <div
              style={{
                marginTop: '12px',
                padding: '12px',
                background: 'rgba(15, 23, 42, 0.6)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
              }}
            >
              <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--accent-cyan)' }}>
                Add New Section:
              </span>
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr auto', gap: '8px', alignItems: 'center' }}>
                <input
                  type="text"
                  placeholder="Section Name (e.g. Section E - Logic)"
                  value={newSecName}
                  onChange={(e) => setNewSecName(e.target.value)}
                  className="input-field"
                  style={{ height: '32px', fontSize: '12px' }}
                />
                <input
                  type="number"
                  placeholder="Start Q"
                  min="1"
                  max={totalQuestions}
                  value={newSecStart}
                  onChange={(e) => setNewSecStart(e.target.value)}
                  className="input-field"
                  style={{ height: '32px', fontSize: '12px' }}
                />
                <input
                  type="number"
                  placeholder="End Q"
                  min="1"
                  max={totalQuestions}
                  value={newSecEnd}
                  onChange={(e) => setNewSecEnd(e.target.value)}
                  className="input-field"
                  style={{ height: '32px', fontSize: '12px' }}
                />
                <button
                  type="button"
                  onClick={handleAddSection}
                  className="btn btn-primary"
                  style={{ height: '32px', padding: '0 12px', fontSize: '12px' }}
                >
                  <Plus size={14} /> Add
                </button>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '12px' }}>
              <button
                type="button"
                onClick={() => setSectionsModalOpen(false)}
                className="btn btn-primary"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AnswerKeyPage;
