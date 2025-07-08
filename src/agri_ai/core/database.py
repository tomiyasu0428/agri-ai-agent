"""
MongoDB connection and database operations for the Agricultural AI Agent.
"""

import logging
import os
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class MongoDBClient:
    """MongoDB client for agricultural AI agent database operations."""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        self.mongodb_uri = os.getenv("MONGODB_URI")
        self.database_name = os.getenv("MONGODB_DATABASE", "agri_ai_db")
        
        if not self.mongodb_uri:
            raise ValueError("MONGODB_URI environment variable is required")
    
    async def connect(self) -> None:
        """Connect to MongoDB Atlas."""
        try:
            self.client = AsyncIOMotorClient(self.mongodb_uri)
            self.database = self.client[self.database_name]
            
            # Test connection
            await self.client.admin.command('ping')
            logger.info(f"Connected to MongoDB database: {self.database_name}")
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    async def get_collection(self, collection_name: str):
        """Get a collection from the database."""
        if self.database is None:
            raise RuntimeError("Database not connected")
        return self.database[collection_name]
    
    async def health_check(self) -> bool:
        """Check if the database connection is healthy."""
        try:
            await self.client.admin.command('ping')
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


class AgriDatabase:
    """High-level database operations for agricultural data."""
    
    def __init__(self, mongo_client: MongoDBClient):
        self.mongo_client = mongo_client
    
    async def get_today_tasks(self, worker_id: str, date: str) -> List[Dict[str, Any]]:
        """Get today's tasks for a specific worker."""
        collection = await self.mongo_client.get_collection("作業タスク")
        
        # Query for tasks on the specified date
        query = {
            "予定日": date
        }
        
        cursor = collection.find(query)
        tasks = await cursor.to_list(length=None)
        
        # Note: Current schema doesn't have direct worker assignment
        # Return all tasks for the date - can be filtered later
        logger.info(f"Found {len(tasks)} tasks for {date}")
        return tasks
    
    async def complete_task(self, task_id: str, completion_data: Dict[str, Any]) -> bool:
        """Mark a task as completed and log the completion."""
        collection = await self.mongo_client.get_collection("作業タスク")
        
        try:
            result = await collection.update_one(
                {"airtable_id": task_id},
                {
                    "$set": {
                        "ステータス": "✅ 完了",
                        "完了時刻": completion_data.get("完了時刻"),
                        "実施内容": completion_data.get("実施内容")
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Task {task_id} marked as completed")
                return True
            else:
                logger.warning(f"Task {task_id} not found or already completed")
                return False
                
        except Exception as e:
            logger.error(f"Failed to complete task {task_id}: {e}")
            return False
    
    async def get_field_status(self, field_name: str) -> Optional[Dict[str, Any]]:
        """Get current status of a specific field."""
        collection = await self.mongo_client.get_collection("圃場データ")
        
        query = {"圃場名": field_name}
        field_data = await collection.find_one(query)
        
        if field_data:
            logger.info(f"Retrieved status for field: {field_name}")
        else:
            logger.warning(f"Field not found: {field_name}")
        
        return field_data
    
    async def get_pesticide_recommendations(self, field_name: str, crop: str) -> List[Dict[str, Any]]:
        """Get pesticide recommendations for a specific field and crop."""
        collection = await self.mongo_client.get_collection("field_management")
        
        # Get field data
        field_data = await self.get_field_status(field_name)
        if not field_data:
            return []
        
        # Get general material recommendations (filter by material classification)
        material_collection = await self.mongo_client.get_collection("資材マスター")
        query = {"資材分類": "農薬"}
        cursor = material_collection.find(query)
        recommendations = await cursor.to_list(length=None)
        
        logger.info(f"Found {len(recommendations)} material recommendations for {crop}")
        return recommendations
    
    async def get_recent_material_usage(self, field_name: str) -> List[Dict[str, Any]]:
        """Get recent material usage for a specific field."""
        collection = await self.mongo_client.get_collection("資材使用ログ")
        
        query = {"圃場名": field_name}
        cursor = collection.find(query).sort("使用日", -1).limit(10)
        usage_logs = await cursor.to_list(length=None)
        
        logger.info(f"Found {len(usage_logs)} recent material usage logs for {field_name}")
        return usage_logs
    
    async def schedule_next_task(self, field_name: str, task_type: str, days_ahead: int = 7) -> bool:
        """Schedule next task automatically."""
        from datetime import datetime, timedelta
        
        collection = await self.mongo_client.get_collection("作業タスク")
        
        next_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        
        new_task = {
            "タスク名": task_type,
            "予定日": next_date,
            "ステータス": "🗓️ 予定",
            "メモ": "自動生成されたタスク",
            "migrated_at": datetime.now().isoformat(),
            "自動生成": True
        }
        
        try:
            await collection.insert_one(new_task)
            logger.info(f"Scheduled next {task_type} for {field_name} on {next_date}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to schedule next task: {e}")
            return False