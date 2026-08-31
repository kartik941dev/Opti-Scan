import React, { useState, useEffect } from 'react';
import {
  UploadCloud,
  FileImage,
  FolderOpen,
  CheckCircle2,
  AlertCircle,
  Eye,
  Download,
  Clock,
  ScanLine,
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

  // Aspose-style evaluation parameter states
  const [paperSize, setPaperSize] = useState('A4');
  const [numQuestions, setNumQuestions] = useState(100);
  const [numAnswers, setNumAnswers] = useState(4);
  const [keyFormat, setKeyFormat] = useState('a..z');
  const [exportFormat, setExportFormat] = useState('CSV');

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
      {/* Breadcrumbs & Title */}
      <div>
        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
          OptiScan Apps / OMR Evaluation / <span style={{ color: 'var(--accent-primary)', fontWeight: 600 }}>Scan Answer Sheet</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '4px' }}>
          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '8px',
            background: 'var(--accent-orange-light)',
            border: '1px solid var(--accent-orange-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <ScanLine size={20} color="#ea580c" />
          </div>
          <h1 style={{ fontSize: '26px', margin: 0, fontWeight: 800 }}>Scan answer sheet free</h1>
        </div>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: 0 }}>
          Scan OMR sheets by uploading photos or scans of filled OMR forms. High-speed 4-point homography and PyTorch digit recognition.
        </p>
      </div>

      {/* Main Dual-Column Aspose Card */}
      <div className="glass-card" style={{ padding: '32px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: '36px', alignItems: 'start' }}>
          {/* Left Column: Aspose Dashed Dropzone */}
          <div>
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              style={{
                border: dragActive ? '2px dashed #ea580c' : '2px dashed #f37021',
                borderRadius: '8px',
                background: dragActive ? '#fff2e8' : '#fffcf9',
                padding: '52px 24px',
                textAlign: 'center',
                transition: 'all 0.2s ease',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                minHeight: '280px',
              }}
            >
              <label
                className="btn btn-secondary"
                style={{
                  cursor: 'pointer',
                  padding: '10px 24px',
                  fontSize: '14px',
                  fontWeight: 600,
                  background: '#ffe8d6',
                  color: '#ea580c',
                  border: '1px solid #fed7aa',
                  borderRadius: '6px',
                  boxShadow: '0 1px 3px rgba(243, 112, 33, 0.1)',
                }}
              >
                Browse file(s)
                <input
                  type="file"
                  multiple
                  accept="image/png,image/jpeg,image/jpg,image/tiff,application/pdf"
                  onChange={(e) => handleFiles(e.target.files)}
                  style={{ display: 'none' }}
                />
              </label>

              <span style={{ fontSize: '13px', color: '#475569', marginTop: '16px', fontWeight: 500 }}>
                or drag them in this box *
              </span>
            </div>

            <div style={{ textAlign: 'center', marginTop: '14px', fontSize: '11px', color: 'var(--text-muted)' }}>
              * Supports JPG, PNG, TIFF, and Multi-Page PDF files (up to 200MB per batch)
            </div>
          </div>

          {/* Right Column: Aspose Parameter Controls */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* Active Exam Selector */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)' }}>Target Exam</span>
              <select
                value={selectedExamId}
                onChange={(e) => setSelectedExamId(e.target.value)}
                className="input-field"
                style={{ width: '220px', padding: '6px 10px', fontSize: '13px' }}
              >
                {exams.map((ex) => (
                  <option key={ex.id} value={ex.id}>
                    {ex.title} ({ex.code})
                  </option>
                ))}
              </select>
            </div>

            {/* Paper Size */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)' }}>Paper size</span>
              <div style={{ display: 'flex', gap: '8px' }}>
                {['Letter', 'A4', 'Legal'].map((size) => (
                  <button
                    key={size}
                    type="button"
                    onClick={() => setPaperSize(size)}
                    className={`toggle-pill ${paperSize === size ? 'active' : 'inactive'}`}
                  >
                    {size}
                  </button>
                ))}
              </div>
            </div>

            {/* Number of questions slider */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)' }}>Number of questions</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <input
                  type="range"
                  min={10}
                  max={100}
                  step={5}
                  value={numQuestions}
                  onChange={(e) => setNumQuestions(Number(e.target.value))}
                  style={{ accentColor: '#f37021', width: '130px', cursor: 'pointer' }}
                />
                <span style={{
                  fontSize: '12px',
                  fontWeight: 600,
                  color: 'var(--text-secondary)',
                  background: '#f1f5f9',
                  padding: '3px 8px',
                  borderRadius: '4px',
                  minWidth: '36px',
                  textAlign: 'center',
                }}>
                  {numQuestions}
                </span>
              </div>
            </div>

            {/* Number of answers */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)' }}>Number of answers</span>
              <div style={{ display: 'flex', gap: '8px' }}>
                {[3, 4, 5].map((ans) => (
                  <button
                    key={ans}
                    type="button"
                    onClick={() => setNumAnswers(ans)}
                    className={`toggle-pill ${numAnswers === ans ? 'active' : 'inactive'}`}
                    style={{ minWidth: '40px' }}
                  >
                    {ans}
                  </button>
                ))}
              </div>
            </div>

            {/* Answer keys format */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)' }}>Answer keys</span>
              <div style={{ display: 'flex', gap: '8px' }}>
                {['A..Z', 'a..z', '1..9'].map((fmt) => (
                  <button
                    key={fmt}
                    type="button"
                    onClick={() => setKeyFormat(fmt)}
                    className={`toggle-pill ${keyFormat === fmt ? 'active' : 'inactive'}`}
                  >
                    {fmt}
                  </button>
                ))}
              </div>
            </div>

            {/* Save results as */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)' }}>Save results as</span>
              <div style={{ display: 'flex', gap: '8px' }}>
                {['CSV', 'JSON', 'Excel'].map((fmt) => (
                  <button
                    key={fmt}
                    type="button"
                    onClick={() => setExportFormat(fmt)}
                    className={`toggle-pill ${exportFormat === fmt ? 'active' : 'inactive'}`}
                  >
                    {fmt}
                  </button>
                ))}
              </div>
            </div>

            {/* Action Buttons */}
            <div style={{ display: 'flex', gap: '12px', marginTop: '12px' }}>
              <label
                className="btn btn-primary"
                style={{
                  flex: 1,
                  cursor: 'pointer',
                  padding: '11px 18px',
                  borderRadius: '6px',
                }}
              >
                Scan Answer Sheet
                <input
                  type="file"
                  multiple
                  accept="image/png,image/jpeg,image/jpg,image/tiff,application/pdf"
                  onChange={(e) => handleFiles(e.target.files)}
                  style={{ display: 'none' }}
                />
              </label>

              <button
                type="button"
                onClick={handleDemoGenerate}
                className="btn btn-secondary"
                style={{
                  borderRadius: '6px',
                  padding: '11px 18px',
                  background: '#f97316',
                  color: '#ffffff',
                  border: 'none',
                }}
                disabled={uploading}
              >
                <FolderOpen size={15} />
                {uploading ? 'Processing...' : 'Load Demo Sheets'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      {uploading && (
        <div className="glass-card" style={{ padding: '16px 20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '13px' }}>
            <span style={{ fontWeight: 600, color: '#ea580c' }}>
              Executing Computer Vision Alignment & Decision Engine...
            </span>
            <span>{progress}%</span>
          </div>
          <div style={{ width: '100%', height: '6px', background: '#f1f5f9', borderRadius: '3px', overflow: 'hidden' }}>
            <div style={{ width: `${progress}%`, height: '100%', background: 'var(--accent-primary)', transition: 'width 0.3s ease' }} />
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
          <div style={{
            textAlign: 'center',
            padding: '48px 20px',
            color: 'var(--text-muted)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <div style={{
              width: '52px',
              height: '52px',
              borderRadius: '50%',
              background: '#fff2e8',
              border: '1px solid #fcd9bd',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '14px',
            }}>
              <FileImage size={24} style={{ color: '#ea580c' }} />
            </div>
            <h4 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)', margin: '0 0 6px 0' }}>
              No evaluated submissions yet
            </h4>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: 0, maxWidth: '440px', lineHeight: 1.5 }}>
              Drag and drop OMR sheet scans into the upload zone above or load sample sheets. Evaluated candidate records and visual audit overlays will appear here automatically.
            </p>
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
                  <td style={{ fontWeight: 700, color: 'var(--accent-primary)' }}>
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
