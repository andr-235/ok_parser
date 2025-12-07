from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Group:
    uid: str
    name: str
    description: Optional[str] = None
    members_count: int = 0
    photo_url: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "uid": self.uid,
            "name": self.name,
            "description": self.description,
            "members_count": self.members_count,
            "photo_url": self.photo_url,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Group":
        return cls(
            uid=data["uid"],
            name=data["name"],
            description=data.get("description"),
            members_count=data.get("members_count", 0),
            photo_url=data.get("photo_url"),
            created_at=data.get("created_at", datetime.now(timezone.utc)),
            updated_at=data.get("updated_at", datetime.now(timezone.utc)),
        )

    @classmethod
    def from_api(cls, data: dict) -> "Group":
        return cls(
            uid=str(data.get("uid", data.get("id", ""))),
            name=data.get("name", ""),
            description=data.get("description"),
            members_count=data.get("members_count", 0),
            photo_url=data.get("pic_avatar"),
        )

