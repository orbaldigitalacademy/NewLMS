from typing import Optional, List, Literal, Union
from pydantic import BaseModel, Field, AliasChoices, ConfigDict
from .base import BaseDocument


LevelType = Literal["beginner", "intermediate", "advanced"]


# ---------------------------------------------------------------------------
# Sub-models — each maps 1:1 to a section in CourseDetailPage.jsx.
# All fields have safe defaults so old courses that never set them still
# deserialize into empty sub-objects (the React page falls back to statics).
# ---------------------------------------------------------------------------

class Instructor(BaseModel):
    """Displayed in the 'Meet your instructor' section."""
    name: str = ""
    photo: str = ""
    qualifications: str = ""
    experience: str = ""
    bio: str = ""


class Project(BaseModel):
    """Portfolio project shown in the 'Projects you'll build' section."""
    title: str = ""
    description: str = ""
    image: str = ""


class Career(BaseModel):
    """Career opportunity shown in the Careers section."""
    role: str = ""
    salary: str = ""


class Testimonial(BaseModel):
    """Student review shown in the Testimonials section."""
    name: str = ""
    role: str = ""
    quote: str = ""
    photo: str = ""
    rating: int = Field(default=5, ge=1, le=5)


class WhyChooseItem(BaseModel):
    """
    Value-prop card in 'Why choose us'.
    `icon` is a string matching ICON_MAP on the frontend:
    Rocket / HeartHandshake / ShieldCheck / Lightbulb / Sparkles / Target /
    Award / GraduationCap. Unknown strings fall back safely on the client.
    """
    icon: str = "Rocket"
    title: str = ""
    description: str = ""


class CompareRow(BaseModel):
    """
    Row in the 'Orbal Academy vs. alternatives' table.

    Each column cell (`orbal`, `self`, `bootcamp`) is either:
      • True  → green check
      • False → red X
      • "partial" → amber dash
      • any other string → literal text (e.g. "8-12 weeks", "₦1.5M – ₦3M+")
    """
    feature: str = ""
    orbal: Union[bool, str] = False
    self: Union[bool, str] = False
    bootcamp: Union[bool, str] = False


class FAQ(BaseModel):
    """FAQ item shown in the accordion."""
    q: str = ""
    a: str = ""


# ---------------------------------------------------------------------------
# Course document
# ---------------------------------------------------------------------------

class Course(BaseDocument):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    # ---- core / hero ----
    title: str
    slug: str
    short_description: str
    # Renamed from `description` — React form sends `full_description`.
    # AliasChoices lets old records/clients using `description` still work.
    full_description: str = Field(
        default="",
        validation_alias=AliasChoices("full_description", "description"),
    )
    category: str = ""
    level: LevelType = "beginner"
    price: float = 0.0  # in NGN; 0 = free
    currency: str = "NGN"

    # Renamed from `thumbnail_url` — React form sends `image_url`.
    image_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("image_url", "thumbnail_url"),
    )
    video_url: Optional[str] = None

    # Instructor: legacy scalar fields (linking to a user) + new nested profile
    # displayed on the course page.
    instructor_id: str = ""
    instructor_name: str = ""
    instructor: Optional[Instructor] = None

    tags: List[str] = Field(default_factory=list)

    # Duration: keep the int for internal maths, add a human string for hero.
    duration: str = ""                # e.g. "8 weeks" — shown in the hero
    duration_minutes: int = 0         # for filtering / analytics

    is_published: bool = False
    enrollment_count: int = 0

    # ---- string-list sections ----
    learning_outcomes: List[str] = Field(default_factory=list)
    problems:          List[str] = Field(default_factory=list)
    who_for:           List[str] = Field(default_factory=list)
    requirements:      List[str] = Field(default_factory=list)
    offer_includes:    List[str] = Field(default_factory=list)

    # ---- array-of-object sections ----
    projects:     List[Project]       = Field(default_factory=list)
    careers:      List[Career]        = Field(default_factory=list)
    testimonials: List[Testimonial]   = Field(default_factory=list)
    why_choose:   List[WhyChooseItem] = Field(default_factory=list)
    compare_rows: List[CompareRow]    = Field(default_factory=list)
    faqs:         List[FAQ]           = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Create payload — everything the admin form can send at creation.
# ---------------------------------------------------------------------------

class CourseCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    title: str
    short_description: str
    full_description: str = Field(
        default="",
        validation_alias=AliasChoices("full_description", "description"),
    )
    category: str = ""
    level: LevelType = "beginner"
    price: float = 0.0

    image_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("image_url", "thumbnail_url"),
    )
    video_url: Optional[str] = None

    duration: str = ""
    duration_minutes: int = 0

    tags: List[str] = Field(default_factory=list)
    is_published: bool = False

    # nested / list sections
    instructor: Optional[Instructor] = None

    learning_outcomes: List[str] = Field(default_factory=list)
    problems:          List[str] = Field(default_factory=list)
    who_for:           List[str] = Field(default_factory=list)
    requirements:      List[str] = Field(default_factory=list)
    offer_includes:    List[str] = Field(default_factory=list)

    projects:     List[Project]       = Field(default_factory=list)
    careers:      List[Career]        = Field(default_factory=list)
    testimonials: List[Testimonial]   = Field(default_factory=list)
    why_choose:   List[WhyChooseItem] = Field(default_factory=list)
    compare_rows: List[CompareRow]    = Field(default_factory=list)
    faqs:         List[FAQ]           = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Update payload — every field optional so partial patches work
# (e.g. publish toggle sends only { is_published: true }).
#
# In the route, ALWAYS do:
#     data = payload.model_dump(exclude_unset=True, by_alias=False)
#     await db.courses.update_one({"_id": id}, {"$set": data})
# so unset sections don't get overwritten to empty.
# ---------------------------------------------------------------------------

class CourseUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    title: Optional[str] = None
    short_description: Optional[str] = None
    full_description: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("full_description", "description"),
    )
    category: Optional[str] = None
    level: Optional[LevelType] = None
    price: Optional[float] = None

    image_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("image_url", "thumbnail_url"),
    )
    video_url: Optional[str] = None

    duration: Optional[str] = None
    duration_minutes: Optional[int] = None

    tags: Optional[List[str]] = None
    is_published: Optional[bool] = None

    instructor: Optional[Instructor] = None

    learning_outcomes: Optional[List[str]] = None
    problems:          Optional[List[str]] = None
    who_for:           Optional[List[str]] = None
    requirements:      Optional[List[str]] = None
    offer_includes:    Optional[List[str]] = None

    projects:     Optional[List[Project]]       = None
    careers:      Optional[List[Career]]        = None
    testimonials: Optional[List[Testimonial]]   = None
    why_choose:   Optional[List[WhyChooseItem]] = None
    compare_rows: Optional[List[CompareRow]]    = None
    faqs:         Optional[List[FAQ]]           = None


# ---------------------------------------------------------------------------
# Enrollment — unchanged from your original.
# ---------------------------------------------------------------------------

class Enrollment(BaseDocument):
    user_id: str
    course_id: str
    progress: float = 0.0  # 0-100
    completed_lessons: List[str] = Field(default_factory=list)
    is_completed: bool = False
    completed_at: Optional[str] = None
    certificate_url: Optional[str] = None
