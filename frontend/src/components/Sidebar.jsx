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
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import Logo from './Logo';

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
      background: 'rgba(7, 11, 24, 0.92)',
      backdropFilter: 'blur(12px)',
      WebkitBackdropFilter: 'blur(12px)',
      borderRight: '1px solid #1E3152',
      display: 'flex',
      flexDirection: 'column',
      padding: '24px 16px',
      zIndex: 100,
      boxShadow: '2px 0 20px rgba(0, 0, 0, 0.5)',
    }}>
      {/* Brand Header with Single Official Logo Component */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        padding: '6px 8px 24px 8px',
        borderBottom: '1px solid #1E3152',
        marginBottom: '20px',
      }}>
        <Logo darkBg height={48} showLink to="/" />
      </div>

      {/* Navigation Links */}
      <nav style={{ display: 'flex', flexDirection: 'column', gap: '6px', flex: 1 }}>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => `sidebar-nav-link ${isActive ? 'active' : ''}`.trim()}
            >
              <Icon size={18} />
              <span>{item.name}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* User Info & Logout */}
      <div style={{
        padding: '16px 8px 0 8px',
        borderTop: '1px solid #1E3152',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
          <div style={{
            width: '34px',
            height: '34px',
            borderRadius: '50%',
            background: 'rgba(37, 99, 235, 0.16)',
            border: '1px solid rgba(96, 165, 250, 0.25)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}>
            <UserCheck size={18} color="#60A5FA" />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <span style={{
              fontSize: '13px',
              fontWeight: 600,
              color: '#F8FAFC',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}>
              {user?.full_name || 'Educator'}
            </span>
            <span style={{ fontSize: '11px', color: '#94A3B8' }}>
              {user?.role || 'Instructor'}
            </span>
          </div>
        </div>
        <button
          onClick={handleLogout}
          title="Sign Out"
          style={{
            background: 'transparent',
            border: 'none',
            color: '#94A3B8',
            cursor: 'pointer',
            padding: '6px',
            borderRadius: '6px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.15s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.color = '#F8FAFC';
            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.06)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.color = '#94A3B8';
            e.currentTarget.style.background = 'transparent';
          }}
        >
          <LogOut size={16} />
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
