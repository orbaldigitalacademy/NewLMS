"""Base model. API uses `id`. MongoDB stores `_id`. Conversion is explicit."""
import uuid
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class BaseDocument(BaseModel):
    """Base document model.

    API surface always uses `id` (string UUID).
    For Mongo storage we manually rename `id` -> `_id` in `to_mongo()` and reverse in
    `from_mongo()`. No Pydantic alias is used so FastAPI response_model serializes
    cleanly as `id`.
    """

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=_utcnow_iso)
    updated_at: str = Field(default_factory=_utcnow_iso)

    def to_mongo(self) -> dict:
        d = self.model_dump()
        d["_id"] = d.pop("id")
        return d

    @classmethod
    def from_mongo(cls, doc: dict | None):
        if doc is None:
            return None
        data = dict(doc)
        if "_id" in data and "id" not in data:
            data["id"] = data.pop("_id")
        else:
            data.pop("_id", None)
        return cls(**data)
