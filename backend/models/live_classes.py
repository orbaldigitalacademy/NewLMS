from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum
import uuid


# ==================================================
# STATUS ENUM
# ==================================================
class LiveClassStatus(str, Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    COMPLETED = "completed"


# ==================================================
# RESOURCE (optional extension for future)
# ==================================================
class LiveClassResource(BaseModel):
    name: str
    url: str
    type: str  # pdf, link, video, etc.


# ==================================================
# MAIN LIVE CLASS MODEL
# ==================================================
class LiveClass(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    title: str
    description: Optional[str] = ""

    course_id: str
    meeting_url: str
    room_name: Optional[str] = None

    start_time: str  # ISO string
    end_time: str    # ISO string

    status: LiveClassStatus = LiveClassStatus.SCHEDULED

    recording_url: Optional[str] = ""
    recording_available: bool = False

    created_by: str

    deleted: bool = False
    deleted_at: Optional[str] = None

    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: Optional[str] = None


# ==================================================
# DB HELPERS
# ==================================================
class LiveClassInDB(LiveClass):
    """
    Internal representation (MongoDB).
    You can extend later if needed.
    """
    pass


# ==================================================
# RESPONSE HELPERS
# ==================================================
class LiveClassResponse(LiveClass):
    """
    Safe API response model.
    """
    pass
