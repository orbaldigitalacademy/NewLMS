
"""Professional certificate generator for Orbal Digital Academy."""

import io
import os
from pathlib import Path
from datetime import date, datetime, timezone

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF


# ---------------------------------------------------
# BRAND COLORS
# ---------------------------------------------------

ACADEMY = "ORBAL DIGITAL ACADEMY"

NAVY = HexColor("#102B5B")
BLUE = HexColor("#07509A")
LIGHT_BLUE = HexColor("#8BA9D7")
GOLD = HexColor("#B39245")
ORANGE = HexColor("#C96837")
INK = HexColor("#253047")
MUTED = HexColor("#64748B")
WHITE = HexColor("#FFFFFF")
CREAM = HexColor("#FCFBF7")


# ---------------------------------------------------
# ASSET PATHS
# ---------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"

LOGO_PATH = ASSETS_DIR / "orbal_logo.png"
TRAINING_SIGNATURE_PATH = ASSETS_DIR / "training_signature.png"
DIRECTOR_SIGNATURE_PATH = ASSETS_DIR / "director_signature.png"
SEAL_PATH = ASSETS_DIR / "certificate_seal.png"


# ---------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------

def _date(value):
    if isinstance(value, (datetime, date)):
        return value.strftime("%d %B %Y")

    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(
                value.replace("Z", "+00:00")
            ).strftime("%d %B %Y")
        except ValueError:
            return value

    return datetime.now(timezone.utc).strftime("%d %B %Y")


def _asset(c, path, x, y, w, h):
    if not path or not os.path.isfile(path):
        return False

    try:
        c.drawImage(
            ImageReader(path),
            x,
            y,
            width=w,
            height=h,
            preserveAspectRatio=True,
            anchor="c",
            mask="auto",
        )
        return True

    except Exception as exc:
        print(f"Certificate asset error ({path}): {exc}")
        return False


def _fit(c, value, font, max_size, min_size, width):
    size = max_size

    while (
        size > min_size
        and c.stringWidth(value, font, size) > width
    ):
        size -= 0.5

    return size


def _wrap(c, value, font, size, width, max_lines=2):
    words = str(value).split()
    lines = []
    line = ""

    for word in words:
        trial = (line + " " + word).strip()

        if c.stringWidth(trial, font, size) <= width:
            line = trial
        else:
            if line:
                lines.append(line)
            line = word

    if line:
        lines.append(line)

    return lines[:max_lines]


def _centered_lines(c, lines, y, font, size, spacing):
    c.setFont(font, size)

    for index, line in enumerate(lines):
        c.drawCentredString(
            c._pagesize[0] / 2,
            y - index * spacing,
            line,
        )


# ---------------------------------------------------
# CERTIFICATE GENERATOR
# ---------------------------------------------------

