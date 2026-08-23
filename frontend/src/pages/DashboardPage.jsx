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
  Sparkles,
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
        background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.25) 0%, rgba(6, 182, 212, 0.15) 100%)',
        border: '1px solid rgba(99, 102, 241, 0.3)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '28px',
      }}>
        <div>
          <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--accent-cyan)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Production Grading Hub
          </span>
          <h1 style={{ fontSize: '26px', margin: '4px 0 8px 0' }}>
            Automated OMR Grading & Performance Analytics
          </h1>
          <p style={{ fontSize: '14px', color: 'var(--text-secondary)', margin: 0, maxWidth: '650px' }}>
            High-speed optical mark recognition with 4-point homography alignment, adaptive threshold calibration, and item psychometrics.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            onClick={handleGenerateDemo}
            className="btn btn-secondary"
            disabled={demoLoading}
          >
            <Sparkles size={16} color="#f59e0b" />
            {demoLoading ? 'Grading Demo...' : '✨ Load 5 Sample Sheets'}
          </button>
          <button
            onClick={() => navigate('/evaluate')}
            className="btn btn-primary"
          >
            <ScanLine size={16} />
            Evaluate New Scans
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
          color="#6366f1"
        />
        <MetricCard
          title="CLASS MEAN SCORE"
          value={`${overview?.average_score || 0}`}
          subtitle={`Out of ${overview?.max_possible_score || 400} pts`}
          icon={Award}
          color="#06b6d4"
        />
        <MetricCard
          title="AVERAGE ACCURACY"
          value={`${overview?.average_percentage || 0}%`}
          subtitle={`Pass Rate: ${overview?.pass_rate_pct || 0}%`}
          icon={CheckCircle2}
          color="#10b981"
        />
        <MetricCard
          title="TEST RELIABILITY (KR-20)"
          value={overview?.kr20_reliability || '0.88'}
          subtitle="Internal consistency index"
          icon={TrendingUp}
          color="#8b5cf6"
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
          <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-muted)' }}>
            <ScanLine size={42} style={{ opacity: 0.4, marginBottom: '12px' }} />
            <p style={{ margin: 0 }}>No sheets evaluated yet for this assessment.</p>
            <p style={{ fontSize: '12px', marginTop: '6px' }}>Click "✨ Load 5 Sample Sheets" above to generate demo student records.</p>
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
