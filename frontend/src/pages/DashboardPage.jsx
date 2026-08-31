import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users,
  Award,
  CheckCircle2,
  TrendingUp,
  ScanLine,
  FileSpreadsheet,
  FileCheck2,
  FolderOpen,
  Eye,
  Download,
} from 'lucide-react';
import MetricCard from '../components/MetricCard';
import SheetViewerModal from '../components/SheetViewerModal';
import { examsAPI, resultsAPI, omrAPI } from '../api/endpoints';

const DashboardPage = () => {
  const [exams, setExams] = useState([]);
  const [selectedExamId, setSelectedExamId] = useState('');
  const [overview, setOverview] = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [inspectingSub, setInspectingSub] = useState(null);
  const [demoLoading, setDemoLoading] = useState(false);

  const navigate = useNavigate();

  useEffect(() => {
    loadExams();
  }, []);

  useEffect(() => {
    if (selectedExamId) {
      loadExamData(selectedExamId);
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

  const loadExamData = async (examId) => {
    setLoading(true);
    try {
      const [ovRes, subsRes] = await Promise.all([
        resultsAPI.getOverview(examId),
        resultsAPI.getSubmissions(examId),
      ]);
      setOverview(ovRes.data);
      setSubmissions(subsRes.data);
    } catch (err) {
      console.error('Failed to load exam data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateDemo = async () => {
    if (!selectedExamId) return;
    setDemoLoading(true);
    try {
      const formData = new FormData();
      formData.append('exam_id', selectedExamId);
      await omrAPI.loadDemoSheets(formData);
      await loadExamData(selectedExamId);
    } catch (err) {
      console.error('Failed to generate demo sheets:', err);
    } finally {
      setDemoLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      {/* Top Banner Header */}
      <div className="glass-card" style={{
        background: 'linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%)',
        border: '1px solid #fed7aa',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '28px',
      }}>
        <div>
          <span style={{ fontSize: '12px', fontWeight: 700, color: '#ea580c', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Production Grading Hub
          </span>
          <h1 style={{ fontSize: '26px', margin: '4px 0 8px 0', color: '#0f172a' }}>
            Automated OMR Grading & Performance Analytics
          </h1>
          <p style={{ fontSize: '14px', color: '#475569', margin: 0, maxWidth: '650px' }}>
            High-speed optical mark recognition with 4-point homography alignment, adaptive threshold calibration, and item psychometrics.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <button
            onClick={() => navigate('/evaluate')}
            className="btn btn-primary"
          >
            <ScanLine size={16} />
            Evaluate New Scans
          </button>
          <button
            onClick={handleGenerateDemo}
            className="btn btn-secondary"
            style={{ fontSize: '13px', opacity: 0.9 }}
            disabled={demoLoading}
          >
            <FolderOpen size={15} color="#ea580c" />
            {demoLoading ? 'Grading Demo...' : 'Load 5 Sample Sheets'}
          </button>
        </div>
      </div>

      {/* Active Exam Selector */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-secondary)' }}>
            Active Assessment:
          </span>
          <select
            value={selectedExamId}
            onChange={(e) => setSelectedExamId(e.target.value)}
            className="input-field"
            style={{ width: '360px', padding: '8px 12px' }}
          >
            {exams.map((ex) => (
              <option key={ex.id} value={ex.id}>
                {ex.title} ({ex.code})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* KPI Metrics Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
        <MetricCard
          title="TOTAL SHEETS GRADED"
          value={overview?.total_candidates || 0}
          subtitle="Processed candidates"
          icon={Users}
          color="#f37021"
        />
        <MetricCard
          title="CLASS MEAN SCORE"
          value={`${overview?.average_score || 0}`}
          subtitle={`Out of ${overview?.max_possible_score || 400} pts`}
          icon={Award}
          color="#ea580c"
        />
        <MetricCard
          title="AVERAGE ACCURACY"
          value={`${overview?.average_percentage || 0}%`}
          subtitle={`Pass Rate: ${overview?.pass_rate_pct || 0}%`}
          icon={CheckCircle2}
          color="#16a34a"
        />
        <MetricCard
          title="TEST RELIABILITY (KR-20)"
          value={overview?.total_candidates > 0 && overview?.kr20_reliability != null ? overview.kr20_reliability : '—'}
          subtitle={overview?.total_candidates > 0 ? "Internal consistency index" : "No data available"}
          icon={TrendingUp}
          color="#d97706"
        />
      </div>

      {/* Recent Submissions Table */}
      <div className="glass-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div>
            <h3 style={{ fontSize: '18px', margin: 0 }}>Candidate Submissions Roster</h3>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Live evaluated sheets with transparent audit trail
            </span>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <a
              href={resultsAPI.getExportCsvUrl(selectedExamId)}
              className="btn btn-secondary"
              style={{ fontSize: '12px', padding: '6px 12px' }}
            >
              <Download size={14} /> Export CSV
            </a>
            <a
              href={resultsAPI.getExportExcelUrl(selectedExamId)}
              className="btn btn-secondary"
              style={{ fontSize: '12px', padding: '6px 12px' }}
            >
              <FileSpreadsheet size={14} /> Export Excel
            </a>
          </div>
        </div>

        {submissions.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: '56px 20px',
            color: 'var(--text-muted)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <div style={{
              width: '56px',
              height: '56px',
              borderRadius: '50%',
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '16px',
            }}>
              <ScanLine size={28} style={{ color: 'var(--accent-cyan)', opacity: 0.8 }} />
            </div>
            <h4 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)', margin: '0 0 6px 0' }}>
              No submissions yet
            </h4>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: '0 0 16px 0', maxWidth: '440px', lineHeight: 1.5 }}>
              Upload and evaluate candidate OMR sheets in the Evaluation tab, or load sample sheets to see real-time grading and psychometrics.
            </p>
            <div style={{ display: 'flex', gap: '10px' }}>
              <button
                onClick={() => navigate('/evaluate')}
                className="btn btn-primary"
                style={{ fontSize: '12px', padding: '6px 14px' }}
              >
                <ScanLine size={14} /> Upload & Evaluate Sheets
              </button>
              <button
                onClick={handleGenerateDemo}
                className="btn btn-secondary"
                style={{ fontSize: '12px', padding: '6px 14px' }}
                disabled={demoLoading}
              >
                <FolderOpen size={14} color="#ea580c" />
                {demoLoading ? 'Grading Demo...' : 'Load Sample Sheets'}
              </button>
            </div>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Roll Number</th>
                  <th>Total Score</th>
                  <th>Accuracy %</th>
                  <th>Attempted</th>
                  <th>Correct / Wrong</th>
                  <th>Audit Status</th>
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
                    <td>{sub.total_attempted} / 100</td>
                    <td>
                      <span style={{ color: 'var(--accent-success)' }}>{sub.total_correct}</span> / <span style={{ color: 'var(--accent-danger)' }}>{sub.total_incorrect}</span>
                    </td>
                    <td>
                      <span className={`badge ${sub.status === 'SUCCESS' ? 'badge-success' : 'badge-warning'}`}>
                        {sub.status}
                      </span>
                    </td>
                    <td>
                      <button
                        onClick={() => setInspectingSub(sub)}
                        className="btn btn-secondary"
                        style={{ fontSize: '12px', padding: '4px 10px' }}
                      >
                        <Eye size={13} /> View Audit
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
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

export default DashboardPage;
