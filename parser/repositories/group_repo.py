from typing import Optional
from pymongo.database import Database

from .base import BaseRepository
from ..models import Group


class GroupRepository(BaseRepository[Group]):
    def __init__(self, db: Database):
        super().__init__(db, "groups")
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._collection.create_index("uid", unique=True)

    def _to_model(self, data: dict) -> Group:
        return Group.from_dict(data)

    def _to_dict(self, item: Group) -> dict:
        return item.to_dict()

    def find_by_uid(self, uid: str) -> Optional[Group]:
        return self.find_one({"uid": uid})

    def upsert(self, group: Group) -> str:
        result = self._collection.update_one(
            {"uid": group.uid},
            {"$set": self._to_dict(group)},
            upsert=True,
        )
        return str(result.upserted_id or group.uid)

