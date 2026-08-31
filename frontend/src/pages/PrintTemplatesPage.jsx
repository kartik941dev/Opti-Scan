import React from 'react';
import { Printer, Download, FileText, CheckCircle2, AlertTriangle, Sparkles } from 'lucide-react';

const PrintTemplatesPage = () => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div>
        <h1 style={{ fontSize: '24px', margin: '0 0 4px 0' }}>Printable OMR Sheet Templates</h1>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: 0 }}>
          Download vector PDF examination forms optimized for standard laser/inkjet printers
        </p>
      </div>

      {/* Templates Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '20px' }}>
        {/* 100Q Standard Template */}
        <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
              <span className="badge badge-success">A4 Form Factor</span>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>4 Columns × 25 Questions</span>
            </div>

            <h3 style={{ fontSize: '18px', margin: '0 0 8px 0' }}>
              Standard 100-Question Assessment Sheet
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: '0 0 16px 0' }}>
              Includes 4 corner fiducial registration squares, 6-digit student roll number matrix, and 4 curriculum sections.
            </p>

            <div style={{
              background: 'rgba(15, 23, 42, 0.6)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-subtle)',
              padding: '12px',
              fontSize: '12px',
              color: 'var(--text-secondary)',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
            }}>
              <div>• <b>Paper Size:</b> ISO A4 (210 x 297 mm)</div>
              <div>• <b>Options per Question:</b> 4 (A, B, C, D)</div>
              <div>• <b>Corner Fiducials:</b> 4 Solid Black 8mm Anchors</div>
            </div>
          </div>

          <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid var(--border-subtle)' }}>
            <a
              href="/standard_100q_omr.pdf"
              download="OptiScan_Standard_100Q.pdf"
              className="btn btn-primary"
              style={{ width: '100%' }}
            >
              <Download size={16} /> Download Printable PDF
            </a>
          </div>
        </div>
      </div>

      {/* Printing & Scanning Guidelines */}
      <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
        <h3 style={{ fontSize: '18px', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Printer size={20} color="#6366f1" /> Printing & Scanning Best Practices
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', fontSize: '13px' }}>
          <div style={{
            background: 'rgba(16, 185, 129, 0.08)',
            border: '1px solid rgba(16, 185, 129, 0.2)',
            borderRadius: 'var(--radius-sm)',
            padding: '14px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
          }}>
            <span style={{ fontWeight: 700, color: '#10b981', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <CheckCircle2 size={16} /> Recommended Settings
            </span>
            <div>• Print at <b>100% Actual Size</b> (disable "Fit to Page" or "Shrink to Fit").</div>
            <div>• Use standard 75–80 gsm white A4 paper.</div>
            <div>• Ensure black corner fiducial squares are crisp and solid.</div>
            <div>• Students should use black/blue ballpoint pen or 2B pencil.</div>
          </div>

          <div style={{
            background: 'rgba(245, 158, 11, 0.08)',
            border: '1px solid rgba(245, 158, 11, 0.2)',
            borderRadius: 'var(--radius-sm)',
            padding: '14px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
          }}>
            <span style={{ fontWeight: 700, color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <AlertTriangle size={16} /> Smartphone Photo Capture Guidelines
            </span>
            <div>• Ensure all <b>4 black corner squares</b> are fully inside the camera frame.</div>
            <div>• Avoid severe glare and cast shadows across the sheet.</div>
            <div>• Maintain a resolution of at least 1080p (2 Megapixels).</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PrintTemplatesPage;
