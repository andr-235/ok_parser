from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Comment:
    id: str
    discussion_id: str
    group_id: str
    author_id: str
    author_name: str
    text: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    likes_count: int = 0
    reply_to_id: Optional[str] = None
    discussion_text: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "discussion_id": self.discussion_id,
            "group_id": self.group_id,
            "author_id": self.author_id,
            "author_name": self.author_name,
            "text": self.text,
            "created_at": self.created_at,
            "likes_count": self.likes_count,
            "reply_to_id": self.reply_to_id,
            "discussion_text": self.discussion_text,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Comment":
        return cls(
            id=data["id"],
            discussion_id=data["discussion_id"],
            group_id=data["group_id"],
            author_id=data["author_id"],
            author_name=data["author_name"],
            text=data["text"],
            created_at=data.get("created_at", datetime.now(timezone.utc)),
            likes_count=data.get("likes_count", 0),
            reply_to_id=data.get("reply_to_id"),
            discussion_text=data.get("discussion_text"),
        )

    @classmethod
    def from_api(
        cls,
        data: dict,
        discussion_id: str,
        group_id: str,
        user_info: Optional[dict] = None,
        discussion_text: Optional[str] = None,
    ) -> "Comment":
        author = data.get("author", {})
        author_id = str(author.get("uid", data.get("author_id", "")))
        
        if user_info:
            author_name = user_info.get("name", "")
            if not author_name:
                first_name = user_info.get("first_name", "")
                last_name = user_info.get("last_name", "")
                author_name = f"{first_name} {last_name}".strip()
        else:
            author_name = author.get("name", data.get("author_name", ""))
        
        created_ms = data.get("created_ms", data.get("date", 0))
        
        if isinstance(created_ms, int) and created_ms > 0:
            created_at = datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc)
        else:
            created_at = datetime.now(timezone.utc)

        return cls(
            id=str(data.get("id", "")),
            discussion_id=discussion_id,
            group_id=group_id,
            author_id=author_id,
            author_name=author_name or "",
            text=data.get("text", data.get("message", "")),
            created_at=created_at,
            likes_count=data.get("likes_count", data.get("like_count", 0)),
            reply_to_id=data.get("reply_to_comment_id"),
            discussion_text=discussion_text,
        )

