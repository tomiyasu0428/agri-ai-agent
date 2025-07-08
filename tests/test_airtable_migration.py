"""
Tests for Airtable to MongoDB migration.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.agri_ai.utils.airtable_client import AirtableClient, AirtableToMongoMigrator


class TestAirtableClient:
    """Test Airtable client functionality."""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings with Airtable configuration."""
        settings = MagicMock()
        settings.airtable_api_key = "test_api_key"
        settings.airtable_base_id = "test_base_id"
        return settings
    
    @pytest.fixture
    def mock_airtable_client(self, mock_settings):
        """Create a mock Airtable client."""
        with patch('src.agri_ai.utils.airtable_client.get_settings', return_value=mock_settings):
            with patch('src.agri_ai.utils.airtable_client.Api') as mock_api:
                mock_base = MagicMock()
                mock_api.return_value.base.return_value = mock_base
                
                client = AirtableClient()
                client.base = mock_base
                return client
    
    def test_get_all_records_success(self, mock_airtable_client):
        """Test successful record retrieval."""
        # Mock table and records
        mock_table = MagicMock()
        mock_records = [
            {
                "id": "rec123",
                "createdTime": "2025-07-08T10:00:00.000Z",
                "fields": {"圃場": "鴨川家裏", "作物": "大豆"}
            }
        ]
        mock_table.all.return_value = mock_records
        mock_airtable_client.base.table.return_value = mock_table
        
        # Test
        records = mock_airtable_client.get_all_records("test_table")
        
        assert len(records) == 1
        assert records[0]["id"] == "rec123"
        assert records[0]["fields"]["圃場"] == "鴨川家裏"
    
    def test_get_all_records_error(self, mock_airtable_client):
        """Test record retrieval with error."""
        mock_table = MagicMock()
        mock_table.all.side_effect = Exception("API Error")
        mock_airtable_client.base.table.return_value = mock_table
        
        records = mock_airtable_client.get_all_records("test_table")
        
        assert records == []
    
    def test_get_table_schema_success(self, mock_airtable_client):
        """Test successful schema retrieval."""
        mock_table = MagicMock()
        mock_records = [
            {
                "id": "rec123",
                "fields": {"圃場": "鴨川家裏", "作物": "大豆", "面積": "10a"}
            }
        ]
        mock_table.all.return_value = mock_records
        mock_airtable_client.base.table.return_value = mock_table
        
        schema = mock_airtable_client.get_table_schema("test_table")
        
        assert "fields" in schema
        assert "圃場" in schema["fields"]
        assert "作物" in schema["fields"]
        assert "面積" in schema["fields"]
        assert schema["record_count"] == 1
    
    def test_list_tables(self, mock_airtable_client):
        """Test table listing."""
        # Mock successful table access
        mock_table = MagicMock()
        mock_table.all.return_value = [{"id": "test"}]
        mock_airtable_client.base.table.return_value = mock_table
        
        tables = mock_airtable_client.list_tables()
        
        # Should find at least some common table names
        assert isinstance(tables, list)


