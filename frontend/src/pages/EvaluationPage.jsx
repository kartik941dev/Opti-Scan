import React, { useState, useEffect } from 'react';
import {
  UploadCloud,
  FileImage,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Eye,
  Download,
  Clock,
} from 'lucide-react';
import SheetViewerModal from '../components/SheetViewerModal';
import { examsAPI, omrAPI, resultsAPI } from '../api/endpoints';

const EvaluationPage = () => {
  const [exams, setExams] = useState([]);
  const [selectedExamId, setSelectedExamId] = useState('');
  const [submissions, setSubmissions] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [inspectingSub, setInspectingSub] = useState(null);
  const [dragActive, setDragActive] = useState(false);

  useEffect(() => {
    loadExams();
  }, []);

  useEffect(() => {
    if (selectedExamId) {
      loadSubmissions(selectedExamId);
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
    }
  };

  const loadSubmissions = async (examId) => {
    try {
      const res = await resultsAPI.getSubmissions(examId);
      setSubmissions(res.data);
    } catch (err) {
      console.error('Failed to load submissions:', err);
    }
  };

  const handleFiles = async (files) => {
    if (!files || files.length === 0 || !selectedExamId) return;

    setUploading(true);
    setProgress(20);

    const formData = new FormData();
    formData.append('exam_id', selectedExamId);
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }

    try {
      setProgress(50);
      await omrAPI.uploadBatch(formData);
      setProgress(100);
      await loadSubmissions(selectedExamId);
    } catch (err) {
      console.error('Failed to upload OMR sheets:', err);
    } finally {
      setTimeout(() => {
        setUploading(false);
        setProgress(0);
      }, 600);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleDemoGenerate = async () => {
    if (!selectedExamId) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('exam_id', selectedExamId);
      await omrAPI.loadDemoSheets(formData);
      await loadSubmissions(selectedExamId);
    } catch (err) {
      console.error('Failed to load demo sheets:', err);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: '24px', margin: '0 0 4px 0' }}>Batch Sheet Ingestion & Live Evaluation</h1>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: 0 }}>
            Upload raw scanner images or smartphone captures for automated grading
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <select
            value={selectedExamId}
            onChange={(e) => setSelectedExamId(e.target.value)}
            className="input-field"
            style={{ width: '320px', padding: '8px 12px' }}
          >
            {exams.map((ex) => (
              <option key={ex.id} value={ex.id}>
                {ex.title} ({ex.code})
              </option>
            ))}
          </select>

          <button onClick={handleDemoGenerate} className="btn btn-secondary" disabled={uploading}>
            <Sparkles size={16} color="#f59e0b" />
            {uploading ? 'Processing...' : '✨ Load 5 Sample Sheets'}
          </button>
        </div>
      </div>

      {/* Drag and Drop Zone */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        style={{
          border: dragActive ? '2px dashed #6366f1' : '2px dashed rgba(255, 255, 255, 0.15)',
          borderRadius: 'var(--radius-lg)',
          background: dragActive ? 'rgba(99, 102, 241, 0.08)' : 'rgba(15, 23, 42, 0.6)',
          backdropFilter: 'blur(12px)',
          padding: '48px 24px',
          textAlign: 'center',
          transition: 'all 0.2s ease',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '14px',
        }}
      >
        <div style={{
          width: '56px',
          height: '56px',
          borderRadius: '16px',
          background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(6, 182, 212, 0.2))',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <UploadCloud size={28} color="#6366f1" />
        </div>

        <div>
          <h3 style={{ fontSize: '18px', margin: '0 0 6px 0' }}>
            Drag and drop OMR sheet scans here
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: 0 }}>
            Supports JPG, PNG, TIFF, or Multi-Page PDF files (up to 200MB per batch)
          </p>
        </div>

        <label className="btn btn-primary" style={{ cursor: 'pointer', marginTop: '6px' }}>
          Browse Files
          <input
            type="file"
            multiple
            accept="image/png,image/jpeg,image/jpg,image/tiff,application/pdf"
            onChange={(e) => handleFiles(e.target.files)}
            style={{ display: 'none' }}
          />
        </label>
      </div>

      {/* Progress Bar */}
      {uploading && (
        <div className="glass-card" style={{ padding: '16px 20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '13px' }}>
            <span style={{ fontWeight: 600, color: 'var(--accent-cyan)' }}>
              Executing Computer Vision Alignment & Decision Engine...
            </span>
            <span>{progress}%</span>
          </div>
          <div style={{ width: '100%', height: '6px', background: 'rgba(255, 255, 255, 0.1)', borderRadius: '3px', overflow: 'hidden' }}>
            <div style={{ width: `${progress}%`, height: '100%', background: 'var(--gradient-brand)', transition: 'width 0.3s ease' }} />
          </div>
        </div>
      )}

      {/* Results Table */}
      <div className="glass-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <h3 style={{ fontSize: '18px', margin: 0 }}>
            Graded Submissions ({submissions.length})
          </h3>
        </div>

        {submissions.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '36px 0', color: 'var(--text-muted)' }}>
            No submissions evaluated yet for this assessment.
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Candidate Roll#</th>
                <th>Score</th>
                <th>Accuracy %</th>
                <th>Correct / Incorrect</th>
                <th>Audit Status</th>
                <th>Latency</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {submissions.map((sub) => (
                <tr key={sub.id || sub.student_id}>
                  <td style={{ fontWeight: 700, color: 'var(--accent-cyan)' }}>
                    #{sub.student_id}
                  </td>
                  <td style={{ fontWeight: 700 }}>
                    {sub.total_score} <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>/ {sub.max_score}</span>
                  </td>
                  <td>
                    <span style={{
                      color: sub.accuracy_pct >= 70 ? 'var(--accent-success)' : sub.accuracy_pct >= 40 ? 'var(--accent-warning)' : 'var(--accent-danger)',
                      fontWeight: 600,
                    }}>
                      {sub.accuracy_pct}%
                    </span>
                  </td>
                  <td>
                    <span style={{ color: 'var(--accent-success)' }}>{sub.total_correct}</span> / <span style={{ color: 'var(--accent-danger)' }}>{sub.total_incorrect}</span>
                  </td>
                  <td>
                    <span className={`badge ${sub.status === 'SUCCESS' ? 'badge-success' : 'badge-warning'}`}>
                      {sub.status}
                    </span>
                  </td>
                  <td style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                    <Clock size={12} style={{ display: 'inline', marginRight: '4px' }} />
                    {sub.processing_time_ms}ms
                  </td>
                  <td>
                    <button
                      onClick={() => setInspectingSub(sub)}
                      className="btn btn-secondary"
                      style={{ fontSize: '12px', padding: '4px 10px' }}
                    >
                      <Eye size={13} /> Inspect Scan
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Visual Sheet Inspector Modal */}
      {inspectingSub && (
        <SheetViewerModal
          submission={inspectingSub}
          examId={selectedExamId}
          onClose={() => setInspectingSub(null)}
        />
      )}
    </div>
  );
};

export default EvaluationPage;
