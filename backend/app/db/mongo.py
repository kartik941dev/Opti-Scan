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

    async def insert_many(self, docs: List[Dict[str, Any]]):
        inserted_ids = []
        for doc in docs:
            res = await self.insert_one(doc)
            inserted_ids.append(res.inserted_id)

        class ManyResult:
            def __init__(self, ids):
                self.inserted_ids = ids
        return ManyResult(inserted_ids)

    async def count_documents(self, filter_query: Optional[Dict[str, Any]] = None) -> int:
        filter_query = filter_query or {}
        cursor = self.find(filter_query)
        items = await cursor.to_list()
        return len(items)


class ResilientCollectionProxy:
    """Proxies Motor collection calls; seamlessly falls back to InMemoryCollection on connection failures."""

    def __init__(self, name: str, db_manager: "DatabaseManager"):
        self.name = name
        self.db_manager = db_manager

    def _get_fallback(self) -> InMemoryCollection:
        return self.db_manager.get_fallback_collection(self.name)

    async def insert_one(self, *args, **kwargs):
        if not self.db_manager.use_fallback and self.db_manager.db is not None:
            try:
                return await self.db_manager.db[self.name].insert_one(*args, **kwargs)
            except Exception:
                self.db_manager.use_fallback = True
        return await self._get_fallback().insert_one(*args, **kwargs)

    async def insert_many(self, *args, **kwargs):
        if not self.db_manager.use_fallback and self.db_manager.db is not None:
            try:
                return await self.db_manager.db[self.name].insert_many(*args, **kwargs)
            except Exception:
                self.db_manager.use_fallback = True
        return await self._get_fallback().insert_many(*args, **kwargs)

    async def find_one(self, *args, **kwargs):
        if not self.db_manager.use_fallback and self.db_manager.db is not None:
            try:
                return await self.db_manager.db[self.name].find_one(*args, **kwargs)
            except Exception:
                self.db_manager.use_fallback = True
        return await self._get_fallback().find_one(*args, **kwargs)

    def find(self, *args, **kwargs):
        if not self.db_manager.use_fallback and self.db_manager.db is not None:
            try:
                motor_cursor = self.db_manager.db[self.name].find(*args, **kwargs)

                class ResilientCursor:
                    def __init__(self, m_cursor, fallback_fn, args, kwargs):
                        self._m_cursor = m_cursor
                        self._fallback_fn = fallback_fn
                        self._args = args
                        self._kwargs = kwargs

                    async def to_list(self, length: Optional[int] = None):
                        try:
                            return await self._m_cursor.to_list(length)
                        except Exception:
                            fallback_col = self._fallback_fn()
                            cursor = fallback_col.find(*self._args, **self._kwargs)
                            return await cursor.to_list(length)

                    def __aiter__(self):
                        return self._m_cursor.__aiter__()

                return ResilientCursor(motor_cursor, self._get_fallback, args, kwargs)
            except Exception:
                self.db_manager.use_fallback = True
        return self._get_fallback().find(*args, **kwargs)

    async def update_one(self, *args, **kwargs):
        if not self.db_manager.use_fallback and self.db_manager.db is not None:
            try:
                return await self.db_manager.db[self.name].update_one(*args, **kwargs)
            except Exception:
                self.db_manager.use_fallback = True
        return await self._get_fallback().update_one(*args, **kwargs)

    async def delete_one(self, *args, **kwargs):
        if not self.db_manager.use_fallback and self.db_manager.db is not None:
            try:
                return await self.db_manager.db[self.name].delete_one(*args, **kwargs)
            except Exception:
                self.db_manager.use_fallback = True
        return await self._get_fallback().delete_one(*args, **kwargs)

    async def delete_many(self, *args, **kwargs):
        if not self.db_manager.use_fallback and self.db_manager.db is not None:
            try:
                return await self.db_manager.db[self.name].delete_many(*args, **kwargs)
            except Exception:
                self.db_manager.use_fallback = True
        return await self._get_fallback().delete_many(*args, **kwargs)

    async def count_documents(self, *args, **kwargs):
        if not self.db_manager.use_fallback and self.db_manager.db is not None:
            try:
                return await self.db_manager.db[self.name].count_documents(*args, **kwargs)
            except Exception:
                self.db_manager.use_fallback = True
        return await self._get_fallback().count_documents(*args, **kwargs)


class DatabaseManager:
    """Unified Database Handler managing Mongo async client with fallback."""

    def __init__(self):
        self.client = None
        self.db = None
        self.use_fallback = not HAS_MOTOR
        self.fallback_collections: Dict[str, InMemoryCollection] = {}
        self.proxies: Dict[str, ResilientCollectionProxy] = {}

    def connect(self):
        if not HAS_MOTOR:
            self.use_fallback = True
            return

        try:
            self.client = motor.motor_asyncio.AsyncIOMotorClient(
                MONGO_URI,
                serverSelectionTimeoutMS=1000,
            )
            self.db = self.client[DB_NAME]
            self.use_fallback = False
        except Exception:
            self.use_fallback = True

    def get_fallback_collection(self, collection_name: str) -> InMemoryCollection:
        if collection_name not in self.fallback_collections:
            self.fallback_collections[collection_name] = InMemoryCollection(collection_name)
        return self.fallback_collections[collection_name]

    def get_collection(self, collection_name: str):
        if collection_name not in self.proxies:
            self.proxies[collection_name] = ResilientCollectionProxy(collection_name, self)
        return self.proxies[collection_name]

    def close(self):
        if self.client:
            self.client.close()


db_manager = DatabaseManager()
db_manager.connect()


def get_collection(name: str):
    return db_manager.get_collection(name)

