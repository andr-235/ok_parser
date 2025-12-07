from datetime import datetime
from typing import Optional
from pymongo.database import Database

from .base import BaseRepository
from ..models import Comment


class CommentRepository(BaseRepository[Comment]):
    def __init__(self, db: Database):
        super().__init__(db, "comments")
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._collection.create_index("id", unique=True)
        self._collection.create_index("discussion_id")
        self._collection.create_index("group_id")
        self._collection.create_index("created_at")
        self._collection.create_index("author_id")

    def _to_model(self, data: dict) -> Comment:
        return Comment.from_dict(data)

    def _to_dict(self, item: Comment) -> dict:
        return item.to_dict()

    def find_by_discussion(self, discussion_id: str) -> list[Comment]:
        return self.find({"discussion_id": discussion_id})

    def find_by_group(self, group_id: str) -> list[Comment]:
        return self.find({"group_id": group_id})

    def find_by_author(self, author_id: str) -> list[Comment]:
        return self.find({"author_id": author_id})

    def find_by_date_range(
        self, start: datetime, end: Optional[datetime] = None
    ) -> list[Comment]:
        query: dict = {"created_at": {"$gte": start}}
        if end:
            query["created_at"]["$lte"] = end
        return self.find(query)

    def get_comments_by_date(self) -> list[dict]:
        pipeline = [
            {
                "$group": {
                    "_id": {
                        "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                    },
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"_id": 1}},
        ]
        return self.aggregate(pipeline)

    def get_top_authors(self, limit: int = 10) -> list[dict]:
        pipeline = [
            {"$group": {"_id": "$author_name", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": limit},
        ]
        return self.aggregate(pipeline)

    def upsert_many(self, comments: list[Comment]) -> int:
        if not comments:
            return 0
        
        operations = []
        from pymongo import UpdateOne
        
        for comment in comments:
            operations.append(
                UpdateOne(
                    {"id": comment.id},
                    {"$set": self._to_dict(comment)},
                    upsert=True,
                )
            )
        
        result = self._collection.bulk_write(operations)
        return result.upserted_count + result.modified_count

