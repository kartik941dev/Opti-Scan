import React, { useState, useEffect } from 'react';
import { Plus, Trash2, Edit3, FileCheck2, Calendar, Hash } from 'lucide-react';
import { examsAPI } from '../api/endpoints';

const formatDate = (dateStr) => {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return '—';
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
};

const ExamsPage = () => {
  const [exams, setExams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);

  // Form State
  const [title, setTitle] = useState('');
  const [code, setCode] = useState('');
  const [description, setDescription] = useState('');
  const [totalQuestions, setTotalQuestions] = useState(100);

  useEffect(() => {
    loadExams();
  }, []);

  const loadExams = async () => {
    try {
      const res = await examsAPI.list();
      setExams(res.data);
    } catch (err) {
      console.error('Failed to fetch exams:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await examsAPI.create({
        title,
        code,
        description,
        total_questions: parseInt(totalQuestions, 10),
      });
      setShowModal(false);
      setTitle('');
      setCode('');
      setDescription('');
      loadExams();
    } catch (err) {
      console.error('Failed to create exam:', err);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this exam and all its candidate submissions?')) return;
    try {
      await examsAPI.delete(id);
      loadExams();
    } catch (err) {
      console.error('Failed to delete exam:', err);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: '24px', margin: '0 0 4px 0' }}>Exams & Assessment Blueprints</h1>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: 0 }}>
            Configure examination parameters, question layouts, and metadata
          </p>
        </div>
        <button onClick={() => setShowModal(true)} className="btn btn-primary">
          <Plus size={16} /> Create New Assessment
        </button>
      </div>

      {/* Exams Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '20px' }}>
        {exams.map((ex) => (
          <div key={ex.id} className="glass-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                <span className="badge badge-success" style={{ fontSize: '11px' }}>
                  {ex.code}
                </span>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  {ex.total_questions} Questions
                </span>
              </div>

              <h3 style={{ fontSize: '18px', margin: '0 0 8px 0', color: 'var(--text-primary)' }}>
                {ex.title}
              </h3>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: 0, minHeight: '38px' }}>
                {ex.description || 'Standard multi-subject OMR assessment blueprint.'}
              </p>
            </div>

            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              paddingTop: '16px',
              borderTop: '1px solid var(--border-subtle)',
              marginTop: '16px',
            }}>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                Created: {formatDate(ex.created_at || Date.now())}
              </span>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  onClick={() => handleDelete(ex.id)}
                  className="btn btn-danger"
                  style={{ padding: '6px 10px', fontSize: '12px' }}
                  title="Delete Exam"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Create Exam Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '500px' }}>
            <h2 style={{ fontSize: '20px', margin: '0 0 16px 0' }}>Create Assessment Blueprint</h2>
            <form onSubmit={handleCreate} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
                  Exam Title
                </label>
                <input
                  type="text"
                  className="input-field"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Physics Midterm Examination 2026"
                  required
                />
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
                  Exam Code / Subject ID
                </label>
                <input
                  type="text"
                  className="input-field"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="e.g. PHY-2026-A"
                  required
                />
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
                  Description / Syllabus
                </label>
                <textarea
                  className="input-field"
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Brief exam overview..."
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)' }}>
                    Total Questions Limit (1 - 1,000)
                  </label>
                  <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--accent-primary)' }}>
                    {totalQuestions} Questions
                  </span>
                </div>
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', alignItems: 'center' }}>
                  {[25, 50, 100, 180, 200, 500, 1000].map((preset) => (
                    <button
                      key={preset}
                      type="button"
                      onClick={() => setTotalQuestions(preset)}
                      className={`toggle-pill ${totalQuestions === preset ? 'active' : 'inactive'}`}
                      style={{ padding: '4px 8px', fontSize: '11px' }}
                    >
                      {preset}Q
                    </button>
                  ))}
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
                    title="Question limit (up to 1,000)"
                  />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '12px' }}>
                <button type="button" onClick={() => setShowModal(false)} className="btn btn-secondary">
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Save Blueprint
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default ExamsPage;
