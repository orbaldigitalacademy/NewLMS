"""LMS FastAPI application entry point."""
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from pathlib import Path
from starlette.middleware.cors import CORSMiddleware
from routers import testimonials
from routers import live_classes as live_classes_router
from routers import uploads as uploads_router
from routers.settings import router as settings_router


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
from routers.payments import router as payments_router
from routers import profile
from routers.fx import fx_router


async def seed_data():
    """Seed an admin and a few demo courses on first run."""
    # Seed admin
    admin_email = "superadmin@gmail.com"
    existing_admin = await db.users.find_one({"email": admin_email})
    if not existing_admin:
        admin = User(
            email=admin_email,
            name="Orbal Admin",
            password_hash=hash_password("Oryiman@21"),
            role="admin",
            bio="Founding educator at Orbal Digital Academy.",
        )
        await db.users.insert_one(admin.to_mongo())
        logger.info("Seeded admin user")
    admin_doc = await db.users.find_one({"email": admin_email})
    admin_id = admin_doc["_id"]
    admin_name = admin_doc["name"]

    # Seed student
    student_email = "student@orbalacademy.com"
    if not await db.users.find_one({"email": student_email}):
        student = User(
            email=student_email,
            name="Ada Lovelace",
            password_hash=hash_password("Pioneerstudent"),
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
                "user_name": "Abutu Gabriel, Lagos Nigeria",
                "content": (
                    "Orbal Digital Academy played a key role in my career growth. "
                    "I joined the January 2026 cohort, and by February, I secured a position as an Inventory Officer at a multinational fashion company. "
                    "During my interview, I confidently demonstrated What-If Analysis and Power BI visualization skills I gained from the training, and I was asked to resume the very next day. "
                    "I'm sincerely grateful to Dr. Moses Kor for the exceptional training and mentorship."
                ),
                "rating": 5,
                "is_approved": True,
                "is_featured": True,
                "avatar_url": "/images/Abu.png",
},
            },
            {
                "user_name": "Godwin Ifer",
                "content": (
                    "Before joining Orbal Digital Academy, I only knew basic Excel. "
                    "Within three months, I was building interactive Power BI dashboards "
                    "and analyzing business data confidently. The practical assignments "
                    "made all the difference."
                ),
                "rating": 5,
                "is_approved": True,
                "is_featured": True,
                avatar_url": "/images/ordue.jpg",
            },
            {
                "user_name": "Timothy Terver",
                "content": (
                    "The Data Analytics training at Orbal Digital Academy significantly improved my skills in Microsoft Excel and enhanced my proficiency in Power BI. "
                    "I have been able to apply these skills in my daily tasks and in preparing my office's monthly reports, making my work more efficient and effective. "
                ),
                "rating": 5,
                "is_approved": True,
                "is_featured": False,
                avatar_url": "/images/bember.jpg",
            },
            {
                "user_name": "Monica Quaqua",
                "content": (
                    "The Online Data Analysis course has significantly strengthened my skills as a Monitoring, Evaluation, and Learning (MEL) professional, "
                    "equipping me with practical experience in Python, Excel, Power B, SQL and other data analysis and visualization tools "
                ),
                "rating": 5,
                "is_approved": True,
                "is_featured": False,
                "avatar_url": "/images/Monica Quaqua.jpeg",
            },
            {
                "user_name": "Hamza Ibrahim",
                "content": (
                    "The training really helped me a lot. I learned discipline and how to properly analyze my business, and it has made things much easier for me. "
                    "Thank you for the impactful training. "
                ),
                "rating": 4,
                "is_approved": True,
                "is_featured": True,
                "avatar_url": "/images/Hamza.jpeg",
            },

            {
                "user_name": "Bassey Friday",
                "content": (
                    "One thing that stood out was the emphasis on solving real business "
                    "problems rather than simply learning software. That practical mindset "
                    "has been invaluable."
                ),
                "rating": 4,
                "is_approved": True,
                "is_featured": False,
                avatar_url": "/images/basseyimage.jpg",
            },
            {
                "user_name": "Jay Sackie Menniboe",
                "content": (
                    "I'm truly grateful to God for Mr. Moses and his team. "
                    "The Data Analytics training anchored by Mr. Moses has practically prepared me for my specialty program (Health Knowledge & Informatica). "
                ),
                "rating": 5,
                "is_approved": True,
                "is_featured": False,
                 avatar_url": "/images/Jay Sachie.jpeg",
            },
            {
                "user_name": "Dorcas Moses",
                "content": (
                    "The Python for Data Analysis module completely changed how I work "
                    "with data. Tasks that used to take hours in Excel now take just "
                    "a few minutes."
                ),
                "rating": 4,
                "is_approved": True,
                "is_featured": False,
                avatar_url": "/images/Doo.jpg",
            },
            {
                "user_name": "Judith Timothy",
                "content": (
                    "The mentorship didn't end after classes. We received career advice, "
                    "CV reviews, and interview preparation that helped me transition into "
                    "my first data role."
                ),
                "rating": 5,
                "is_approved": True,
                "is_featured": True,
                avatar_url": "/images/judiimage.jpg",
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

@app.middleware("http")
async def log_origin(request, call_next):
    print("ORIGIN:", request.headers.get("origin"))
    response = await call_next(request)
    return response

api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"message": "LMS API ready"}


@api_router.get("/health")
async def health():
    return {"status": "ok"}

origins = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", "").split(",")
    if origin.strip()
]
print("CORS Origins:", origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount sub-routers
api_router.include_router(auth_router.router)
api_router.include_router(courses_router.router)
api_router.include_router(lessons_router.router)
api_router.include_router(enrollments_router.router)
api_router.include_router(payments_router)
api_router.include_router(testimonials_router.router)
api_router.include_router(uploads_router.router)
api_router.include_router(contacts_router.router)
api_router.include_router(admin_router.router)
api_router.include_router(live_classes_router.router)

app.include_router(settings_router, prefix="/api")
app.include_router(api_router)
app.include_router(testimonials.router)
app.include_router(uploads_router.router,prefix="/api",)
app.include_router(profile.router, prefix="/api")
app.include_router(fx_router, prefix="/api")





