# Atlas Academy — LMS PRD

## Original Problem Statement
Create a LMS with the following backend file structure:
- `main.py`, `database.py`, `dependencies.py`, `auth.py`
- `models/`: user, course, lesson, payment, testimonial
- `routers/`: auth, courses, lessons, enrollments, payments, testimonials, uploads, contacts, admin
- `services/`: cloudinary_service, certificate_service, payment_service
- `utils/`: security, scheduler

## User Choices (from clarification)
- **Auth**: JWT-based custom (email/password)
- **Payments**: Paystack (placeholder keys)
- **Uploads**: Cloudinary (placeholder keys)
- **Lessons**: Video + text + PDFs
- **Features**: Student dashboard, course catalog, enrollments, lesson viewer, progress, certificates on completion, testimonials, contact, admin panel

## Architecture
- **Stack**: FastAPI + MongoDB (motor) + React 19 + Tailwind/shadcn
- **Auth**: JWT (HS256), bcrypt password hash, FastAPI HTTPBearer dependency
- **IDs**: UUID strings stored as Mongo `_id`, exposed as `id` via Pydantic base model
- **Files**: Cloudinary service (placeholder mode returns placehold.co URLs)
- **Payments**: Paystack HTTP API (initialize → redirect → callback verify → enroll). Returns 503 when not configured.
- **Background tasks**: APScheduler abandons stale pending payments every 30 min
- **Certificates**: ReportLab generates landscape A4 PDF with editorial styling

## User Personas
- **Student**: browses catalog, enrolls (free or paid), watches lessons, marks progress, downloads certificate
- **Admin**: manages courses, lessons, users, payments, testimonials, contact messages

## Implemented (2026-02)
- Backend: 9 routers, 5 model modules, 3 services, 2 utils, seed admin/student/4 courses (16 lessons total)/3 testimonials
- Frontend: Editorial design (Cormorant Garamond + Manrope, wine-red accent on bone background)
  - Pages: Home, Catalog (filters/search), Course Detail, Login, Register, Dashboard, Learn (video player + curriculum sidebar + progress), Contact, Payment Callback, Admin
  - Layout, Header (mobile menu), Footer, Protected routes
- Testing: 26/26 backend tests passing; full student & admin e2e flows passing

## Backlog (Next)
- **P0**: Replace placeholder Paystack & Cloudinary credentials → live paid-course flow
- **P1**: Course reviews/ratings per student, instructor profile pages
- **P1**: Quiz/assessment lessons, discussion threads per lesson
- **P2**: Email notifications via Resend (enrollment, completion, payment receipt)
- **P2**: Coupon/promo codes; bundle pricing
- **P2**: Analytics dashboard (per-course completion funnels)

## Test Credentials
| Role    | Email                       | Password   |
|---------|-----------------------------|------------|
| Admin   | admin@atlasacademy.io       | admin123   |
| Student | student@atlasacademy.io     | student123 |
