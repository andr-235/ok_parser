from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Discussion:
    id: str
    group_id: str
    object_type: str
    title: Optional[str] = None
    message: Optional[str] = None
    owner_uid: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_comments_count: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "group_id": self.group_id,
            "object_type": self.object_type,
            "title": self.title,
            "message": self.message,
            "owner_uid": self.owner_uid,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "total_comments_count": self.total_comments_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Discussion":
        return cls(
            id=data["id"],
            group_id=data["group_id"],
            object_type=data["object_type"],
            title=data.get("title"),
            message=data.get("message"),
            owner_uid=data.get("owner_uid"),
            created_at=data.get("created_at", datetime.now(timezone.utc)),
            updated_at=data.get("updated_at", datetime.now(timezone.utc)),
            total_comments_count=data.get("total_comments_count", 0),
        )

    def get_url(self) -> str:
        if self.object_type == "GROUP_TOPIC":
            return f"https://ok.ru/discussions/1/{self.group_id}/{self.id}"
        elif self.object_type == "MOVIE":
            if self.owner_uid and self.owner_uid != self.group_id:
                return f"https://ok.ru/video/{self.owner_uid}/{self.id}"
            return f"https://ok.ru/video/{self.id}"
        elif self.object_type == "USER_STATUS":
            if self.owner_uid:
                return f"https://ok.ru/profile/{self.owner_uid}/statuses/{self.id}"
            return f"https://ok.ru/discussions/1/{self.group_id}/{self.id}"
        elif self.object_type == "USER_PHOTO":
            if self.owner_uid:
                return f"https://ok.ru/profile/{self.owner_uid}/photo/{self.id}"
            return f"https://ok.ru/discussions/1/{self.group_id}/{self.id}"
        else:
            return f"https://ok.ru/discussions/1/{self.group_id}/{self.id}"

    @classmethod
    def from_api(cls, data: dict, group_id: str) -> "Discussion":
        object_id = str(data.get("object_id", data.get("id", "")))
        object_type = data.get("object_type", "GROUP_TOPIC")
        
        creation_date = data.get("creation_date")
        created_at = datetime.now(timezone.utc)
        if creation_date:
            try:
                created_at = datetime.strptime(creation_date, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        
        return cls(
            id=object_id,
            group_id=group_id,
            object_type=object_type,
            title=data.get("title"),
            message=data.get("message"),
            owner_uid=data.get("owner_uid"),
            created_at=created_at,
            total_comments_count=data.get("total_comments_count", 0),
        )

