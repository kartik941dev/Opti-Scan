import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  Eye,
  EyeOff,
  AlertCircle,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import Logo from '../components/Logo';
import GhostFibers from '../components/GhostFibers';

const LoginPage = () => {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showForgotNotice, setShowForgotNotice] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const { login, register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isRegister) {
        await register(email, fullName, password);
      } else {
        await login(email, password);
      }
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || 'Authentication failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  // Authentic OMR question rows with Deep Navy, Professional Blue (processing), and Teal (verified)
  const omrItems = [
    { q: '01', marked: 1, type: 'navy' }, // ○ ● ○ ○ ○
    { q: '02', marked: 0, type: 'teal' }, // ● ○ ○ ○ ○ (Verified Detection)
    { q: '03', marked: 2, type: 'navy' }, // ○ ○ ● ○ ○
    { q: '04', marked: 3, type: 'blue' }, // ○ ○ ○ ● ○ (Selected / Processing State)
    { q: '05', marked: 1, type: 'navy' }, // ○ ● ○ ○ ○
    { q: '06', marked: 0, type: 'navy' }, // ● ○ ○ ○ ○
    { q: '07', marked: 3, type: 'teal' }, // ○ ○ ○ ● ○ (Verified Detection)
  ];

  return (
    <div className="optiscan-auth-page">
      {/* ===================================================================
          FULL-SCREEN AMBIENT BACKGROUND: Subtle WebGL GhostFibers Canvas
          Covers the entire viewport (100vw x 100vh) in sophisticated dark tech palette
          =================================================================== */}
      <div className="optiscan-auth-bg-canvas" aria-hidden="true">
        <GhostFibers
          lineColor="#111A3A"
          glowColor="#2563EB"
          speed={0.16}
          scale={2.2}
          rotation={0}
          rotationSpeed={0.2}
          layers={4}
          waveAmplitude={0.012}
          waveFrequency={2.8}
          waveSpeed={0.12}
          layerSpeed={0.06}
          twist={0.08}
          twistFrequency={4.5}
          twistSpeed={0.9}
          lineFrequency={4.5}
          lineSpacing={2}
          lineSharpness={16}
          glowFalloff={12}
          glowIntensity={1.3}
          brightness={1.6}
          blueBoost={1.15}
          vignette={0.85}
          grain={0.04}
          dpr={1}
        />
      </div>

      {/* ===================================================================
          MAIN RESPONSIVE 2-COLUMN LAYOUT (~55% Left / ~45% Right)
          Vertically centered over the unified full-screen ambient canvas
          =================================================================== */}
      <div className="optiscan-auth-layout">
        {/* -----------------------------------------------------------------
            LEFT COLUMN: Premium Product Introduction & Tactile OMR Hero
            ----------------------------------------------------------------- */}
        <div className="optiscan-intro-col">
          {/* Official OptiScan Logo (transparent background, crisp on dark background, 400px desktop width) */}
          <div className="optiscan-intro-logo">
            <Logo darkBg width={400} className="optiscan-hero-logo" alt="OptiScan" />
          </div>

          <div className="optiscan-intro-body">
            <span className="optiscan-eyebrow-tag">ASSESSMENT INTELLIGENCE</span>

            <h1 className="optiscan-hero-title">
              From answer sheets<br />
              to insights.
            </h1>

            <p className="optiscan-hero-subtitle">
              Automated OMR grading and psychometric analytics built for educators.
            </p>

            {/* Realistic Physical OMR Answer Sheet Visual */}
            <div className="optiscan-omr-artifact-card" aria-hidden="true">
              {/* 4 Corner Registration Fiducials */}
              <div className="optiscan-fiducial tl" />
              <div className="optiscan-fiducial tr" />
              <div className="optiscan-fiducial bl" />
              <div className="optiscan-fiducial br" />

              {/* OMR Sheet Header */}
              <div className="optiscan-omr-head-row">
                <span className="optiscan-omr-form-id">OPTISCAN-100A</span>
                <span className="optiscan-omr-form-type">STANDARD OMR SHEET</span>
              </div>

              {/* OMR Grid Canvas */}
              <div className="optiscan-omr-grid-body">
                {/* Timing Rail (Left Black Marks) */}
                <div className="optiscan-timing-rail">
                  {omrItems.map((_, idx) => (
                    <div key={idx} className="optiscan-timing-notch" />
                  ))}
                </div>

                {/* Questions Stack */}
                <div className="optiscan-questions-container">
                  {/* Column Letters */}
                  <div className="optiscan-col-headers">
                    {['A', 'B', 'C', 'D', 'E'].map((col) => (
                      <span key={col} className="optiscan-col-char">{col}</span>
                    ))}
                  </div>

                  {/* Rows */}
                  <div className="optiscan-rows-stack">
                    {omrItems.map((row) => (
                      <div key={row.q} className="optiscan-q-row">
                        <span className="optiscan-q-label">Q{row.q}</span>
                        <div className="optiscan-bubbles-group">
                          {[0, 1, 2, 3, 4].map((colIdx) => {
                            const isMarked = row.marked === colIdx;
                            let fillClass = '';
                            if (isMarked) {
                              if (row.type === 'blue') fillClass = 'fill-blue';
                              else if (row.type === 'teal') fillClass = 'fill-teal';
                              else fillClass = 'fill-navy';
                            }
                            return (
                              <span
                                key={colIdx}
                                className={`optiscan-bubble ${fillClass}`}
                              />
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Laser / Scan Evaluation Indicator Line */}
                <div className="optiscan-omr-scan-bar" />
              </div>

              {/* Subtle OMR Processing Status Badges */}
              <div className="optiscan-omr-foot-badges">
                <span className="optiscan-status-tag active">● OMR DETECTED</span>
                <span className="optiscan-status-tag ready">ASSESSMENT READY</span>
              </div>
            </div>

            {/* Subtle Feature Indicators */}
            <div className="optiscan-feature-bullets">
              <div className="optiscan-feature-item">
                <span className="optiscan-bullet-dot" />
                <span>Automated OMR grading</span>
              </div>
              <div className="optiscan-feature-item">
                <span className="optiscan-bullet-dot" />
                <span>Student performance analytics</span>
              </div>
              <div className="optiscan-feature-item">
                <span className="optiscan-bullet-dot" />
                <span>Psychometric insights</span>
              </div>
            </div>
          </div>
        </div>

        {/* -----------------------------------------------------------------
            RIGHT COLUMN: Clean White Enterprise Authentication Card
            ----------------------------------------------------------------- */}
        <div className="optiscan-auth-col">
          <div className="optiscan-auth-card">
            {/* Mobile Header (Visible only on compact viewports) */}
            <div className="optiscan-mobile-brand-bar">
              <Logo darkBg width={240} alt="OptiScan" />
              <div style={{ marginTop: '8px' }}>
                <span className="optiscan-eyebrow-tag" style={{ fontSize: '10px', marginBottom: 0 }}>
                  ASSESSMENT INTELLIGENCE
                </span>
              </div>
            </div>

            {/* Card Header */}
            <div className="optiscan-card-header">
              <h2 className="optiscan-card-title">
                {isRegister ? 'Create your account' : 'Welcome back'}
              </h2>
              <p className="optiscan-card-subtitle">
                {isRegister
                  ? 'Sign up to start evaluating assessments with OptiScan.'
                  : 'Sign in to continue to your OptiScan workspace.'}
              </p>
            </div>

            {/* Error Message Callout */}
            {error && (
              <div className="optiscan-error-callout" role="alert">
                <AlertCircle size={16} style={{ flexShrink: 0 }} />
                <span>{error}</span>
              </div>
            )}

            {/* Forgot Password Notice */}
            {showForgotNotice && !isRegister && (
              <div className="optiscan-notice-callout">
                <strong>Institutional Security:</strong> Please contact your institution IT department or examination administrator to reset educator credentials.
              </div>
            )}

            {/* Real Authentication Form */}
            <form onSubmit={handleSubmit}>
              {isRegister && (
                <div className="optiscan-form-row">
                  <div className="optiscan-label-container">
                    <label className="optiscan-input-label" htmlFor="fullName">
                      Full Name
                    </label>
                  </div>
                  <div className="optiscan-input-box-wrap">
                    <input
                      id="fullName"
                      type="text"
                      className="optiscan-text-input"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      placeholder="Prof. Sarah Miller"
                      required
                    />
                  </div>
                </div>
              )}

              <div className="optiscan-form-row">
                <div className="optiscan-label-container">
                  <label className="optiscan-input-label" htmlFor="email">
                    Email Address
                  </label>
                </div>
                <div className="optiscan-input-box-wrap">
                  <input
                    id="email"
                    type="email"
                    className="optiscan-text-input"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="teacher@optiscan.dev"
                    required
                  />
                </div>
              </div>

              <div className="optiscan-form-row">
                <div className="optiscan-label-container">
                  <label className="optiscan-input-label" htmlFor="password">
                    Password
                  </label>
                  {!isRegister && (
                    <button
                      type="button"
                      className="optiscan-forgot-trigger"
                      onClick={() => setShowForgotNotice(!showForgotNotice)}
                    >
                      Forgot password?
                    </button>
                  )}
                </div>
                <div className="optiscan-input-box-wrap">
                  <input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    className="optiscan-text-input"
                    style={{ paddingRight: '44px' }}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    required
                  />
                  <button
                    type="button"
                    className="optiscan-eye-toggle"
                    onClick={() => setShowPassword(!showPassword)}
                    title={showPassword ? 'Hide password' : 'Show password'}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>

              {/* Primary Submit Button: Professional Blue (#2563EB) */}
              <button
                type="submit"
                className="optiscan-main-action-btn"
                disabled={loading}
              >
                <span>{loading ? 'Authenticating...' : isRegister ? 'Create Account' : 'Sign In'}</span>
                <ArrowRight size={16} />
              </button>
            </form>

            {/* Switch Mode Row */}
            <div className="optiscan-mode-switch-row">
              <span>
                {isRegister ? 'Already have an account?' : "Don't have an account?"}
              </span>
              <button
                type="button"
                className="optiscan-mode-switch-btn"
                onClick={() => {
                  setIsRegister(!isRegister);
                  setError('');
                  setShowForgotNotice(false);
                }}
              >
                {isRegister ? 'Sign In' : 'Sign Up'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
