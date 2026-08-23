import React, { useState, useEffect } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  ZAxis,
  CartesianGrid,
} from 'recharts';
import {
  BarChart3,
  Download,
  FileSpreadsheet,
  TrendingUp,
  PieChart,
  HelpCircle,
  Award,
} from 'lucide-react';
import { examsAPI, resultsAPI } from '../api/endpoints';

const ResultsAnalyticsPage = () => {
  const [exams, setExams] = useState([]);
  const [selectedExamId, setSelectedExamId] = useState('');
  const [overview, setOverview] = useState(null);
  const [itemAnalysis, setItemAnalysis] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadExams();
  }, []);

  useEffect(() => {
    if (selectedExamId) {
      loadAnalytics(selectedExamId);
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

  const loadAnalytics = async (examId) => {
    setLoading(true);
    try {
      const [ovRes, itemRes] = await Promise.all([
        resultsAPI.getOverview(examId),
        resultsAPI.getItemAnalysis(examId),
      ]);
      setOverview(ovRes.data);
      setItemAnalysis(itemRes.data);
    } catch (err) {
      console.error('Failed to load analytics:', err);
    } finally {
      setLoading(false);
    }
  };

  const sectionalData = overview?.sectional_averages
    ? Object.entries(overview.sectional_averages).map(([name, avg]) => ({
        name: name.split('(')[0].trim(),
        accuracy: avg,
      }))
    : [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: '24px', margin: '0 0 4px 0' }}>Psychometric Item Analytics & Reporting</h1>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: 0 }}>
            Classical Test Theory (CTT) item difficulty, discrimination index, and sectional mastery
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

          <a
            href={resultsAPI.getExportCsvUrl(selectedExamId)}
            className="btn btn-secondary"
          >
            <Download size={15} /> Export CSV
          </a>
          <a
            href={resultsAPI.getExportExcelUrl(selectedExamId)}
            className="btn btn-primary"
          >
            <FileSpreadsheet size={15} /> Multi-Tab Excel
          </a>
        </div>
      </div>

      {/* 2-Column Chart Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        {/* Score Distribution Histogram */}
        <div className="glass-card">
          <h3 style={{ fontSize: '16px', marginBottom: '4px' }}>Score Distribution Histogram</h3>
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '16px' }}>
            Candidate percentile frequency curve (Class Average: {overview?.average_percentage || 0}%)
          </span>

          <div style={{ width: '100%', height: '240px' }}>
            <ResponsiveContainer>
              <BarChart data={overview?.score_distribution || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.06)" />
                <XAxis dataKey="range" stroke="#94a3b8" fontSize={11} />
                <YAxis stroke="#94a3b8" fontSize={11} />
                <Tooltip
                  contentStyle={{ background: '#0f172a', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '8px' }}
                  itemStyle={{ color: '#06b6d4' }}
                />
                <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Sectional Performance Mastery */}
        <div className="glass-card">
          <h3 style={{ fontSize: '16px', marginBottom: '4px' }}>Sectional Mastery Breakdown</h3>
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '16px' }}>
            Mean student accuracy by curriculum subject domain
          </span>

          <div style={{ width: '100%', height: '240px' }}>
            <ResponsiveContainer>
              <BarChart data={sectionalData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.06)" />
                <XAxis type="number" domain={[0, 100]} stroke="#94a3b8" fontSize={11} unit="%" />
                <YAxis dataKey="name" type="category" stroke="#94a3b8" fontSize={11} width={90} />
                <Tooltip
                  contentStyle={{ background: '#0f172a', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '8px' }}
                  itemStyle={{ color: '#10b981' }}
                />
                <Bar dataKey="accuracy" fill="#06b6d4" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Item Analysis Matrix Table */}
      <div className="glass-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <div>
            <h3 style={{ fontSize: '18px', margin: 0 }}>Item Diagnostic Matrix (Classical Test Theory)</h3>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Difficulty Index (P), Discrimination Index (D), and Distractor Choice Frequencies
            </span>
          </div>
        </div>

        {itemAnalysis.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '36px 0', color: 'var(--text-muted)' }}>
            No item statistics available yet.
          </div>
        ) : (
          <div style={{ maxHeight: '450px', overflowY: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Q#</th>
                  <th>Key</th>
                  <th>Difficulty (P)</th>
                  <th>Classification</th>
                  <th>Discrimination (D)</th>
                  <th>Distractor Frequency (A / B / C / D / Blank)</th>
                </tr>
              </thead>
              <tbody>
                {itemAnalysis.map((item) => (
                  <tr key={item.question_number}>
                    <td style={{ fontWeight: 700 }}>Q{item.question_number}</td>
                    <td>
                      <span className="badge badge-success" style={{ fontSize: '11px' }}>
                        {item.correct_key}
                      </span>
                    </td>
                    <td style={{ fontWeight: 600 }}>{item.difficulty_p}</td>
                    <td>
                      <span style={{
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontSize: '11px',
                        fontWeight: 600,
                        background: item.difficulty_label === 'Easy' ? 'rgba(16, 185, 129, 0.15)' : item.difficulty_label === 'Moderate' ? 'rgba(6, 182, 212, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                        color: item.difficulty_label === 'Easy' ? '#10b981' : item.difficulty_label === 'Moderate' ? '#06b6d4' : '#ef4444',
                      }}>
                        {item.difficulty_label}
                      </span>
                    </td>
                    <td style={{
                      fontWeight: 700,
                      color: item.discrimination_d >= 0.3 ? '#10b981' : item.discrimination_d >= 0.15 ? '#f59e0b' : '#ef4444',
                    }}>
                      {item.discrimination_d > 0 ? `+${item.discrimination_d}` : item.discrimination_d} ({item.discrimination_label})
                    </td>
                    <td style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                      A: {item.distractors.A} &nbsp;|&nbsp; B: {item.distractors.B} &nbsp;|&nbsp; C: {item.distractors.C} &nbsp;|&nbsp; D: {item.distractors.D} &nbsp;|&nbsp; Blank: {item.distractors.BLANK}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default ResultsAnalyticsPage;
