# Backend additions for the Course landing page

Add these to your existing Course Pydantic model and Mongo document. All fields are **optional** — existing courses won't break.

---

## 1. Pydantic models (add to your `models.py` / wherever `Course` lives)

```python
from pydantic import BaseModel, Field
from typing import List, Optional


# --- Sub-models -------------------------------------------------------------

class Instructor(BaseModel):
    name: str
    photo: Optional[str] = None          # image URL
    qualifications: Optional[str] = None # e.g. "PhD in CS, M.Sc. Software Eng."
    experience: Optional[str] = None     # e.g. "12+ years industry & teaching"
    bio: Optional[str] = None


class Testimonial(BaseModel):
    name: str
    role: Optional[str] = None           # e.g. "Frontend Developer"
    rating: int = 5                      # 1..5
    quote: str
    photo: Optional[str] = None          # image URL


class CourseProject(BaseModel):
    title: str
    description: str


class FAQItem(BaseModel):
    q: str
    a: str


# --- Add these fields to your existing Course model -------------------------

class Course(BaseModel):
    # ...your existing fields (id, title, short_description, full_description,
    #    price, duration, image_url, learning_outcomes, etc.)...

    instructor: Optional[Instructor] = None
    testimonials: List[Testimonial] = Field(default_factory=list)
    projects: List[CourseProject] = Field(default_factory=list)
    faqs: List[FAQItem] = Field(default_factory=list)
    who_for: List[str] = Field(default_factory=list)
    requirements: List[str] = Field(default_factory=list)
```

Also add the same fields to your `CourseCreate` / `CourseUpdate` request models so admins can set them.

---

## 2. Site settings (for the "Why Choose Orbal Academy" section)

The frontend reads `settingsAPI.get()` → `data.why_choose_items`. Add this to your Settings model:

```python
class WhyChooseItem(BaseModel):
    icon: Optional[str] = None       # lucide-react icon name, e.g. "Rocket"
    title: str
    description: str


class SiteSettings(BaseModel):
    # ...your existing settings fields...
    why_choose_items: List[WhyChooseItem] = Field(default_factory=list)
```

Note: the frontend currently falls back to a static set of 4 icons (`Rocket`, `HeartHandshake`, `ShieldCheck`, `Lightbulb`). If you want admin-selectable icons, you'll need to map the string `icon` value to an icon component on the frontend — happy to add that mapping if useful.

---

## 3. Example MongoDB document shape

```json
{
  "id": "course_123",
  "title": "Full-Stack Web Development",
  "short_description": "...",
  "price": 75000,
  "duration": "12 weeks",
  "image_url": "...",
  "learning_outcomes": ["...", "..."],

  "instructor": {
    "name": "Dr. Adaeze Okafor",
    "photo": "https://...",
    "qualifications": "PhD in CS",
    "experience": "12+ years",
    "bio": "..."
  },
  "testimonials": [
    { "name": "Chinedu A.", "role": "Frontend Dev", "rating": 5,
      "quote": "...", "photo": "https://..." }
  ],
  "projects": [
    { "title": "Capstone Project", "description": "..." }
  ],
  "faqs": [
    { "q": "Do I need experience?", "a": "No..." }
  ],
  "who_for": [
    "Beginners switching into tech",
    "Self-taught learners wanting structure"
  ],
  "requirements": [
    "A laptop with stable internet",
    "~5 hours per week"
  ]
}
```

---

## 4. Migration note

Because all new fields are optional / default to empty lists, **no migration is required**. Existing courses will simply render with the frontend's built-in fallback content until you fill them in via the admin panel.
