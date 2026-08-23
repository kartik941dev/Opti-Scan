import React, { useState, useEffect } from 'react';
import { KeyRound, Save, Upload, Download, Sparkles, Check } from 'lucide-react';
import { examsAPI, answerKeyAPI } from '../api/endpoints';

const AnswerKeyPage = () => {
  const [exams, setExams] = useState([]);
  const [selectedExamId, setSelectedExamId] = useState('');
  const [answers, setAnswers] = useState({});
  const [markingRule, setMarkingRule] = useState({
    correct: 4.0,
    incorrect: -1.0,
    unattempted: 0.0,
    multi_mark: -1.0,
    bonus: 4.0,
  });
  const [loading, setLoading] = useState(true);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const options = ['A', 'B', 'C', 'D', 'BONUS'];

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
      setAnswers(res.data.answers || {});
      if (res.data.default_rule) {
        setMarkingRule(res.data.default_rule);
      }
    } catch (err) {
      console.error('Failed to load answer key:', err);
    }
  };

  const handleSelectOption = (qNum, opt) => {
    setAnswers((prev) => ({
      ...prev,
      [qNum]: opt,
    }));
  };

  const handleSave = async () => {
    try {
      await answerKeyAPI.save({
        exam_id: selectedExamId,
        answers,
        default_rule: markingRule,
      });
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err) {
      console.error('Failed to save answer key:', err);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('exam_id', selectedExamId);
    formData.append('file', file);

    try {
      const res = await answerKeyAPI.uploadJson(formData);
      setAnswers(res.data.answers);
      if (res.data.default_rule) {
        setMarkingRule(res.data.default_rule);
      }
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err) {
      console.error('Failed to upload answer key JSON:', err);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: '24px', margin: '0 0 4px 0' }}>Master Answer Key & Marking Scheme</h1>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: 0 }}>
            Define ground-truth question keys, negative penalties, and sectional weights
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <label className="btn btn-secondary" style={{ cursor: 'pointer' }}>
            <Upload size={15} /> Upload JSON Key
            <input type="file" accept=".json" onChange={handleFileUpload} style={{ display: 'none' }} />
          </label>
          <button onClick={handleSave} className="btn btn-primary">
            {savedSuccess ? <Check size={16} /> : <Save size={16} />}
            {savedSuccess ? 'Key Saved!' : 'Save Answer Key'}
          </button>
        </div>
      </div>

      {/* Exam Selector & Marking Rules Card */}
      <div className="glass-card" style={{ display: 'grid', gridTemplateColumns: '1.2fr 2fr', gap: '24px' }}>
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
        </div>

        {/* Scoring Scheme Controls */}
        <div>
          <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
            Scoring Rules (+Correct / -Negative / Bonus):
          </label>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px' }}>
            <div>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Correct (+Pts)</span>
              <input
                type="number"
                step="0.5"
                className="input-field"
                value={markingRule.correct}
                onChange={(e) => setMarkingRule({ ...markingRule, correct: parseFloat(e.target.value) })}
              />
            </div>
            <div>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Incorrect (-Pts)</span>
              <input
                type="number"
                step="0.5"
                className="input-field"
                value={markingRule.incorrect}
                onChange={(e) => setMarkingRule({ ...markingRule, incorrect: parseFloat(e.target.value) })}
              />
            </div>
            <div>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Unattempted</span>
              <input
                type="number"
                step="0.5"
                className="input-field"
                value={markingRule.unattempted}
                onChange={(e) => setMarkingRule({ ...markingRule, unattempted: parseFloat(e.target.value) })}
              />
            </div>
            <div>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Bonus Mark</span>
              <input
                type="number"
                step="0.5"
                className="input-field"
                value={markingRule.bonus}
                onChange={(e) => setMarkingRule({ ...markingRule, bonus: parseFloat(e.target.value) })}
              />
            </div>
          </div>
        </div>
      </div>

      {/* 100-Question Interactive Grid */}
      <div className="glass-card">
        <h3 style={{ fontSize: '16px', marginBottom: '16px' }}>Interactive Key Matrix (100 Questions)</h3>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '20px',
        }}>
          {[0, 1, 2, 3].map((colIdx) => {
            const secTitles = ['Section A (Physics)', 'Section B (Chemistry)', 'Section C (Mathematics)', 'Section D (Biology)'];
            const startQ = colIdx * 25 + 1;
            const endQ = (colIdx + 1) * 25;

            return (
              <div key={colIdx} style={{
                background: 'rgba(15, 23, 42, 0.5)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '14px',
              }}>
                <span style={{
                  fontSize: '12px',
                  fontWeight: 700,
                  color: 'var(--accent-cyan)',
                  display: 'block',
                  marginBottom: '12px',
                  borderBottom: '1px solid var(--border-subtle)',
                  paddingBottom: '6px',
                }}>
                  {secTitles[colIdx]} (Q{startQ}-{endQ})
                </span>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {Array.from({ length: 25 }, (_, i) => {
                    const qNum = startQ + i;
                    const selected = answers[String(qNum)] || 'A';

                    return (
                      <div key={qNum} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', width: '32px' }}>
                          Q{String(qNum).padStart(2, '0')}
                        </span>

                        <div style={{ display: 'flex', gap: '4px' }}>
                          {options.map((opt) => (
                            <button
                              key={opt}
                              onClick={() => handleSelectOption(String(qNum), opt)}
                              style={{
                                width: opt === 'BONUS' ? '46px' : '26px',
                                height: '26px',
                                borderRadius: '4px',
                                fontSize: '11px',
                                fontWeight: 700,
                                border: selected === opt ? '1px solid #6366f1' : '1px solid rgba(255, 255, 255, 0.1)',
                                background: selected === opt ? 'linear-gradient(135deg, #6366f1, #06b6d4)' : 'rgba(255, 255, 255, 0.04)',
                                color: selected === opt ? '#ffffff' : 'var(--text-secondary)',
                                cursor: 'pointer',
                                transition: 'all 0.15s ease',
                              }}
                            >
                              {opt}
                            </button>
                          ))}
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
    </div>
  );
};

export default AnswerKeyPage;
