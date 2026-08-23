"""
MongoDB Database Connection & Fallback Data Access Layer.
"""

import os
import uuid
from typing import Any, Dict, List, Optional

try:
    import motor.motor_asyncio
    HAS_MOTOR = True
except ImportError:
    HAS_MOTOR = False

MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DB_NAME", "optiscan_db")


def _matches_filter(doc: Dict[str, Any], filter_query: Dict[str, Any]) -> bool:
    for k, v in filter_query.items():
        doc_val = doc.get(k)
        if isinstance(v, dict):
            for op, op_val in v.items():
                if op == "$ne" and doc_val == op_val:
                    return False
                if op == "$in" and doc_val not in op_val:
                    return False
                if op == "$nin" and doc_val in op_val:
                    return False
                if op == "$gt" and not (doc_val > op_val):
                    return False
                if op == "$lt" and not (doc_val < op_val):
                    return False
        elif doc_val != v:
            return False
    return True


class InMemoryCollection:
    """In-memory collection fallback when live MongoDB is unreachable."""

    def __init__(self, name: str):
        self.name = name
        self.documents: Dict[str, Dict[str, Any]] = {}

    async def insert_one(self, doc: Dict[str, Any]):
        doc_copy = dict(doc)
        if "_id" not in doc_copy or not doc_copy["_id"]:
            doc_copy["_id"] = str(uuid.uuid4())
        self.documents[doc_copy["_id"]] = doc_copy

        class Result:
            inserted_id = doc_copy["_id"]
        return Result()

    async def find_one(self, filter_query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        for doc in self.documents.values():
            if _matches_filter(doc, filter_query):
                return dict(doc)
        return None

    def find(self, filter_query: Optional[Dict[str, Any]] = None):
        filter_query = filter_query or {}
        matches = [dict(doc) for doc in self.documents.values() if _matches_filter(doc, filter_query)]

        class AsyncCursor:
            def __init__(self, items):
                self.items = items

            async def to_list(self, length: Optional[int] = None):
                if length is not None:
                    return self.items[:length]
                return self.items

            def __aiter__(self):
                self._iter = iter(self.items)
                return self

            async def __anext__(self):
                try:
                    return next(self._iter)
                except StopIteration:
                    raise StopAsyncIteration

        return AsyncCursor(matches)

    async def update_one(self, filter_query: Dict[str, Any], update_doc: Dict[str, Any]):
        doc = await self.find_one(filter_query)
        if doc:
            doc_id = doc["_id"]
            if "$set" in update_doc:
                self.documents[doc_id].update(update_doc["$set"])
            else:
                self.documents[doc_id].update(update_doc)

            class UpdateResult:
                matched_count = 1
                modified_count = 1
            return UpdateResult()

        class UpdateResultZero:
            matched_count = 0
            modified_count = 0
        return UpdateResultZero()

    async def delete_one(self, filter_query: Dict[str, Any]):
        doc = await self.find_one(filter_query)
        if doc and doc["_id"] in self.documents:
            del self.documents[doc["_id"]]

            class DeleteResult:
                deleted_count = 1
            return DeleteResult()

        class DeleteResultZero:
            deleted_count = 0
        return DeleteResultZero()

    async def delete_many(self, filter_query: Dict[str, Any]):
        cursor = self.find(filter_query)
        docs = await cursor.to_list()
        count = 0
        for doc in docs:
            if doc["_id"] in self.documents:
                del self.documents[doc["_id"]]
                count += 1

        class DeleteResult:
            deleted_count = count
        return DeleteResult()

    async def count_documents(self, filter_query: Dict[str, Any]) -> int:
        cursor = self.find(filter_query)
        items = await cursor.to_list()
        return len(items)


class DatabaseManager:
    """Unified Database Handler managing Mongo async client with fallback."""

    def __init__(self):
        self.client = None
        self.db = None
        self.use_fallback = not HAS_MOTOR
        self.fallback_collections: Dict[str, InMemoryCollection] = {}

    def connect(self):
        if not HAS_MOTOR:
            self.use_fallback = True
            return

        try:
            self.client = motor.motor_asyncio.AsyncIOMotorClient(
                MONGO_URI,
                serverSelectionTimeoutMS=2000,
            )
            self.db = self.client[DB_NAME]
            self.use_fallback = False
        except Exception:
            self.use_fallback = True

    def get_collection(self, collection_name: str):
        if self.use_fallback or self.db is None:
            if collection_name not in self.fallback_collections:
                self.fallback_collections[collection_name] = InMemoryCollection(collection_name)
            return self.fallback_collections[collection_name]
        return self.db[collection_name]

    def close(self):
        if self.client:
            self.client.close()


db_manager = DatabaseManager()
db_manager.connect()


def get_collection(name: str):
    return db_manager.get_collection(name)
