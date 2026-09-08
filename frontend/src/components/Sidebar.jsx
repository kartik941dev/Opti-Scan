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
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import Logo from './Logo';

const Sidebar = ({ collapsed = false, onToggle }) => {
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
    <aside
      className={`optiscan-sidebar ${collapsed ? 'sidebar-collapsed' : ''}`}
      style={{
        width: collapsed ? '72px' : '260px',
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
        padding: collapsed ? '20px 10px' : '24px 16px',
        zIndex: 100,
        boxShadow: '2px 0 20px rgba(0, 0, 0, 0.5)',
        transition: 'width 0.25s cubic-bezier(0.4, 0, 0.2, 1), padding 0.25s ease',
        overflowX: 'hidden',
      }}
    >
      {/* Brand Header with Single Official Logo Component & Collapse Toggle */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: collapsed ? 'center' : 'space-between',
        padding: collapsed ? '6px 0 16px 0' : '6px 4px 20px 8px',
        borderBottom: '1px solid #1E3152',
        marginBottom: collapsed ? '16px' : '20px',
      }}>
        {!collapsed && (
          <div style={{ display: 'flex', alignItems: 'center', overflow: 'hidden' }}>
            <Logo darkBg height={48} showLink to="/" />
          </div>
        )}

        {onToggle && (
          <button
            onClick={onToggle}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            style={{
              background: 'rgba(37, 99, 235, 0.12)',
              border: '1px solid rgba(96, 165, 250, 0.25)',
              color: '#60A5FA',
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.15s ease',
              flexShrink: 0,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(37, 99, 235, 0.22)';
              e.currentTarget.style.color = '#93C5FD';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(37, 99, 235, 0.12)';
              e.currentTarget.style.color = '#60A5FA';
            }}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
          </button>
        )}
      </div>

      {/* Navigation Links */}
      <nav style={{ display: 'flex', flexDirection: 'column', gap: '6px', flex: 1 }}>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => `sidebar-nav-link ${isActive ? 'active' : ''} ${collapsed ? 'collapsed-link' : ''}`.trim()}
              title={item.name}
              style={collapsed ? { justifyContent: 'center', padding: '11px 0', borderLeft: 'none' } : {}}
            >
              <Icon size={19} />
              {!collapsed && <span>{item.name}</span>}
            </NavLink>
          );
        })}
      </nav>

      {/* User Info & Logout */}
      <div style={{
        padding: collapsed ? '14px 0 0 0' : '16px 8px 0 8px',
        borderTop: '1px solid #1E3152',
        display: 'flex',
        alignItems: 'center',
        justifyContent: collapsed ? 'center' : 'space-between',
        flexDirection: collapsed ? 'column' : 'row',
        gap: collapsed ? '10px' : '0',
      }}>
        <div
          title={user?.full_name || 'kartik Patel'}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            minWidth: 0,
            justifyContent: collapsed ? 'center' : 'flex-start'
          }}
        >
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
          {!collapsed && (
            <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <span style={{
                fontSize: '13px',
                fontWeight: 600,
                color: '#F8FAFC',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}>
                {user?.full_name || 'kartik Patel'}
              </span>
            </div>
          )}
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
