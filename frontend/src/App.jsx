import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Sidebar from './components/Sidebar';
import DotField from './components/DotField';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import ExamsPage from './pages/ExamsPage';
import AnswerKeyPage from './pages/AnswerKeyPage';
import EvaluationPage from './pages/EvaluationPage';
import ResultsAnalyticsPage from './pages/ResultsAnalyticsPage';
import PrintTemplatesPage from './pages/PrintTemplatesPage';

const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  const [sidebarCollapsed, setSidebarCollapsed] = React.useState(() => {
    try {
      return localStorage.getItem('optiscan_sidebar_collapsed') === 'true';
    } catch {
      return false;
    }
  });

  const toggleSidebar = () => {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem('optiscan_sidebar_collapsed', String(next));
      } catch {}
      return next;
    });
  };

  if (loading) {
    return (
      <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#6366f1' }}>
        Loading OptiScan Portal...
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="app-container" style={{ position: 'relative', minHeight: '100vh', background: '#080C1A' }}>
      <DotField
        dotRadius={1.5}
        dotSpacing={14}
        bulgeStrength={67}
        glowRadius={160}
        sparkle={false}
        waveAmplitude={0}
        style={{
          position: 'fixed',
          inset: 0,
          width: '100vw',
          height: '100vh',
          zIndex: 0,
          pointerEvents: 'none',
        }}
      />
      <Sidebar collapsed={sidebarCollapsed} onToggle={toggleSidebar} />
      <main
        className={`main-content ${sidebarCollapsed ? 'collapsed' : ''}`}
        style={{
          position: 'relative',
          zIndex: 1,
          marginLeft: sidebarCollapsed ? '72px' : '260px',
          maxWidth: sidebarCollapsed ? 'calc(100vw - 72px)' : '1400px',
          transition: 'margin-left 0.25s cubic-bezier(0.4, 0, 0.2, 1), max-width 0.25s ease',
        }}
      >
        {children}
      </main>
    </div>
  );
};

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/exams"
            element={
              <ProtectedRoute>
                <ExamsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/answer-key"
            element={
              <ProtectedRoute>
                <AnswerKeyPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/evaluate"
            element={
              <ProtectedRoute>
                <EvaluationPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/analytics"
            element={
              <ProtectedRoute>
                <ResultsAnalyticsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/print-templates"
            element={
              <ProtectedRoute>
                <PrintTemplatesPage />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
