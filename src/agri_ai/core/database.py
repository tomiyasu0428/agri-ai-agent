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
        collection = await self.mongo_client.get_collection("daily_schedules")
        
        query = {
            "日付": date,
            "圃場別予定.作業者": worker_id
        }
        
        document = await collection.find_one(query)
        if not document:
            return []
        
        # Filter tasks for the specific worker
        worker_tasks = [
            task for task in document.get("圃場別予定", [])
            if task.get("作業者") == worker_id
        ]
        
        return worker_tasks
    
    async def complete_task(self, task_id: str, completion_data: Dict[str, Any]) -> bool:
        """Mark a task as completed and log the completion."""
        collection = await self.mongo_client.get_collection("daily_schedules")
        
        try:
            result = await collection.update_one(
                {"圃場別予定._id": task_id},
                {
                    "$set": {
                        "圃場別予定.$.ステータス": "完了",
                        "圃場別予定.$.完了時刻": completion_data.get("完了時刻"),
                        "圃場別予定.$.実施内容": completion_data.get("実施内容")
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
        collection = await self.mongo_client.get_collection("field_management")
        
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
        
        # Get pesticide history for rotation logic
        pesticide_history = field_data.get("防除履歴", [])
        
        # Simple recommendation logic (to be enhanced)
        recommendations = []
        
        # Get last used pesticides
        recent_pesticides = [
            entry.get("使用農薬", [])
            for entry in pesticide_history[-3:]  # Last 3 applications
        ]
        
        flattened_recent = [item for sublist in recent_pesticides for item in sublist]
        
        # Example pesticide rotation logic
        available_pesticides = [
            {"農薬名": "クプロシールド", "用途": "防除", "希釈倍率": 1000},
            {"農薬名": "アグロケア", "用途": "防除", "希釈倍率": 800},
            {"農薬名": "バイオガード", "用途": "防除", "希釈倍率": 1200}
        ]
        
        # Recommend pesticides not recently used
        for pesticide in available_pesticides:
            if pesticide["農薬名"] not in flattened_recent:
                recommendations.append(pesticide)
        
        return recommendations[:2]  # Return top 2 recommendations
    
    async def schedule_next_task(self, field_name: str, task_type: str, days_ahead: int = 7) -> bool:
        """Schedule next task automatically."""
        from datetime import datetime, timedelta
        
        collection = await self.mongo_client.get_collection("daily_schedules")
        
        next_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        
        new_task = {
            "圃場": field_name,
            "作業者": "未定",
            "タスク": task_type,
            "ステータス": "未着手",
            "予定時刻": f"{next_date}T09:00:00Z",
            "自動生成": True
        }
        
        try:
            # Check if schedule document exists for the date
            existing_schedule = await collection.find_one({"日付": next_date})
            
            if existing_schedule:
                # Add task to existing schedule
                await collection.update_one(
                    {"日付": next_date},
                    {"$push": {"圃場別予定": new_task}}
                )
            else:
                # Create new schedule document
                new_schedule = {
                    "日付": next_date,
                    "圃場別予定": [new_task]
                }
                await collection.insert_one(new_schedule)
            
            logger.info(f"Scheduled next {task_type} for {field_name} on {next_date}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to schedule next task: {e}")
            return False