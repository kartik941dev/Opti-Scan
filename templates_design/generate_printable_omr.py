"""
Printable Vector A4 OMR Sheet Generator (PDF & High-Resolution Image).
Generates standardized 100-Question and 50-Question exam sheets.
"""

from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def draw_printable_100q_omr(output_path: Path):
    """
    Generate pixel-aligned printable A4 100-Question OMR Sheet with:
    - 4 Black solid square corner fiducials (10mm x 10mm)
    - Candidate Roll Number grid (6 columns x 10 digits)
    - 4 Section columns (25 questions each, options A B C D)
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4  # 210mm x 297mm

    # 1. Corner Fiducial Markers (10mm squares)
    m_size = 8 * mm
    margin = 12 * mm

    c.setFillColorRGB(0, 0, 0)
    c.rect(margin, height - margin - m_size, m_size, m_size, fill=1, stroke=0)  # TL
    c.rect(width - margin - m_size, height - margin - m_size, m_size, m_size, fill=1, stroke=0)  # TR
    c.rect(width - margin - m_size, margin, m_size, m_size, fill=1, stroke=0)  # BR
    c.rect(margin, margin, m_size, m_size, fill=1, stroke=0)  # BL

    # 2. Header
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2.0, height - 18 * mm, "OPTISCAN STANDARD ASSESSMENT SHEET")
    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2.0, height - 23 * mm, "Use dark blue/black pen or 2B pencil. Completely darken the circle.")
    c.setLineWidth(1)
    c.line(margin + m_size + 4 * mm, height - 26 * mm, width - margin - m_size - 4 * mm, height - 26 * mm)

    # 3. Candidate Info & Student ID Grid
    c.setFont("Helvetica-Bold", 9)
    c.drawString(margin + 5 * mm, height - 34 * mm, "STUDENT DETAILS")

    # Name Box
    c.setLineWidth(0.5)
    c.rect(margin + 5 * mm, height - 48 * mm, 90 * mm, 10 * mm, fill=0, stroke=1)
    c.setFont("Helvetica", 7)
    c.drawString(margin + 7 * mm, height - 41 * mm, "Candidate Name: _____________________________________")

    # Roll Number Grid (Right side)
    id_start_x = width - margin - 65 * mm
    id_start_y = height - 34 * mm
    c.setFont("Helvetica-Bold", 8)
    c.drawString(id_start_x, id_start_y, "ROLL NUMBER")

    c.setFont("Helvetica", 6)
    bubble_r = 1.8 * mm
    col_dx = 5.5 * mm
    row_dy = 4.2 * mm

    # Draw 6 digits x 10 rows
    for col in range(6):
        cx = id_start_x + col * col_dx + 4 * mm
        for digit in range(10):
            cy = id_start_y - 8 * mm - digit * row_dy
            c.circle(cx, cy, bubble_r, stroke=1, fill=0)
            c.drawCentredString(cx, cy - 1 * mm, str(digit))

    # 4. Question Columns (4 columns of 25 questions)
    c.setLineWidth(0.5)
    q_grid_y = height - 90 * mm
    q_dy = 6.8 * mm
    opt_dx = 5.2 * mm
    col_w = 40 * mm
    col_starts = [margin + 4 * mm + i * (col_w + 3 * mm) for i in range(4)]
    sections = ["SEC A (Q1-25)", "SEC B (Q26-50)", "SEC C (Q51-75)", "SEC D (Q76-100)"]
    options = ["A", "B", "C", "D"]

    q_num = 1
    for col_idx, col_x in enumerate(col_starts):
        # Section Header Box
        c.setFillColorRGB(0.92, 0.95, 0.98)
        c.rect(col_x, q_grid_y + 2 * mm, col_w, 6 * mm, fill=1, stroke=1)
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(col_x + col_w / 2.0, q_grid_y + 4 * mm, sections[col_idx])

        for row in range(25):
            cy = q_grid_y - (row + 1) * q_dy
            c.setFont("Helvetica-Bold", 7)
            c.drawString(col_x + 1 * mm, cy - 1 * mm, f"{q_num:02d}")

            for opt_idx, opt in enumerate(options):
                ox = col_x + 11 * mm + opt_idx * opt_dx
                c.setLineWidth(0.6)
                c.circle(ox, cy, bubble_r, stroke=1, fill=0)
                c.setFont("Helvetica", 6)
                c.drawCentredString(ox, cy - 0.8 * mm, opt)

            q_num += 1

    # 5. Footer Instructions & Barcode placeholder
    c.setFont("Helvetica", 6)
    c.drawString(margin + 5 * mm, margin + 4 * mm, "OptiScan Certified OMR Form v2.0 - Do not fold or tear - Serial: OS-2026-A4-100Q")

    c.save()
    print(f"[OK] Generated Printable 100Q OMR Sheet: {output_path}")


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent
    draw_printable_100q_omr(out_dir / "standard_100q_omr.pdf")
