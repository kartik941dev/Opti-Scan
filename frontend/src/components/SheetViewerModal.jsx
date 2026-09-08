import React from 'react';
import { X, Download, CheckCircle2, XCircle, AlertTriangle, HelpCircle } from 'lucide-react';
import { resultsAPI } from '../api/endpoints';
import { SERVER_BASE_URL } from '../api/client';

const SheetViewerModal = ({ submission, examId, onClose }) => {
  if (!submission) return null;

  const pdfUrl = resultsAPI.getScorecardPdfUrl(examId, submission.student_id);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '1050px' }}>
        {/* Modal Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div>
            <h2 style={{ fontSize: '20px', margin: 0 }}>
              Visual Audit Inspection: Candidate <span className="brand-gradient-text">#{submission.student_id}</span>
            </h2>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Scan File: {submission.sheet_filename} &nbsp;|&nbsp; Latency: {submission.processing_time_ms}ms
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <a
              href={pdfUrl}
              target="_blank"
              rel="noreferrer"
              className="btn btn-primary"
              style={{ fontSize: '13px', padding: '8px 14px' }}
            >
              <Download size={15} /> Download Scorecard PDF
            </a>
            <button
              onClick={onClose}
              style={{
                background: 'rgba(255, 255, 255, 0.08)',
                border: 'none',
                color: 'var(--text-primary)',
                borderRadius: '8px',
                padding: '8px',
                cursor: 'pointer',
              }}
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Score Overview Row */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '12px',
          marginBottom: '20px',
          padding: '16px',
          background: 'rgba(255, 255, 255, 0.04)',
          borderRadius: 'var(--radius-sm)',
          border: '1px solid var(--border-subtle)',
        }}>
          <div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Total Score</span>
            <h4 style={{ fontSize: '20px', margin: '4px 0 0 0', color: 'var(--accent-primary)' }}>
              {submission.total_score} / {submission.max_score}
            </h4>
          </div>
          <div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Accuracy Rate</span>
            <h4 style={{ fontSize: '20px', margin: '4px 0 0 0', color: 'var(--accent-success)' }}>
              {submission.accuracy_pct}%
            </h4>
          </div>
          <div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Correct / Attempted</span>
            <h4 style={{ fontSize: '20px', margin: '4px 0 0 0' }}>
              {submission.total_correct} / {submission.total_attempted}
            </h4>
          </div>
          <div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Audit Status</span>
            <div style={{ marginTop: '4px' }}>
              <span className={`badge ${submission.status === 'SUCCESS' ? 'badge-success' : 'badge-warning'}`}>
                {submission.status}
              </span>
            </div>
          </div>
        </div>

        {/* Layout Grid: Annotated Image + Question Audit Log */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          {/* Annotated Sheet Image */}
          <div style={{
            background: '#090d16',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-subtle)',
            padding: '12px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
              Annotated Inspection Scan
            </span>
            {submission.annotated_image_url ? (
              <img
                src={submission.annotated_image_url.startsWith('http') ? submission.annotated_image_url : `${SERVER_BASE_URL}${submission.annotated_image_url}`}
                alt="Annotated OMR"
                style={{ width: '100%', maxHeight: '480px', objectFit: 'contain', borderRadius: '4px' }}
              />
            ) : (
              <div style={{ height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b' }}>
                Annotated overlay processing...
              </div>
            )}
          </div>

          {/* Question Breakdown List */}
          <div style={{
            maxHeight: '520px',
            overflowY: 'auto',
            background: 'rgba(15, 23, 42, 0.4)',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-subtle)',
            padding: '12px',
          }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px', display: 'block' }}>
              Question-by-Question Diagnostic
            </span>

            <table className="data-table" style={{ fontSize: '12px' }}>
              <thead>
                <tr>
                  <th>Q#</th>
                  <th>Marked</th>
                  <th>Key</th>
                  <th>Status</th>
                  <th>Delta</th>
                </tr>
              </thead>
              <tbody>
                {submission.questions_audit?.map((q) => (
                  <tr key={q.question_number}>
                    <td style={{ fontWeight: 600 }}>Q{q.question_number}</td>
                    <td>
                      <span style={{
                        padding: '2px 6px',
                        borderRadius: '4px',
                        background: q.is_correct ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                        color: q.is_correct ? '#10b981' : '#ef4444',
                        fontWeight: 700,
                      }}>
                        {q.selected_option || 'BLANK'}
                      </span>
                    </td>
                    <td style={{ color: 'var(--text-muted)' }}>{q.correct_answer || '-'}</td>
                    <td>
                      {q.is_correct ? (
                        <span style={{ color: '#10b981', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <CheckCircle2 size={13} /> Correct
                        </span>
                      ) : q.status === 'BLANK' ? (
                        <span style={{ color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <HelpCircle size={13} /> Blank
                        </span>
                      ) : (
                        <span style={{ color: '#ef4444', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <XCircle size={13} /> Wrong
                        </span>
                      )}
                    </td>
                    <td style={{ fontWeight: 700, color: q.score_delta > 0 ? '#10b981' : q.score_delta < 0 ? '#ef4444' : '#64748b' }}>
                      {q.score_delta > 0 ? `+${q.score_delta}` : q.score_delta}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SheetViewerModal;
