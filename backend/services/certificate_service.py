"""Professional Orbal Digital Academy certificate generator (ReportLab).
Optional assets configured by environment: CERT_LOGO_PATH, CERT_SEAL_PATH,
CERT_TRAINING_SIGNATURE_PATH, CERT_DIRECTOR_SIGNATURE_PATH.
"""
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

ACADEMY = 'ORBAL DIGITAL ACADEMY'
NAVY = HexColor('#102B5B')
BLUE = HexColor('#07509A')
LIGHT = HexColor('#8BA9D7')
OLIVE = HexColor('#6D6B0B')
ORANGE = HexColor('#FF874D')
INK = HexColor('#101828')

BASE_DIR = Path(__file__).resolve().parent.parent

LOGO_PATH = BASE_DIR / "assets" / "orbal_logo.png"

TRAINING_SIGNATURE_PATH = ( BASE_DIR / "assets" / "training_signature.png")

DIRECTOR_SIGNATURE_PATH = ( BASE_DIR / "assets" / "director_signature.png")

def _date(value):
    if isinstance(value, datetime):
        return value.strftime('%d %B %Y')
    if isinstance(value, date):
        return value.strftime('%d %B %Y')
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00')).strftime('%d %B %Y')
        except ValueError:
            return value
    return datetime.now(timezone.utc).strftime('%d %B %Y')


def _asset(c, path, x, y, w, h):

    if not path:
        return False

    if not os.path.isfile(path):
        print(f"Asset not found: {path}")
        return False

    try:
        image = ImageReader(path)

        c.drawImage(
            image,
            x,
            y,
            width=w,
            height=h,
            preserveAspectRatio=True,
            anchor="c",
            mask="auto"
        )

        return True

    except Exception as e:
        print(f"Failed to load certificate asset {path}: {e}")
        return False


def _fit(c, value, font, max_size, min_size, width):
    size = max_size
    while size > min_size and c.stringWidth(value, font, size) > width:
        size -= 0.5
    return size


def _wrap(c, text, font, size, width, max_lines=3):
    words = text.split()
    lines, line = [], ''
    for word in words:
        trial = (line + ' ' + word).strip()
        if c.stringWidth(trial, font, size) <= width:
            line = trial
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines[:max_lines]


