import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  FileCheck2,
  KeyRound,
  ScanLine,
  BarChart3,
  Printer,
  LogOut,
  UserCheck,
  Sparkles,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const Sidebar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Exams & Layouts', path: '/exams', icon: FileCheck2 },
    { name: 'Master Answer Key', path: '/answer-key', icon: KeyRound },
    { name: 'Evaluate OMR', path: '/evaluate', icon: ScanLine },
    { name: 'Analytics & Reports', path: '/analytics', icon: BarChart3 },
    { name: 'Printable Sheets', path: '/print-templates', icon: Printer },
  ];

  return (
    <aside style={{
      width: '260px',
      position: 'fixed',
      top: 0,
      left: 0,
      bottom: 0,
      background: '#ffffff',
      borderRight: '1px solid var(--border-subtle)',
      display: 'flex',
      flexDirection: 'column',
      padding: '24px 16px',
      zIndex: 100,
      boxShadow: '2px 0 12px rgba(0, 0, 0, 0.02)',
    }}>
      {/* Brand Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '0 12px 28px 12px' }}>
        <div style={{
          width: '38px',
          height: '38px',
          borderRadius: '10px',
          background: 'linear-gradient(135deg, #f97316, #ea580c)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 2px 10px rgba(243, 112, 33, 0.35)',
        }}>
          <Sparkles size={22} color="#ffffff" />
        </div>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: 800, letterSpacing: '-0.03em', margin: 0, color: '#0f172a' }}>
            Opti<span style={{ color: '#f37021' }}>Scan</span>
          </h2>
          <span style={{ fontSize: '11px', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>
            OMR GRADING PLATFORM
          </span>
        </div>
      </div>

      {/* Navigation Links */}
      <nav style={{ display: 'flex', flexDirection: 'column', gap: '6px', flex: 1 }}>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '12px 14px',
                borderRadius: '8px',
                color: isActive ? '#ea580c' : '#475569',
                background: isActive ? '#fff2e8' : 'transparent',
                borderLeft: isActive ? '3px solid #f37021' : '3px solid transparent',
                textDecoration: 'none',
                fontFamily: 'var(--font-heading)',
                fontSize: '14px',
                fontWeight: isActive ? 700 : 500,
                transition: 'all 0.15s ease',
              })}
            >
              <Icon size={18} color={undefined} />
              <span>{item.name}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* User Info & Logout */}
      <div style={{
        padding: '16px 12px 0 12px',
        borderTop: '1px solid #f1f5f9',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '34px',
            height: '34px',
            borderRadius: '50%',
            background: '#fff2e8',
            border: '1px solid #fcd9bd',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <UserCheck size={18} color="#ea580c" />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontSize: '13px', fontWeight: 600, color: '#0f172a' }}>
              {user?.full_name || 'Demo Educator'}
            </span>
            <span style={{ fontSize: '11px', color: '#64748b' }}>
              {user?.role || 'Teacher'}
            </span>
          </div>
        </div>
        <button
          onClick={handleLogout}
          title="Sign Out"
          style={{
            background: 'transparent',
            border: 'none',
            color: '#94a3b8',
            cursor: 'pointer',
            padding: '6px',
            borderRadius: '6px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <LogOut size={16} />
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