def generate_certificate_pdf(
    student_name: str,
    course_title: str,
    completion_date: str | datetime | None = None,
    certificate_id: str | None = None,
    verification_url: str | None = None,
    enrollment_date: str | datetime | None = None,
    course_description: str | None = None,
) -> bytes:

    buffer = io.BytesIO()

    W, H = landscape(A4)
    c = canvas.Canvas(
        buffer,
        pagesize=(W, H),
        pageCompression=1,
    )

    c.setTitle(f"{ACADEMY} - Professional Certificate")
    c.setAuthor(ACADEMY)

    CX = W / 2

    # ---------------------------------------------------
    # 1. WHITE CERTIFICATE BACKGROUND
    # ---------------------------------------------------

    c.setFillColor(WHITE)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # ---------------------------------------------------
    # 2. SLIM NAVY OUTER BORDER
    # ---------------------------------------------------

    border = 22

    c.setStrokeColor(NAVY)
    c.setLineWidth(11)

    c.rect(
        border,
        border,
        W - 2 * border,
        H - 2 * border,
        fill=0,
        stroke=1,
    )

    # Fine gold inner border
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.2)

    c.rect(
        border + 11,
        border + 11,
        W - 2 * (border + 11),
        H - 2 * (border + 11),
        fill=0,
        stroke=1,
    )

    # ---------------------------------------------------
    # 3. SUBTLE GEOMETRIC CORNER ACCENTS
    # ---------------------------------------------------

    def corner_triangle(points, color):
        p = c.beginPath()
        p.moveTo(*points[0])

        for point in points[1:]:
            p.lineTo(*point)

        p.close()
        c.setFillColor(color)
        c.drawPath(p, fill=1, stroke=0)

    # Top-left
    corner_triangle(
        [(28, H - 28), (112, H - 28), (28, H - 112)],
        NAVY,
    )

    corner_triangle(
        [(43, H - 43), (92, H - 43), (43, H - 92)],
        LIGHT_BLUE,
    )

    # Bottom-right
    corner_triangle(
        [(W - 28, 28), (W - 112, 28), (W - 28, 112)],
        NAVY,
    )

    corner_triangle(
        [(W - 43, 43), (W - 92, 43), (W - 43, 92)],
        LIGHT_BLUE,
    )

    # ---------------------------------------------------
    # 4. ACADEMY LOGO
    # ---------------------------------------------------

    logo = os.getenv("CERT_LOGO_PATH") or str(LOGO_PATH)

    if not _asset(c, logo, 82, H - 145, 68, 68):
        c.setStrokeColor(GOLD)
        c.setLineWidth(1.5)
        c.circle(116, H - 111, 29, fill=0, stroke=1)

        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(116, H - 115, "ODA")

    # ---------------------------------------------------
    # 5. ACADEMY NAME
    # ---------------------------------------------------

    c.setFillColor(NAVY)

    academy_size = _fit(
        c,
        ACADEMY,
        "Helvetica-Bold",
        27,
        18,
        W - 300,
    )

    c.setFont("Helvetica-Bold", academy_size)
    c.drawCentredString(CX + 28, H - 91, ACADEMY)

    c.setFillColor(MUTED)
    c.setFont("Helvetica", 10)
    c.drawCentredString(
        CX + 28,
        H - 110,
        "Professional Training and Certification",
    )

    # ---------------------------------------------------
    # 6. CERTIFICATE ID
    # ---------------------------------------------------

    if certificate_id:
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 8)
        c.drawRightString(
            W - 67,
            H - 67,
            f"Certificate ID: {certificate_id}",
        )

    # ---------------------------------------------------
    # 7. CERTIFICATE HEADING
    # ---------------------------------------------------

    c.setFillColor(ORANGE)
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(
        CX,
        H - 172,
        "PROFESSIONAL CERTIFICATE",
    )

    # Decorative gold divider
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.2)
    c.line(CX - 105, H - 186, CX + 105, H - 186)

    # ---------------------------------------------------
    # 8. COURSE TITLE
    # ---------------------------------------------------

    course_text = course_title.upper()

    course_size = _fit(
        c,
        course_text,
        "Helvetica-Bold",
        20,
        12,
        W - 170,
    )

    course_lines = _wrap(
        c,
        course_text,
        "Helvetica-Bold",
        course_size,
        W - 170,
        2,
    )

    c.setFillColor(NAVY)

    _centered_lines(
        c,
        course_lines,
        H - 215,
        "Helvetica-Bold",
        course_size,
        21,
    )

    # ---------------------------------------------------
    # 9. RECIPIENT NAME
    # ---------------------------------------------------

    c.setFillColor(MUTED)
    c.setFont("Times-Italic", 14)
    c.drawCentredString(
        CX,
        H - 275,
        "This is to certify that",
    )

    name_size = _fit(
        c,
        student_name,
        "Times-BoldItalic",
        37,
        20,
        W - 230,
    )

    c.setFillColor(NAVY)
    c.setFont("Times-BoldItalic", name_size)
    c.drawCentredString(
        CX,
        H - 317,
        student_name,
    )

    c.setStrokeColor(GOLD)
    c.setLineWidth(1)
    c.line(
        CX - 180,
        H - 328,
        CX + 180,
        H - 328,
    )

    # ---------------------------------------------------
    # 10. ACHIEVEMENT DESCRIPTION
    # ---------------------------------------------------

    description = (
        course_description
        or "has successfully completed a 3-month prosessinal training in data analytics coverig Excel, Power BI, Tableau
        SQL, Python and SPSS."
    )

    desc_lines = _wrap(
        c,
        description,
        "Helvetica",
        11,
        W - 240,
        3,
    )

    c.setFillColor(INK)

    _centered_lines(
        c,
        desc_lines,
        H - 352,
        "Helvetica",
        11,
        16,
    )

    # ---------------------------------------------------
    # 11. ENROLLMENT AND AWARD DATES
    # ---------------------------------------------------

    bottom = 80

    if enrollment_date:
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 9)
        c.drawString(93, bottom + 83, "DATE ENROLLED")

        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(
            93,
            bottom + 68,
            _date(enrollment_date),
        )

    c.setFillColor(MUTED)
    c.setFont("Helvetica", 12)
    c.drawRightString(
        W - 93,
        bottom + 83,
        "DATE AWARDED",
    )

    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(
        W - 93,
        bottom + 68,
        _date(completion_date),
    )

    # ---------------------------------------------------
    # 12. SIGNATURES
    # ---------------------------------------------------

    training_signature = (
        os.getenv("CERT_TRAINING_SIGNATURE_PATH")
        or str(TRAINING_SIGNATURE_PATH)
    )

    director_signature = (
        os.getenv("CERT_DIRECTOR_SIGNATURE_PATH")
        or str(DIRECTOR_SIGNATURE_PATH)
    )

    training_x = 110
    director_x = W - 240

    _asset(
        c,
        training_signature,
        training_x,
        bottom + 18,
        110,
        37,
    )

    _asset(
        c,
        director_signature,
        director_x,
        bottom + 18,
        110,
        37,
    )

    c.setStrokeColor(MUTED)
    c.setLineWidth(0.6)

    c.line(
        training_x,
        bottom + 16,
        training_x + 140,
        bottom + 16,
    )

    c.line(
        director_x,
        bottom + 16,
        director_x + 140,
        bottom + 16,
    )

    training_name = os.getenv(
        "CERT_TRAINING_NAME",
        "Head of Training",
    )

    director_name = os.getenv(
        "CERT_DIRECTOR_NAME",
        "Executive Director",
    )

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 12)

    c.drawString(
        training_x,
        bottom + 3,
        training_name,
    )

    c.drawString(
        director_x,
        bottom + 3,
        director_name,
    )

    c.setFillColor(MUTED)
    c.setFont("Helvetica", 12)

    c.drawString(
        training_x,
        bottom - 10,
        "Head of Training",
    )

    c.drawString(
        director_x,
        bottom - 10,
        "Executive Director",
    )

    # ---------------------------------------------------
    # 13. GOLD CERTIFICATION SEAL
    # ---------------------------------------------------

    seal = os.getenv("CERT_SEAL_PATH") or str(SEAL_PATH)

    if not _asset(c, seal, CX - 29, bottom + 7, 58, 58):
        c.setFillColor(GOLD)
        c.circle(
            CX,
            bottom + 37,
            27,
            stroke=0,
            fill=1,
        )

        c.setStrokeColor(CREAM)
        c.setLineWidth(1.5)
        c.circle(
            CX,
            bottom + 37,
            21,
            stroke=1,
            fill=0,
        )

        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(
            CX,
            bottom + 34,
            "ODA",
        )

    # ---------------------------------------------------
    # 14. QR CODE VERIFICATION
    # ---------------------------------------------------

    if verification_url:
        widget = qr.QrCodeWidget(verification_url)
        bounds = widget.getBounds()

        qsize = 44

        drawing = Drawing(
            qsize,
            qsize,
            transform=[
                qsize / (bounds[2] - bounds[0]),
                0,
                0,
                qsize / (bounds[3] - bounds[1]),
                0,
                0,
            ],
        )

        drawing.add(widget)

        renderPDF.draw(
            drawing,
            c,
            CX - qsize / 2,
            43,
        )

        c.setFillColor(MUTED)
        c.setFont("Helvetica", 7)
        c.drawCentredString(
            CX,
            38,
            "Scan to verify",
        )

    # ---------------------------------------------------
    # 15. FINALIZE PDF
    # ---------------------------------------------------

    c.showPage()
    c.save()

    data = buffer.getvalue()
    buffer.close()

    if not data.startswith(b"%PDF-"):
        raise ValueError("Invalid certificate PDF generated")

    return data


# ---------------------------------------------------
# LOCAL PREVIEW
# ---------------------------------------------------

if __name__ == "__main__":
    sample = generate_certificate_pdf(
        student_name="Sample Student",
        course_title="Professional Certificate Course in Data Analytics",
        completion_date="2026-10-27",
        certificate_id="ODA-SAMPLE123",
        verification_url=(
            "https://www.orbalacademy.com/verify/ODA-SAMPLE123"
        ),
        enrollment_date="2026-07-22",
    )

    output_path = BASE_DIR / "orbal_certificate_preview.pdf"

    with open(output_path, "wb") as f:
        f.write(sample)

    print(f"Certificate generated: {output_path}")