def generate_certificate_pdf(
    student_name: str,
    course_title: str,
    completion_date: str | datetime | None = None,
    certificate_id: str | None = None,
    verification_url: str | None = None,
    enrollment_date: str | datetime | None = None,
    course_description: str | None = None,
) -> bytes:
    buf = io.BytesIO()
    W, H = landscape(A4)
    c = canvas.Canvas(buf, pagesize=(W, H), pageCompression=1)
    c.setTitle(f'{ACADEMY} - Certificate of Completion')
    c.setAuthor(ACADEMY)

    # Geometric border inspired by reference certificate
    m = 47
    c.setFillColor(BLUE)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(NAVY)
    c.rect(0, H-64, W, 64, fill=1, stroke=0)
    c.rect(W-56, 0, 56, H, fill=1, stroke=0)
    c.setFillColor(LIGHT)
    path = c.beginPath(); path.moveTo(160,H); path.lineTo(180,H); path.lineTo(112,H-64); path.lineTo(92,H-64); path.close()
    c.drawPath(path,fill=1,stroke=0)
    path = c.beginPath(); path.moveTo(W-205,0); path.lineTo(W-183,0); path.lineTo(W-112,65); path.lineTo(W-134,65); path.close()
    c.drawPath(path,fill=1,stroke=0)
    c.setFillColor(HexColor('#FFFFFF'))
    c.rect(m, 45, W-2*m, H-91, fill=1, stroke=0)

    # Official Orbal Digital Academy logo
        # ---------------------------------
    # Official Orbal Digital Academy Logo
    # ---------------------------------

    logo = os.getenv("CERT_LOGO_PATH") or str(LOGO_PATH)

    print("Certificate logo path:", logo)
    print("Certificate logo exists:", os.path.isfile(logo))

    if not _asset(c, logo, m + 19, H - 151, 76, 76):
        print("WARNING: Custom certificate logo could not be loaded.")

        c.setStrokeColor(OLIVE)
        c.setLineWidth(2)
        c.circle(m + 57, H - 113, 33, fill=0, stroke=1)

        c.setFillColor(OLIVE)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(
            m + 57,
            H - 116,
            "ODA"
        )

    c.setFillColor(OLIVE)
        
    heading_size = _fit(c, ACADEMY, 'Helvetica-Bold', 27, 18, W-270)
    c.setFont('Helvetica-Bold',heading_size)
    c.drawCentredString(W/2+28,H-116,ACADEMY)
    c.setFillColor(INK); c.setFont('Helvetica-Bold',9)
    if certificate_id:
        c.drawRightString(W-m-12,H-83,certificate_id)

    c.setFillColor(ORANGE); c.setFont('Helvetica-Bold',29)
    c.drawCentredString(W/2,H-177,'PROFESSIONAL CERTIFICATE')
    c.setFillColor(INK)
    title_size = _fit(c,course_title.upper(),'Helvetica-Bold',20,12,W-170)
    title_lines = _wrap(c,course_title.upper(),'Helvetica-Bold',title_size,W-165,2)
    for i,line in enumerate(title_lines):
        c.setFont('Helvetica-Bold',title_size)
        c.drawCentredString(W/2,H-210-i*22,line)

    c.setFillColor(ORANGE); c.setFont('Helvetica-Bold',15)
    c.drawCentredString(W/2,H-264,'This is to certify that')
    c.setFillColor(OLIVE)
    name_size = _fit(c,student_name,'Times-Italic',33,19,W-230)
    c.setFont('Times-Italic',name_size)
    c.drawCentredString(W/2,H-310,student_name)
    c.setStrokeColor(OLIVE); c.setLineWidth(1.1)
    c.line(m+90,H-321,W-m-90,H-321)

    description = course_description or 'has successfully completed the prescribed professional training and assessment requirements.'
    c.setFillColor(INK); c.setFont('Helvetica-Bold',12)
    desc_lines = _wrap(c,description,'Helvetica-Bold',12,W-225,3)
    for i,line in enumerate(desc_lines):
        c.drawCentredString(W/2,H-350-i*17,line)

    # Bottom: dates, signatures, seal, verification
    bottom = 72
    c.setFillColor(INK)
    c.setFont('Times-Bold',10)
    if enrollment_date:
        c.drawString(m+56,bottom+83,'Date enrolled:')
        c.setFont('Times-Roman',10)
        c.drawString(m+56,bottom+69,_date(enrollment_date))
    c.setFont('Times-Bold',10)
    c.drawString(W-m-210,bottom+83,'Date awarded:')
    c.setFont('Times-Roman',10)
    c.drawString(W-m-210,bottom+69,_date(completion_date))

       # ---------------------------------
    # Head of Training Signature
    # ---------------------------------

    training_signature = str(TRAINING_SIGNATURE_PATH)

    if not _asset(
        c,
        training_signature,
        m + 47,
        bottom + 28,
        95,
        35
    ):
        print("Head of Training signature not found")

    # ---------------------------------
    # Executive Director Signature
    # ---------------------------------

    director_signature = str(DIRECTOR_SIGNATURE_PATH)

    if not _asset(
        c,
        director_signature,
        W - m - 210,
        bottom + 28,
        95,
        35
    ):
        print("Executive Director signature not found")
        
    # ---------------------------------
    # Signatories' Names and Titles
    # ---------------------------------

    c.setFillColor(INK)

    c.setFont("Times-Bold", 12)

    c.drawString(
        m + 48,
        bottom + 16,
        "NAME OF HEAD OF TRAINING"
    )

    c.drawString(
        W - m - 210,
        bottom + 16,
        "NAME OF EXECUTIVE DIRECTOR"
    )

    c.setFont("Times-Roman", 9)

    c.drawString(
        m + 48,
        bottom + 3,
        "Head of Training"
    )

    c.drawString(
        W - m - 210,
        bottom + 3,
        "Executive Director"
    )

    if not _asset(c,os.getenv('CERT_SEAL_PATH',''),W/2-34,bottom+10,68,68):
        c.setFillColor(HexColor('#D5A72B')); c.circle(W/2,bottom+46,30,stroke=0,fill=1)
        c.setStrokeColor(HexColor('#FFF0AA')); c.setLineWidth(2); c.circle(W/2,bottom+46,24,stroke=1,fill=0)
        c.setFillColor(HexColor('#FFFFFF')); c.setFont('Helvetica-Bold',10)
        c.drawCentredString(W/2,bottom+43,'ODA')

    if verification_url:
        widget = qr.QrCodeWidget(verification_url)
        bounds = widget.getBounds()
        qsize = 43
        drawing = Drawing(qsize,qsize,transform=[qsize/(bounds[2]-bounds[0]),0,0,qsize/(bounds[3]-bounds[1]),0,0])
        drawing.add(widget)
        renderPDF.draw(drawing,c,W/2-qsize/2,52)
        c.setFillColor(INK); c.setFont('Helvetica',7)
        c.drawCentredString(W/2,47,'Scan to verify')

    c.showPage(); c.save()
    data=buf.getvalue();buf.close()
    if not data.startswith(b'%PDF-'):
        raise ValueError('Invalid PDF generated')
    return data

if __name__ == "__main__":

    sample = generate_certificate_pdf(
        student_name="Sample Student",
        course_title="Professional Certificate Course in Data Analytics",
        completion_date="2026-10-22T18:04:49.952434+00:00",
        certificate_id="ODA-SAMPLE123",
        verification_url="https://www.orbalacademy.com/verify/ODA-SAMPLE123",
        enrollment_date="2026-07-22"
    )

    output_path = BASE_DIR / "orbal_certificate_preview.pdf"

    with open(output_path, "wb") as f:
        f.write(sample)

    print("Generated:", len(sample), "bytes")
    print("Saved to:", output_path)
