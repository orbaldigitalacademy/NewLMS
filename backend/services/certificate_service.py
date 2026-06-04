"""Certificate generator - produces a PDF certificate for completed courses."""
import io
import os
from datetime import datetime

from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor


APP_NAME = os.environ.get("APP_NAME", "Atlas Academy")


def generate_certificate_pdf(student_name: str, course_title: str, completion_date: str | None = None) -> bytes:
    """Return PDF bytes for a certificate of completion."""
    buf = io.BytesIO()
    page_w, page_h = landscape(A4)
    c = canvas.Canvas(buf, pagesize=landscape(A4))

    # Background bone
    c.setFillColor(HexColor("#F8F6F0"))
    c.rect(0, 0, page_w, page_h, fill=1, stroke=0)

    # Outer border
    c.setStrokeColor(HexColor("#991B1B"))
    c.setLineWidth(3)
    c.rect(0.5 * inch, 0.5 * inch, page_w - 1 * inch, page_h - 1 * inch, stroke=1, fill=0)

    # Inner thin border
    c.setStrokeColor(HexColor("#1C1917"))
    c.setLineWidth(0.5)
    c.rect(0.7 * inch, 0.7 * inch, page_w - 1.4 * inch, page_h - 1.4 * inch, stroke=1, fill=0)

    # Brand label
    c.setFillColor(HexColor("#57534E"))
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(page_w / 2, page_h - 1.3 * inch, APP_NAME.upper())

    # Title
    c.setFillColor(HexColor("#1C1917"))
    c.setFont("Helvetica", 36)
    c.drawCentredString(page_w / 2, page_h - 2.1 * inch, "Certificate of Completion")

    # Wine accent line
    c.setStrokeColor(HexColor("#991B1B"))
    c.setLineWidth(2)
    c.line(page_w / 2 - 1.5 * inch, page_h - 2.3 * inch, page_w / 2 + 1.5 * inch, page_h - 2.3 * inch)

    # Body
    c.setFillColor(HexColor("#57534E"))
    c.setFont("Helvetica", 14)
    c.drawCentredString(page_w / 2, page_h - 3.1 * inch, "This is to certify that")

    c.setFillColor(HexColor("#1C1917"))
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(page_w / 2, page_h - 3.9 * inch, student_name)

    c.setFillColor(HexColor("#57534E"))
    c.setFont("Helvetica", 14)
    c.drawCentredString(
        page_w / 2, page_h - 4.5 * inch, "has successfully completed the course"
    )

    c.setFillColor(HexColor("#991B1B"))
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(page_w / 2, page_h - 5.2 * inch, course_title)

    # Date / signature row
    date_str = completion_date or datetime.utcnow().strftime("%B %d, %Y")
    c.setFillColor(HexColor("#57534E"))
    c.setFont("Helvetica", 11)
    c.drawString(1.5 * inch, 1.3 * inch, f"Date: {date_str}")
    c.drawRightString(page_w - 1.5 * inch, 1.3 * inch, f"Issued by {APP_NAME}")

    c.showPage()
    c.save()
    return buf.getvalue()
