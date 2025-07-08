"""
Tests for MongoDB database operations.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from src.agri_ai.core.database import MongoDBClient, AgriDatabase


class TestMongoDBClient:
    """Test MongoDB client operations."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock MongoDB client."""
        client = MongoDBClient()
        client.client = AsyncMock()
        client.database = AsyncMock()
        return client
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_client):
        """Test successful health check."""
        mock_client.client.admin.command.return_value = {"ok": 1}
        
        result = await mock_client.health_check()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_client):
        """Test failed health check."""
        mock_client.client.admin.command.side_effect = Exception("Connection failed")
        
        result = await mock_client.health_check()
        assert result is False


class TestAgriDatabase:
    """Test agricultural database operations."""
    
    @pytest.fixture
    def mock_mongo_client(self):
        """Create a mock MongoDB client."""
        return AsyncMock()
    
    @pytest.fixture
    def agri_db(self, mock_mongo_client):
        """Create AgriDatabase instance with mock client."""
        return AgriDatabase(mock_mongo_client)
    
    @pytest.mark.asyncio
    async def test_get_today_tasks_success(self, agri_db, mock_mongo_client):
        """Test successful retrieval of today's tasks."""
        # Mock collection
        mock_collection = AsyncMock()
        mock_mongo_client.get_collection.return_value = mock_collection
        
        # Mock document
        mock_document = {
            "日付": "2025-07-08",
            "圃場別予定": [
                {
                    "圃場": "鴨川家裏",
                    "作業者": "田中",
                    "タスク": "防除4回目",
                    "ステータス": "未着手"
                },
                {
                    "圃場": "山田畑",
                    "作業者": "佐藤",
                    "タスク": "施肥",
                    "ステータス": "未着手"
                }
            ]
        }
        
        mock_collection.find_one.return_value = mock_document
        
        # Test
        tasks = await agri_db.get_today_tasks("田中", "2025-07-08")
        
        assert len(tasks) == 1
        assert tasks[0]["作業者"] == "田中"
        assert tasks[0]["タスク"] == "防除4回目"
    
    @pytest.mark.asyncio
    async def test_get_today_tasks_no_tasks(self, agri_db, mock_mongo_client):
        """Test retrieval when no tasks found."""
        mock_collection = AsyncMock()
        mock_mongo_client.get_collection.return_value = mock_collection
        mock_collection.find_one.return_value = None
        
        tasks = await agri_db.get_today_tasks("田中", "2025-07-08")
        
        assert tasks == []
    
    @pytest.mark.asyncio
    async def test_complete_task_success(self, agri_db, mock_mongo_client):
        """Test successful task completion."""
        mock_collection = AsyncMock()
        mock_mongo_client.get_collection.return_value = mock_collection
        
        # Mock successful update
        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_collection.update_one.return_value = mock_result
        
        completion_data = {
            "完了時刻": "2025-07-08T15:30:00Z",
            "実施内容": "防除完了"
        }
        
        result = await agri_db.complete_task("task123", completion_data)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_get_field_status_success(self, agri_db, mock_mongo_client):
        """Test successful field status retrieval."""
        mock_collection = AsyncMock()
        mock_mongo_client.get_collection.return_value = mock_collection
        
        mock_field_data = {
            "圃場名": "鴨川家裏",
            "現在の作付": {
                "作物": "大豆",
                "品種": "とよまさり"
            }
        }
        
        mock_collection.find_one.return_value = mock_field_data
        
        result = await agri_db.get_field_status("鴨川家裏")
        
        assert result is not None
        assert result["圃場名"] == "鴨川家裏"
        assert result["現在の作付"]["作物"] == "大豆"