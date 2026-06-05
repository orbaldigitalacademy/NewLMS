"""LMS FastAPI application entry point."""
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from pathlib import Path
from starlette.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# Configure logging early
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Local imports AFTER env load
from database import db, client  # noqa: E402
from utils.scheduler import start_scheduler, stop_scheduler  # noqa: E402
from utils.security import hash_password  # noqa: E402
from models.user import User  # noqa: E402
from models.course import Course  # noqa: E402
from models.lesson import Lesson, LessonResource  # noqa: E402
from models.testimonial import Testimonial  # noqa: E402

# Routers
from routers import auth as auth_router  # noqa: E402
from routers import courses as courses_router  # noqa: E402
from routers import lessons as lessons_router  # noqa: E402
from routers import enrollments as enrollments_router  # noqa: E402
from routers import payments as payments_router  # noqa: E402
from routers import testimonials as testimonials_router  # noqa: E402
from routers import uploads as uploads_router  # noqa: E402
from routers import contacts as contacts_router  # noqa: E402
from routers import admin as admin_router  # noqa: E402


async def seed_data():
    """Seed an admin and a few demo courses on first run."""
    # Seed admin
    admin_email = "admin@atlasacademy.io"
    existing_admin = await db.users.find_one({"email": admin_email})
    if not existing_admin:
        admin = User(
            email=admin_email,
            name="Atlas Admin",
            password_hash=hash_password("admin123"),
            role="admin",
            bio="Founding educator at Atlas Academy.",
        )
        await db.users.insert_one(admin.to_mongo())
        logger.info("Seeded admin user")
    admin_doc = await db.users.find_one({"email": admin_email})
    admin_id = admin_doc["_id"]
    admin_name = admin_doc["name"]

    # Seed student
    student_email = "student@atlasacademy.io"
    if not await db.users.find_one({"email": student_email}):
        student = User(
            email=student_email,
            name="Ada Lovelace",
            password_hash=hash_password("student123"),
            role="student",
        )
        await db.users.insert_one(student.to_mongo())
        logger.info("Seeded student user")

    # Seed courses
    if await db.courses.count_documents({}) == 0:
        seed_courses = [
            {
                "title": "Foundations of Modern Design",
                "slug": "foundations-of-modern-design",
                "short_description": "Type, color, grid, and rhythm—learn the building blocks of editorial-grade visual design.",
                "description": (
                    "A deep dive into composition, typography hierarchy, color theory and visual rhythm. "
                    "By the end of this course you will have a portfolio of three design exercises and a "
                    "vocabulary to critique any layout you encounter."
                ),
                "category": "Design",
                "level": "beginner",
                "price": 0.0,
                "thumbnail_url": "https://images.unsplash.com/photo-1512486130939-2c4f79935e4f?crop=entropy&cs=srgb&fm=jpg&w=1200&q=80",
                "tags": ["design", "typography", "fundamentals"],
                "is_published": True,
                "duration_minutes": 180,
            },
            {
                "title": "Full-Stack Engineering with FastAPI & React",
                "slug": "fullstack-fastapi-react",
                "short_description": "Ship production-grade APIs and modern React UIs—from data models to deployment.",
                "description": (
                    "An applied program covering FastAPI services, MongoDB modeling, JWT authentication, "
                    "React 19 with hooks, payment flows, file uploads, and reliable testing patterns."
                ),
                "category": "Engineering",
                "level": "intermediate",
                "price": 15000.0,
                "thumbnail_url": "https://images.unsplash.com/photo-1577985043696-8bd54d9f093f?crop=entropy&cs=srgb&fm=jpg&w=1200&q=80",
                "tags": ["fastapi", "react", "fullstack"],
                "is_published": True,
                "duration_minutes": 720,
            },
            {
                "title": "Strategic Product Thinking",
                "slug": "strategic-product-thinking",
                "short_description": "Frameworks for evaluating opportunity, sequencing bets, and building durable products.",
                "description": (
                    "A practitioner-led course on opportunity sizing, customer development, "
                    "and product strategy. Combines case studies with weekly exercises."
                ),
                "category": "Product",
                "level": "advanced",
                "price": 25000.0,
                "thumbnail_url": "https://images.pexels.com/photos/5553065/pexels-photo-5553065.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
                "tags": ["product", "strategy"],
                "is_published": True,
                "duration_minutes": 540,
            },
            {
                "title": "Writing for the Modern Web",
                "slug": "writing-for-modern-web",
                "short_description": "Develop a clear, confident voice for landing pages, essays and product copy.",
                "description": (
                    "Become a sharper writer by drafting and revising with established craft principles. "
                    "Includes weekly assignments and editor-style critiques."
                ),
                "category": "Writing",
                "level": "beginner",
                "price": 0.0,
                "thumbnail_url": "https://images.pexels.com/photos/5940844/pexels-photo-5940844.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
                "tags": ["writing", "communication"],
                "is_published": True,
                "duration_minutes": 240,
            },
        ]
        for c in seed_courses:
            course = Course(
                **c, instructor_id=admin_id, instructor_name=admin_name
            )
            await db.courses.insert_one(course.to_mongo())

            # Add lessons per course
            sample_lessons = [
                {
                    "title": "Introduction & Course Roadmap",
                    "description": "Orientation video and what you'll build.",
                    "order": 1,
                    "is_preview": True,
                    "duration_minutes": 8,
                    "video_url": "https://www.youtube.com/embed/dQw4w9WgXcQ",
                    "content_text": (
                        "Welcome to the course! This first lesson lays out the syllabus, "
                        "expectations and learning outcomes."
                    ),
                },
                {
                    "title": "Core Concepts",
                    "description": "Vocabulary and the mental model you need.",
                    "order": 2,
                    "duration_minutes": 22,
                    "video_url": "https://www.youtube.com/embed/jNQXAC9IVRw",
                    "content_text": (
                        "We'll cover the core vocabulary and mental models that you'll use "
                        "throughout the rest of the program. Take notes as you go."
                    ),
                    "resources": [
                        {
                            "name": "Lesson Notes (PDF)",
                            "url": "https://www.w3.org/WAI/WCAG21/working-examples/pdf-tags/dinos.pdf",
                            "type": "pdf",
                        }
                    ],
                },
                {
                    "title": "Hands-on Project",
                    "description": "Apply what you've learned in a guided project.",
                    "order": 3,
                    "duration_minutes": 45,
                    "video_url": "https://www.youtube.com/embed/9bZkp7q19f0",
                    "content_text": (
                        "Time to build. Follow along as we work through a guided project that "
                        "ties together everything from the previous lessons."
                    ),
                },
                {
                    "title": "Wrap-up & Next Steps",
                    "description": "Where to go from here.",
                    "order": 4,
                    "duration_minutes": 12,
                    "video_url": "https://www.youtube.com/embed/M7lc1UVf-VE",
                    "content_text": (
                        "Congratulations on reaching the final lesson. Here are recommended "
                        "next steps and reading."
                    ),
                },
            ]
            for sl in sample_lessons:
                resources = [LessonResource(**r) for r in sl.pop("resources", [])]
                lesson = Lesson(course_id=course.id, resources=resources, **sl)
                await db.lessons.insert_one(lesson.to_mongo())
        logger.info("Seeded courses and lessons")

    # Seed testimonials
    if await db.testimonials.count_documents({}) == 0:
        testimonials = [
            {
                "name": "Chioma Okeke",
                "role": "Designer, Lagos",
                "quote": "The Foundations course rewired how I look at every poster, app, and book cover. The critique sessions alone were worth it.",
                "rating": 5,
                "is_approved": True,
                "is_featured": True,
                "avatar_url": "https://images.unsplash.com/photo-1662850886700-4ec19bd30d11?crop=entropy&cs=srgb&fm=jpg&w=400&q=80",
            },
            {
                "name": "Marcus Adeyemi",
                "role": "Software Engineer",
                "quote": "I shipped my first production API in week three. Atlas Academy doesn't just teach—it makes you build.",
                "rating": 5,
                "is_approved": True,
                "is_featured": True,
                "avatar_url": "https://images.pexels.com/photos/8199172/pexels-photo-8199172.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=400&w=400",
            },
            {
                "name": "Zara Bello",
                "role": "Product Manager",
                "quote": "The product strategy lessons gave me a vocabulary for conversations I used to dread. My team has noticed.",
                "rating": 5,
                "is_approved": True,
                "is_featured": True,
            },
        ]
        for t in testimonials:
            tdoc = Testimonial(**t)
            await db.testimonials.insert_one(tdoc.to_mongo())
        logger.info("Seeded testimonials")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup
    await seed_data()
    start_scheduler()
    yield
    # Shutdown
    stop_scheduler()
    client.close()


app = FastAPI(title="LMS API", lifespan=lifespan)

api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"message": "LMS API ready"}


@api_router.get("/health")
async def health():
    return {"status": "ok"}


# Mount sub-routers
api_router.include_router(auth_router.router)
api_router.include_router(courses_router.router)
api_router.include_router(lessons_router.router)
api_router.include_router(enrollments_router.router)
api_router.include_router(payments_router.router)
api_router.include_router(testimonials_router.router)
api_router.include_router(uploads_router.router)
api_router.include_router(contacts_router.router)
api_router.include_router(admin_router.router)

app.include_router(api_router)

cors_origins = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", "").split(",")
    if origin.strip()
]

logger.info(f"CORS_ORIGINS raw: {os.environ.get('CORS_ORIGINS')}")
logger.info(f"CORS_ORIGINS parsed: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
