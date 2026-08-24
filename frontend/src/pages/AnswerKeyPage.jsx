import React, { useState, useEffect } from 'react';
import { KeyRound, Save, Upload, Download, Sparkles, Check, RefreshCw, Trash2, FileText, CheckCircle2, AlertCircle } from 'lucide-react';
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
  const [uploading, setUploading] = useState(false);
  const [notification, setNotification] = useState(null);

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
    setAnswers((prev) => {
      const current = prev[String(qNum)];
      // If clicking already selected option, keep or toggle
      return {
        ...prev,
        [String(qNum)]: opt,
      };
    });
  };

  const handleSave = async () => {
    try {
      await answerKeyAPI.save({
        exam_id: selectedExamId,
        answers,
        default_rule: markingRule,
      });
      setNotification({ type: 'success', text: `Answer Key saved successfully with ${Object.keys(answers).length} questions configured.` });
      setTimeout(() => setNotification(null), 4000);
    } catch (err) {
      setNotification({ type: 'error', text: `Failed to save answer key: ${err.message}` });
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('exam_id', selectedExamId);
    formData.append('file', file);

    try {
      const res = await answerKeyAPI.uploadJson(formData);
      const newAnswers = res.data.answers || {};
      setAnswers(newAnswers);
      if (res.data.default_rule) {
        setMarkingRule(res.data.default_rule);
      }
      setNotification({
        type: 'success',
        text: `Loaded ${Object.keys(newAnswers).length} correct answers from "${file.name}"!`,
      });
      setTimeout(() => setNotification(null), 5000);
    } catch (err) {
      setNotification({
        type: 'error',
        text: err.response?.data?.detail || `Error parsing file "${file.name}". Please ensure it contains question numbers and option keys.`,
      });
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handleCycleFill = () => {
    const opts = ['A', 'B', 'C', 'D'];
    const newAnswers = {};
    for (let i = 1; i <= 100; i++) {
      newAnswers[String(i)] = opts[(i - 1) % 4];
    }
    setAnswers(newAnswers);
    setNotification({ type: 'info', text: 'Filled all 100 questions with cyclic ABCD pattern.' });
    setTimeout(() => setNotification(null), 3000);
  };

  const handleSetAll = (opt) => {
    const newAnswers = {};
    for (let i = 1; i <= 100; i++) {
      newAnswers[String(i)] = opt;
    }
    setAnswers(newAnswers);
    setNotification({ type: 'info', text: `Set all 100 questions to Option ${opt}.` });
    setTimeout(() => setNotification(null), 3000);
  };

  const handleClearAll = () => {
    setAnswers({});
    setNotification({ type: 'info', text: 'Cleared all question answer selections.' });
    setTimeout(() => setNotification(null), 3000);
  };

  const totalAnswered = Object.keys(answers).length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '14px' }}>
        <div>
          <h1 style={{ fontSize: '24px', margin: '0 0 4px 0' }}>Master Answer Key & Marking Scheme</h1>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: 0 }}>
            Upload or define ground-truth question keys (JSON, CSV, Excel, TXT) and scoring penalties
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <label className="btn btn-secondary" style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Upload size={15} /> {uploading ? 'Parsing...' : 'Upload Answer Key (JSON / CSV / Excel / TXT)'}
            <input
              type="file"
              accept=".json,.csv,.tsv,.xlsx,.xls,.txt"
              onChange={handleFileUpload}
              style={{ display: 'none' }}
              disabled={uploading}
            />
          </label>
          <button onClick={handleSave} className="btn btn-primary">
            <Save size={16} /> Save Answer Key
          </button>
        </div>
      </div>

      {/* Notification Banner */}
      {notification && (
        <div style={{
          padding: '12px 16px',
          borderRadius: 'var(--radius-sm)',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          fontSize: '13px',
          fontWeight: 600,
          background: notification.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : notification.type === 'error' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(99, 102, 241, 0.15)',
          border: `1px solid ${notification.type === 'success' ? 'rgba(16, 185, 129, 0.3)' : notification.type === 'error' ? 'rgba(239, 68, 68, 0.3)' : 'rgba(99, 102, 241, 0.3)'}`,
          color: notification.type === 'success' ? '#10b981' : notification.type === 'error' ? '#ef4444' : '#6366f1',
        }}>
          {notification.type === 'success' ? <CheckCircle2 size={18} /> : notification.type === 'error' ? <AlertCircle size={18} /> : <Sparkles size={18} />}
          <span>{notification.text}</span>
        </div>
      )}

      {/* Assessment Selector & Scoring Rules Card */}
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

          <div style={{ marginTop: '14px', fontSize: '12px', color: 'var(--text-muted)' }}>
            Configured Keys: <b style={{ color: 'var(--accent-cyan)' }}>{totalAnswered} / 100 Questions</b>
          </div>
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
                onChange={(e) => setMarkingRule({ ...markingRule, correct: parseFloat(e.target.value) || 0 })}
              />
            </div>
            <div>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Incorrect (-Pts)</span>
              <input
                type="number"
                step="0.5"
                className="input-field"
                value={markingRule.incorrect}
                onChange={(e) => setMarkingRule({ ...markingRule, incorrect: parseFloat(e.target.value) || 0 })}
              />
            </div>
            <div>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Unattempted</span>
              <input
                type="number"
                step="0.5"
                className="input-field"
                value={markingRule.unattempted}
                onChange={(e) => setMarkingRule({ ...markingRule, unattempted: parseFloat(e.target.value) || 0 })}
              />
            </div>
            <div>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Bonus Mark</span>
              <input
                type="number"
                step="0.5"
                className="input-field"
                value={markingRule.bonus}
                onChange={(e) => setMarkingRule({ ...markingRule, bonus: parseFloat(e.target.value) || 0 })}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions Toolbar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 18px',
        background: 'rgba(15, 23, 42, 0.6)',
        borderRadius: 'var(--radius-sm)',
        border: '1px solid var(--border-subtle)',
        flexWrap: 'wrap',
        gap: '10px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)' }}>Quick Fill Actions:</span>
          <button onClick={handleCycleFill} className="btn btn-secondary" style={{ fontSize: '12px', padding: '6px 12px' }}>
            <RefreshCw size={13} /> Cycle Pattern (A B C D)
          </button>
          <button onClick={() => handleSetAll('A')} className="btn btn-secondary" style={{ fontSize: '12px', padding: '6px 10px' }}>All A</button>
          <button onClick={() => handleSetAll('B')} className="btn btn-secondary" style={{ fontSize: '12px', padding: '6px 10px' }}>All B</button>
          <button onClick={() => handleSetAll('C')} className="btn btn-secondary" style={{ fontSize: '12px', padding: '6px 10px' }}>All C</button>
          <button onClick={() => handleSetAll('D')} className="btn btn-secondary" style={{ fontSize: '12px', padding: '6px 10px' }}>All D</button>
        </div>

        <button onClick={handleClearAll} className="btn btn-danger" style={{ fontSize: '12px', padding: '6px 12px' }}>
          <Trash2 size={13} /> Clear All
        </button>
      </div>

      {/* 100-Question Interactive Grid */}
      <div className="glass-card">
        <h3 style={{ fontSize: '16px', marginBottom: '16px' }}>
          Master Answer Key Matrix (100 Questions)
        </h3>

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
                    const selected = answers[String(qNum)] || answers[qNum] || '';

                    return (
                      <div key={qNum} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span style={{
                          fontSize: '12px',
                          fontWeight: 600,
                          color: selected ? 'var(--text-primary)' : 'var(--text-muted)',
                          width: '32px',
                        }}>
                          Q{String(qNum).padStart(2, '0')}
                        </span>

                        <div style={{ display: 'flex', gap: '4px' }}>
                          {options.map((opt) => {
                            const isSelected = selected === opt || (opt === 'BONUS' && (selected === '*' || selected === 'BONUS'));
                            return (
                              <button
                                key={opt}
                                onClick={() => handleSelectOption(String(qNum), opt)}
                                style={{
                                  width: opt === 'BONUS' ? '46px' : '26px',
                                  height: '26px',
                                  borderRadius: '4px',
                                  fontSize: '11px',
                                  fontWeight: 700,
                                  border: isSelected ? '1px solid #6366f1' : '1px solid rgba(255, 255, 255, 0.08)',
                                  background: isSelected ? 'linear-gradient(135deg, #6366f1, #06b6d4)' : 'rgba(255, 255, 255, 0.03)',
                                  color: isSelected ? '#ffffff' : 'var(--text-secondary)',
                                  boxShadow: isSelected ? '0 0 10px rgba(99, 102, 241, 0.5)' : 'none',
                                  cursor: 'pointer',
                                  transition: 'all 0.15s ease',
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
    </div>
  );
};

export default AnswerKeyPage;
