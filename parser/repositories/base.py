from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional
from pymongo.collection import Collection
from pymongo.database import Database

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    def __init__(self, db: Database, collection_name: str):
        self._db = db
        self._collection: Collection = db[collection_name]

    @abstractmethod
    def _to_model(self, data: dict) -> T:
        pass

    @abstractmethod
    def _to_dict(self, item: T) -> dict:
        pass

    def find(self, query: Optional[dict] = None) -> list[T]:
        query = query or {}
        return [self._to_model(doc) for doc in self._collection.find(query)]

    def find_one(self, query: dict) -> Optional[T]:
        doc = self._collection.find_one(query)
        return self._to_model(doc) if doc else None

    def insert(self, item: T) -> str:
        result = self._collection.insert_one(self._to_dict(item))
        return str(result.inserted_id)

    def insert_many(self, items: list[T]) -> list[str]:
        if not items:
            return []
        docs = [self._to_dict(item) for item in items]
        result = self._collection.insert_many(docs)
        return [str(id_) for id_ in result.inserted_ids]

    def update(self, query: dict, update_data: dict) -> int:
        result = self._collection.update_many(query, {"$set": update_data})
        return result.modified_count

    def delete(self, query: dict) -> int:
        result = self._collection.delete_many(query)
        return result.deleted_count

    def count(self, query: Optional[dict] = None) -> int:
        query = query or {}
        return self._collection.count_documents(query)

    def aggregate(self, pipeline: list[dict]) -> list[dict]:
        return list(self._collection.aggregate(pipeline))