class TestAirtableToMongoMigrator:
    """Test the migration functionality."""
    
    @pytest.fixture
    def mock_airtable_client(self):
        """Create a mock Airtable client."""
        return MagicMock()
    
    @pytest.fixture
    def mock_mongo_client(self):
        """Create a mock MongoDB client."""
        return AsyncMock()
    
    @pytest.fixture
    def migrator(self, mock_airtable_client, mock_mongo_client):
        """Create a migrator instance."""
        return AirtableToMongoMigrator(mock_airtable_client, mock_mongo_client)
    
    def test_transform_daily_schedule(self, migrator):
        """Test daily schedule transformation."""
        airtable_record = {
            "id": "rec123",
            "createdTime": "2025-07-08T10:00:00.000Z",
            "fields": {
                "日付": "2025-07-08",
                "圃場": "鴨川家裏",
                "作業者": "田中",
                "タスク": "防除4回目",
                "ステータス": "未着手"
            }
        }
        
        transformed = migrator._transform_airtable_record(airtable_record, "daily_schedules")
        
        assert transformed["airtable_id"] == "rec123"
        assert transformed["日付"] == "2025-07-08"
        assert len(transformed["圃場別予定"]) == 1
        assert transformed["圃場別予定"][0]["圃場"] == "鴨川家裏"
        assert transformed["圃場別予定"][0]["作業者"] == "田中"
    
    def test_transform_field_management(self, migrator):
        """Test field management transformation."""
        airtable_record = {
            "id": "rec456",
            "createdTime": "2025-07-08T10:00:00.000Z",
            "fields": {
                "圃場名": "鴨川家裏",
                "作物": "大豆",
                "品種": "とよまさり",
                "播種日": "2025-05-15",
                "面積": "10a"
            }
        }
        
        transformed = migrator._transform_airtable_record(airtable_record, "圃場管理")
        
        assert transformed["airtable_id"] == "rec456"
        assert transformed["圃場名"] == "鴨川家裏"
        assert transformed["現在の作付"]["作物"] == "大豆"
        assert transformed["現在の作付"]["品種"] == "とよまさり"
        assert transformed["面積"] == "10a"
    
    def test_transform_pesticide_master(self, migrator):
        """Test pesticide master transformation."""
        airtable_record = {
            "id": "rec789",
            "createdTime": "2025-07-08T10:00:00.000Z",
            "fields": {
                "農薬名": "クプロシールド",
                "成分": "銅化合物",
                "用途": "防除",
                "希釈倍率": "1000",
                "使用間隔": "7日"
            }
        }
        
        transformed = migrator._transform_airtable_record(airtable_record, "農薬マスター")
        
        assert transformed["airtable_id"] == "rec789"
        assert transformed["農薬名"] == "クプロシールド"
        assert transformed["成分"] == "銅化合物"
        assert transformed["希釈倍率"] == "1000"
        assert transformed["使用間隔"] == "7日"
    
    @pytest.mark.asyncio
    async def test_migrate_table_success(self, migrator, mock_airtable_client, mock_mongo_client):
        """Test successful table migration."""
        # Mock Airtable data
        mock_records = [
            {
                "id": "rec123",
                "createdTime": "2025-07-08T10:00:00.000Z",
                "fields": {"圃場": "鴨川家裏", "作物": "大豆"}
            }
        ]
        mock_airtable_client.get_all_records.return_value = mock_records
        
        # Mock MongoDB collection
        mock_collection = AsyncMock()
        mock_result = MagicMock()
        mock_result.inserted_ids = ["id1"]
        mock_collection.insert_many.return_value = mock_result
        mock_mongo_client.get_collection.return_value = mock_collection
        
        # Test migration
        result = await migrator.migrate_table("test_table")
        
        assert result["success"] is True
        assert result["records_migrated"] == 1
        assert result["table_name"] == "test_table"
        assert len(result["errors"]) == 0
    
    @pytest.mark.asyncio
    async def test_migrate_table_no_records(self, migrator, mock_airtable_client, mock_mongo_client):
        """Test table migration with no records."""
        mock_airtable_client.get_all_records.return_value = []
        
        result = await migrator.migrate_table("empty_table")
        
        assert result["success"] is False
        assert result["records_migrated"] == 0
        assert "No records found" in result["errors"][0]
    
    @pytest.mark.asyncio
    async def test_migrate_all_tables(self, migrator, mock_airtable_client, mock_mongo_client):
        """Test migrating all tables."""
        # Mock table list
        mock_airtable_client.list_tables.return_value = ["daily_schedules", "圃場管理"]
        
        # Mock migration results
        with patch.object(migrator, 'migrate_table') as mock_migrate:
            mock_migrate.side_effect = [
                {"success": True, "records_migrated": 5, "errors": []},
                {"success": True, "records_migrated": 3, "errors": []}
            ]
            
            result = await migrator.migrate_all_tables()
            
            assert result["tables_migrated"] == 2
            assert result["total_records"] == 8
            assert len(result["table_results"]) == 2