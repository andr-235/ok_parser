from typing import Optional
from pymongo.database import Database

from .base import BaseRepository
from ..models import Discussion


class DiscussionRepository(BaseRepository[Discussion]):
    def __init__(self, db: Database):
        super().__init__(db, "discussions")
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._collection.create_index("id", unique=True)
        self._collection.create_index("group_id")
        self._collection.create_index("object_type")
        self._collection.create_index("created_at")

    def _to_model(self, data: dict) -> Discussion:
        return Discussion.from_dict(data)

    def _to_dict(self, item: Discussion) -> dict:
        return item.to_dict()

    def find_by_id(self, discussion_id: str) -> Optional[Discussion]:
        return self.find_one({"id": discussion_id})

    def find_by_group(self, group_id: str) -> list[Discussion]:
        return self.find({"group_id": group_id})

    def upsert(self, discussion: Discussion) -> str:
        result = self._collection.update_one(
            {"id": discussion.id},
            {"$set": self._to_dict(discussion)},
            upsert=True,
        )
        return str(result.upserted_id or discussion.id)

