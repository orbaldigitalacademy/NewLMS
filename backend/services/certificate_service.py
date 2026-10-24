"""Certificate generator for Orbal Digital Academy."""

import io
import os
from datetime import datetime, timezone

from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import simpleSplit
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF


APP_NAME = os.environ.get(
    "APP_NAME",
    "Orbal Digital Academy"
)


def generate_certificate_pdf(
    student_name: str,
    course_title: str,
    completion_date: str | datetime | None = None,
    certificate_id: str | None = None,
    verification_url: str | None = None,
) -> bytes:

    """Generate a certificate of completion as PDF bytes."""

    buf = io.BytesIO()

    page_w, page_h = landscape(A4)

    c = canvas.Canvas(
        buf,
        pagesize=(page_w, page_h)
    )

    # ---------------------------------
    # 1. Background
    # ---------------------------------

    c.setFillColor(HexColor("#F8F6F0"))

    c.rect(
        0, 0,
        page_w, page_h,
        fill=1,
        stroke=0
    )

    # ---------------------------------
    # 2. Outer border
    # ---------------------------------

    c.setStrokeColor(HexColor("#991B1B"))
    c.setLineWidth(3)

    c.rect(
        0.5 * inch,
        0.5 * inch,
        page_w - inch,
        page_h - inch,
        stroke=1,
        fill=0
    )

    # Inner border
    c.setStrokeColor(HexColor("#1C1917"))
    c.setLineWidth(0.5)

    c.rect(
        0.7 * inch,
        0.7 * inch,
        page_w - 1.4 * inch,
        page_h - 1.4 * inch,
        stroke=1,
        fill=0
    )

    # ---------------------------------
    # 3. Academy name
    # ---------------------------------

    c.setFillColor(HexColor("#57534E"))
    c.setFont("Helvetica-Bold", 14)

    c.drawCentredString(
        page_w / 2,
        page_h - 1.2 * inch,
        APP_NAME.upper()
    )

    # ---------------------------------
    # 4. Certificate title
    # ---------------------------------

    c.setFillColor(HexColor("#1C1917"))
    c.setFont("Helvetica", 34)

    c.drawCentredString(
        page_w / 2,
        page_h - 1.9 * inch,
        "Certificate of Completion"
    )

    # Accent line
    c.setStrokeColor(HexColor("#991B1B"))
    c.setLineWidth(2)

    c.line(
        page_w / 2 - 1.5 * inch,
        page_h - 2.15 * inch,
        page_w / 2 + 1.5 * inch,
        page_h - 2.15 * inch
    )

    # ---------------------------------
    # 5. Certificate body
    # ---------------------------------

    c.setFillColor(HexColor("#57534E"))
    c.setFont("Helvetica", 13)

    c.drawCentredString(
        page_w / 2,
        page_h - 2.75 * inch,
        "This is to certify that"
    )

    # Student name
    c.setFillColor(HexColor("#1C1917"))

    name_font_size = 28
    max_text_width = page_w - 2.2 * inch

    while (
        name_font_size > 12
        and c.stringWidth(
            student_name,
            "Helvetica-Bold",
            name_font_size
        ) > max_text_width
    ):
        name_font_size -= 1

    c.setFont("Helvetica-Bold", name_font_size)

    c.drawCentredString(
        page_w / 2,
        page_h - 3.35 * inch,
        student_name
    )

    c.setFillColor(HexColor("#57534E"))
    c.setFont("Helvetica", 13)

    c.drawCentredString(
        page_w / 2,
        page_h - 3.85 * inch,
        "has successfully completed the course"
    )

    # ---------------------------------
    # 6. Course title
    # ---------------------------------

    c.setFillColor(HexColor("#991B1B"))

    course_lines = simpleSplit(
        course_title,
        "Helvetica-Bold",
        19,
        page_w - 2.4 * inch
    )

    # Keep long titles within the available space
    if len(course_lines) > 2:
        course_lines = simpleSplit(
            course_title,
            "Helvetica-Bold",
            15,
            page_w - 2.4 * inch
        )

    course_font_size = 19 if len(course_lines) <= 2 else 15

    c.setFont("Helvetica-Bold", course_font_size)

    course_y = page_h - 4.35 * inch

    for line in course_lines:
        c.drawCentredString(
            page_w / 2,
            course_y,
            line
        )
        course_y -= 0.27 * inch

    # ---------------------------------
    # 7. Completion date
    # ---------------------------------

    if isinstance(completion_date, datetime):
        date_str = completion_date.strftime("%B %d, %Y")

    elif isinstance(completion_date, str) and completion_date:
        date_str = completion_date

    else:
        date_str = datetime.now(
            timezone.utc
        ).strftime("%B %d, %Y")

    c.setFillColor(HexColor("#57534E"))
    c.setFont("Helvetica", 10)

    c.drawString(
        1.2 * inch,
        1.15 * inch,
        f"Completion Date: {date_str}"
    )

    c.drawRightString(
        page_w - 1.2 * inch,
        1.15 * inch,
        f"Issued by {APP_NAME}"
    )

    # ---------------------------------
    # 8. Certificate ID
    # ---------------------------------

    if certificate_id:

        c.setFont("Helvetica", 9)

        c.drawCentredString(
            page_w / 2,
            1.1 * inch,
            f"Certificate ID: {certificate_id}"
        )

    # ---------------------------------
    # 9. Verification QR code
    # ---------------------------------

    if verification_url:

        qr_code = qr.QrCodeWidget(
            verification_url
        )

        bounds = qr_code.getBounds()

        qr_width = bounds[2] - bounds[0]
        qr_height = bounds[3] - bounds[1]

        qr_size = 0.65 * inch

        drawing = Drawing(
            qr_size,
            qr_size,
            transform=[
                qr_size / qr_width,
                0,
                0,
                qr_size / qr_height,
                0,
                0
            ]
        )

        drawing.add(qr_code)

        renderPDF.draw(
            drawing,
            c,
            page_w / 2 - qr_size / 2,
            1.3 * inch
        )

    # ---------------------------------
    # 10. Finalize PDF
    # ---------------------------------

    c.showPage()
    c.save()

    pdf_bytes = buf.getvalue()
    buf.close()

    return pdf_bytes
