"""
データベースコネクションプールと最適化されたクエリ管理
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from cachetools import TTLCache
import hashlib
import json

from ..exceptions import DatabaseConnectionError, DatabaseQueryError
from ..utils.error_handling import DatabaseErrorHandler
from ..utils.config import get_settings

logger = logging.getLogger(__name__)


class DatabasePool:
    """データベースコネクションプール"""
    
    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        self.collections: Dict[str, AsyncIOMotorCollection] = {}
        
        # クエリキャッシュ（TTL: 5分）
        self.query_cache = TTLCache(maxsize=1000, ttl=300)
        
        # 接続状態管理
        self.is_connected = False
        self.connection_lock = asyncio.Lock()
        self.last_health_check = None
        self.health_check_interval = timedelta(minutes=5)
    
    async def connect(self) -> None:
        """データベースに接続"""
        async with self.connection_lock:
            if self.is_connected:
                return
            
            try:
                logger.info("Connecting to MongoDB...")
                
                self.client = AsyncIOMotorClient(
                    self.settings.mongodb_uri,
                    serverSelectionTimeoutMS=30000,
                    connectTimeoutMS=30000,
                    socketTimeoutMS=30000,
                    maxPoolSize=100,
                    minPoolSize=10,
                    maxIdleTimeMS=30000,
                    waitQueueMultiple=10,
                    retryWrites=True
                )
                
                # 接続テスト
                await self.client.admin.command('ping')
                
                self.database = self.client[self.settings.mongodb_database]
                self.is_connected = True
                self.last_health_check = datetime.now()
                
                logger.info(f"Successfully connected to MongoDB database: {self.settings.mongodb_database}")
                
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                logger.error(f"Failed to connect to MongoDB: {e}")
                raise DatabaseConnectionError(
                    f"MongoDB接続に失敗しました: {str(e)}",
                    context={"mongodb_uri": self.settings.mongodb_uri}
                )
            except Exception as e:
                logger.error(f"Unexpected error during MongoDB connection: {e}")
                raise DatabaseConnectionError(
                    f"データベース接続中に予期しないエラーが発生しました: {str(e)}"
                )
    
    async def disconnect(self) -> None:
        """データベースから切断"""
        async with self.connection_lock:
            if self.client:
                logger.info("Disconnecting from MongoDB...")
                self.client.close()
                self.client = None
                self.database = None
                self.collections.clear()
                self.query_cache.clear()
                self.is_connected = False
                logger.info("Disconnected from MongoDB")
    
    async def ensure_connection(self) -> None:
        """接続を確保（必要に応じて再接続）"""
        if not self.is_connected:
            await self.connect()
            return
        
        # ヘルスチェック
        now = datetime.now()
        if (self.last_health_check is None or 
            now - self.last_health_check > self.health_check_interval):
            try:
                await self.client.admin.command('ping')
                self.last_health_check = now
            except Exception as e:
                logger.warning(f"Health check failed, reconnecting: {e}")
                await self.disconnect()
                await self.connect()
    
    async def get_collection(self, collection_name: str) -> AsyncIOMotorCollection:
        """コレクションを取得（キャッシュ付き）"""
        await self.ensure_connection()
        
        if collection_name not in self.collections:
            self.collections[collection_name] = self.database[collection_name]
        
        return self.collections[collection_name]
    
    def _get_cache_key(self, operation: str, collection: str, query: Dict[str, Any]) -> str:
        """キャッシュキーを生成"""
        key_data = {
            "operation": operation,
            "collection": collection,
            "query": query
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    @DatabaseErrorHandler.handle_query_error(logger)
    async def find_one_cached(
        self, 
        collection_name: str, 
        filter_dict: Dict[str, Any], 
        projection: Optional[Dict[str, int]] = None,
        use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """キャッシュ付きfind_one"""
        cache_key = self._get_cache_key("find_one", collection_name, filter_dict)
        
        # キャッシュから検索
        if use_cache and cache_key in self.query_cache:
            logger.debug(f"Cache hit for find_one: {collection_name}")
            return self.query_cache[cache_key]
        
        # データベースから取得
        collection = await self.get_collection(collection_name)
        result = await collection.find_one(filter_dict, projection)
        
        # キャッシュに保存
        if use_cache and result:
            self.query_cache[cache_key] = result
        
        return result
    
    @DatabaseErrorHandler.handle_query_error(logger)
    async def find_many_cached(
        self,
        collection_name: str,
        filter_dict: Dict[str, Any],
        projection: Optional[Dict[str, int]] = None,
        sort: Optional[List[tuple]] = None,
        limit: Optional[int] = None,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """キャッシュ付きfind"""
        cache_key = self._get_cache_key("find_many", collection_name, {
            "filter": filter_dict,
            "projection": projection,
            "sort": sort,
            "limit": limit
        })
        
        # キャッシュから検索
        if use_cache and cache_key in self.query_cache:
            logger.debug(f"Cache hit for find_many: {collection_name}")
            return self.query_cache[cache_key]
        
        # データベースから取得
        collection = await self.get_collection(collection_name)
        cursor = collection.find(filter_dict, projection)
        
        if sort:
            cursor = cursor.sort(sort)
        if limit:
            cursor = cursor.limit(limit)
        
        result = await cursor.to_list(length=limit)
        
        # キャッシュに保存
        if use_cache:
            self.query_cache[cache_key] = result
        
        return result
    
    @DatabaseErrorHandler.handle_query_error(logger)
    async def aggregate_cached(
        self,
        collection_name: str,
        pipeline: List[Dict[str, Any]],
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """キャッシュ付きaggregate"""
        cache_key = self._get_cache_key("aggregate", collection_name, {"pipeline": pipeline})
        
        # キャッシュから検索
        if use_cache and cache_key in self.query_cache:
            logger.debug(f"Cache hit for aggregate: {collection_name}")
            return self.query_cache[cache_key]
        
        # データベースから取得
        collection = await self.get_collection(collection_name)
        cursor = collection.aggregate(pipeline)
        result = await cursor.to_list(length=None)
        
        # キャッシュに保存
        if use_cache:
            self.query_cache[cache_key] = result
        
        return result
    
    @DatabaseErrorHandler.handle_query_error(logger)
    async def insert_one(
        self,
        collection_name: str,
        document: Dict[str, Any]
    ) -> str:
        """ドキュメントを挿入"""
        collection = await self.get_collection(collection_name)
        result = await collection.insert_one(document)
        
        # キャッシュを無効化
        self._invalidate_cache(collection_name)
        
        return str(result.inserted_id)
    
    @DatabaseErrorHandler.handle_query_error(logger)
    async def update_one(
        self,
        collection_name: str,
        filter_dict: Dict[str, Any],
        update_dict: Dict[str, Any],
        upsert: bool = False
    ) -> bool:
        """ドキュメントを更新"""
        collection = await self.get_collection(collection_name)
        result = await collection.update_one(filter_dict, update_dict, upsert=upsert)
        
        # キャッシュを無効化
        self._invalidate_cache(collection_name)
        
        return result.modified_count > 0 or (upsert and result.upserted_id is not None)
    
    @DatabaseErrorHandler.handle_query_error(logger)
    async def delete_one(
        self,
        collection_name: str,
        filter_dict: Dict[str, Any]
    ) -> bool:
        """ドキュメントを削除"""
        collection = await self.get_collection(collection_name)
        result = await collection.delete_one(filter_dict)
        
        # キャッシュを無効化
        self._invalidate_cache(collection_name)
        
        return result.deleted_count > 0
    
    def _invalidate_cache(self, collection_name: str):
        """特定のコレクションのキャッシュを無効化"""
        keys_to_remove = []
        for key in self.query_cache.keys():
            try:
                # キーからコレクション名を抽出して判定
                # 実際の実装では、より効率的な方法を使用することを推奨
                if collection_name in str(key):
                    keys_to_remove.append(key)
            except:
                continue
        
        for key in keys_to_remove:
            self.query_cache.pop(key, None)
    
    def clear_cache(self):
        """全キャッシュをクリア"""
        self.query_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """キャッシュ統計を取得"""
        return {
            "cache_size": len(self.query_cache),
            "max_size": self.query_cache.maxsize,
            "ttl": self.query_cache.ttl,
            "hits": getattr(self.query_cache, 'hits', 0),
            "misses": getattr(self.query_cache, 'misses', 0)
        }


# グローバルデータベースプールインスタンス
_db_pool = None


async def get_database_pool() -> DatabasePool:
    """データベースプールを取得"""
    global _db_pool
    if _db_pool is None:
        _db_pool = DatabasePool()
        await _db_pool.connect()
    return _db_pool


async def close_database_pool():
    """データベースプールを閉じる"""
    global _db_pool
    if _db_pool:
        await _db_pool.disconnect()
        _db_pool = None