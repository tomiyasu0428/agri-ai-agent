"""
Airtable client for data retrieval and migration.
"""

import logging
from typing import Dict, Any, List, Optional
from pyairtable import Api, Base, Table
from pyairtable.formulas import match
import asyncio
from datetime import datetime

from .config import get_settings

logger = logging.getLogger(__name__)


class AirtableClient:
    """Client for interacting with Airtable API."""
    
    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.airtable_api_key
        self.base_id = self.settings.airtable_base_id
        
        if not self.api_key or not self.base_id:
            raise ValueError("Airtable API key and base ID are required")
        
        self.api = Api(self.api_key)
        self.base = self.api.base(self.base_id)
    
    def get_table(self, table_name: str) -> Table:
        """Get a specific table from the base."""
        return self.base.table(table_name)
    
    def get_all_records(self, table_name: str) -> List[Dict[str, Any]]:
        """Get all records from a table."""
        try:
            table = self.get_table(table_name)
            records = table.all()
            logger.info(f"Retrieved {len(records)} records from {table_name}")
            return records
        except Exception as e:
            logger.error(f"Error retrieving records from {table_name}: {e}")
            return []
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get the schema/structure of a table."""
        try:
            table = self.get_table(table_name)
            # Get a sample record to understand the structure
            sample_records = table.all(max_records=1)
            
            if not sample_records:
                return {"fields": [], "sample": None}
            
            sample_record = sample_records[0]
            fields = list(sample_record.get("fields", {}).keys())
            
            return {
                "fields": fields,
                "sample": sample_record,
                "record_count": len(table.all())
            }
        except Exception as e:
            logger.error(f"Error getting schema for {table_name}: {e}")
            return {"fields": [], "sample": None, "error": str(e)}
    
    def list_tables(self) -> List[str]:
        """List all tables in the base."""
        try:
            # This is a simplified approach - in practice, you'd need to
            # use the Airtable Meta API or have the table names configured
            common_table_names = [
                "daily_schedules", "圃場管理", "作物マスター", "農薬マスター",
                "作業履歴", "作業者マスター", "天候データ", "スケジュール管理"
            ]
            
            existing_tables = []
            for table_name in common_table_names:
                try:
                    table = self.get_table(table_name)
                    # Try to get schema to verify table exists
                    table.all(max_records=1)
                    existing_tables.append(table_name)
                except:
                    continue
            
            return existing_tables
        except Exception as e:
            logger.error(f"Error listing tables: {e}")
            return []


class AirtableToMongoMigrator:
    """Migrates data from Airtable to MongoDB."""
    
    def __init__(self, airtable_client: AirtableClient, mongo_client):
        self.airtable_client = airtable_client
        self.mongo_client = mongo_client
        self.migration_log = []
    
    def _transform_airtable_record(self, record: Dict[str, Any], table_name: str) -> Dict[str, Any]:
        """Transform Airtable record to MongoDB document format."""
        # Extract fields from Airtable record
        fields = record.get("fields", {})
        
        # Create MongoDB document
        mongo_doc = {
            "airtable_id": record.get("id"),
            "created_time": record.get("createdTime"),
            "table_source": table_name,
            "migrated_at": datetime.now().isoformat()
        }
        
        # Add all fields to the document
        mongo_doc.update(fields)
        
        # Table-specific transformations
        if table_name == "daily_schedules":
            mongo_doc = self._transform_daily_schedule(mongo_doc)
        elif table_name == "圃場管理":
            mongo_doc = self._transform_field_management(mongo_doc)
        elif table_name == "作物マスター":
            mongo_doc = self._transform_crop_master(mongo_doc)
        elif table_name == "農薬マスター":
            mongo_doc = self._transform_pesticide_master(mongo_doc)
        elif table_name == "作業履歴":
            mongo_doc = self._transform_work_history(mongo_doc)
        
        return mongo_doc
    
    def _transform_daily_schedule(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Transform daily schedule record."""
        # Convert to the expected MongoDB format
        transformed = {
            "airtable_id": doc.get("airtable_id"),
            "日付": doc.get("日付") or doc.get("Date"),
            "圃場別予定": [],
            "migrated_at": doc.get("migrated_at")
        }
        
        # Create a task entry
        task_entry = {
            "圃場": doc.get("圃場") or doc.get("Field"),
            "作業者": doc.get("作業者") or doc.get("Worker"),
            "タスク": doc.get("タスク") or doc.get("Task"),
            "ステータス": doc.get("ステータス") or doc.get("Status", "未着手"),
            "予定時刻": doc.get("予定時刻") or doc.get("Scheduled Time"),
            "実施時刻": doc.get("実施時刻") or doc.get("Actual Time"),
            "備考": doc.get("備考") or doc.get("Notes")
        }
        
        transformed["圃場別予定"].append(task_entry)
        return transformed
    
    def _transform_field_management(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Transform field management record."""
        return {
            "airtable_id": doc.get("airtable_id"),
            "圃場名": doc.get("圃場名") or doc.get("Field Name"),
            "現在の作付": {
                "作物": doc.get("作物") or doc.get("Crop"),
                "品種": doc.get("品種") or doc.get("Variety"),
                "播種日": doc.get("播種日") or doc.get("Planting Date"),
                "収穫予定": doc.get("収穫予定") or doc.get("Harvest Date")
            },
            "防除履歴": self._parse_pesticide_history(doc),
            "農薬使用制限": doc.get("農薬使用制限") or doc.get("Pesticide Restrictions", {}),
            "面積": doc.get("面積") or doc.get("Area"),
            "土壌条件": doc.get("土壌条件") or doc.get("Soil Condition"),
            "migrated_at": doc.get("migrated_at")
        }
    
    def _transform_crop_master(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Transform crop master record."""
        return {
            "airtable_id": doc.get("airtable_id"),
            "作物名": doc.get("作物名") or doc.get("Crop Name"),
            "品種": doc.get("品種") or doc.get("Variety"),
            "生育期間": doc.get("生育期間") or doc.get("Growing Period"),
            "主要病害虫": doc.get("主要病害虫") or doc.get("Main Pests"),
            "推奨農薬": doc.get("推奨農薬") or doc.get("Recommended Pesticides"),
            "栽培ポイント": doc.get("栽培ポイント") or doc.get("Cultivation Points"),
            "migrated_at": doc.get("migrated_at")
        }
    
    def _transform_pesticide_master(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Transform pesticide master record."""
        return {
            "airtable_id": doc.get("airtable_id"),
            "農薬名": doc.get("農薬名") or doc.get("Pesticide Name"),
            "成分": doc.get("成分") or doc.get("Active Ingredient"),
            "用途": doc.get("用途") or doc.get("Purpose"),
            "対象作物": doc.get("対象作物") or doc.get("Target Crops"),
            "希釈倍率": doc.get("希釈倍率") or doc.get("Dilution Ratio"),
            "使用間隔": doc.get("使用間隔") or doc.get("Application Interval"),
            "注意事項": doc.get("注意事項") or doc.get("Precautions"),
            "migrated_at": doc.get("migrated_at")
        }
    
    def _transform_work_history(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Transform work history record."""
        return {
            "airtable_id": doc.get("airtable_id"),
            "実施日": doc.get("実施日") or doc.get("Date"),
            "圃場": doc.get("圃場") or doc.get("Field"),
            "作業内容": doc.get("作業内容") or doc.get("Work Content"),
            "作業者": doc.get("作業者") or doc.get("Worker"),
            "使用農薬": doc.get("使用農薬") or doc.get("Pesticides Used"),
            "使用量": doc.get("使用量") or doc.get("Amount Used"),
            "天候": doc.get("天候") or doc.get("Weather"),
            "結果": doc.get("結果") or doc.get("Result"),
            "migrated_at": doc.get("migrated_at")
        }
    
    def _parse_pesticide_history(self, doc: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse pesticide history from various possible formats."""
        history = []
        
        # Try to extract from different possible field names
        history_fields = [
            "防除履歴", "Pesticide History", "防除記録", "Treatment History"
        ]
        
        for field in history_fields:
            if field in doc and doc[field]:
                if isinstance(doc[field], list):
                    history.extend(doc[field])
                elif isinstance(doc[field], str):
                    # Parse string format if needed
                    # This would need custom parsing logic based on your data format
                    history.append({"記録": doc[field]})
        
        return history
    
    async def migrate_table(self, table_name: str, mongo_collection_name: str = None) -> Dict[str, Any]:
        """Migrate a single table from Airtable to MongoDB."""
        if not mongo_collection_name:
            mongo_collection_name = table_name
        
        migration_result = {
            "table_name": table_name,
            "mongo_collection": mongo_collection_name,
            "success": False,
            "records_migrated": 0,
            "errors": []
        }
        
        try:
            # Get all records from Airtable
            airtable_records = self.airtable_client.get_all_records(table_name)
            
            if not airtable_records:
                migration_result["errors"].append("No records found in Airtable table")
                return migration_result
            
            # Get MongoDB collection
            collection = await self.mongo_client.get_collection(mongo_collection_name)
            
            # Transform and insert records
            mongo_documents = []
            for record in airtable_records:
                try:
                    transformed_doc = self._transform_airtable_record(record, table_name)
                    mongo_documents.append(transformed_doc)
                except Exception as e:
                    migration_result["errors"].append(f"Error transforming record {record.get('id')}: {e}")
            
            # Insert into MongoDB
            if mongo_documents:
                result = await collection.insert_many(mongo_documents)
                migration_result["records_migrated"] = len(result.inserted_ids)
                migration_result["success"] = True
            
            logger.info(f"Successfully migrated {migration_result['records_migrated']} records from {table_name}")
            
        except Exception as e:
            error_msg = f"Error migrating table {table_name}: {e}"
            logger.error(error_msg)
            migration_result["errors"].append(error_msg)
        
        return migration_result
    
    async def migrate_all_tables(self) -> Dict[str, Any]:
        """Migrate all tables from Airtable to MongoDB."""
        overall_result = {
            "migration_started": datetime.now().isoformat(),
            "tables_migrated": 0,
            "total_records": 0,
            "table_results": [],
            "errors": []
        }
        
        try:
            # Get list of tables
            tables = self.airtable_client.list_tables()
            
            if not tables:
                overall_result["errors"].append("No tables found in Airtable base")
                return overall_result
            
            # Define table mapping (Airtable table name -> MongoDB collection name)
            table_mapping = {
                "daily_schedules": "daily_schedules",
                "圃場管理": "field_management",
                "作物マスター": "crop_master",
                "農薬マスター": "pesticide_master",
                "作業履歴": "work_history",
                "作業者マスター": "worker_master",
                "天候データ": "weather_data",
                "スケジュール管理": "schedule_management"
            }
            
            # Migrate each table
            for table_name in tables:
                mongo_collection = table_mapping.get(table_name, table_name)
                result = await self.migrate_table(table_name, mongo_collection)
                
                overall_result["table_results"].append(result)
                if result["success"]:
                    overall_result["tables_migrated"] += 1
                    overall_result["total_records"] += result["records_migrated"]
                
                overall_result["errors"].extend(result["errors"])
        
        except Exception as e:
            error_msg = f"Error in overall migration: {e}"
            logger.error(error_msg)
            overall_result["errors"].append(error_msg)
        
        overall_result["migration_completed"] = datetime.now().isoformat()
        return overall_result
    
    def get_migration_summary(self) -> Dict[str, Any]:
        """Get a summary of the migration process."""
        return {
            "migration_log": self.migration_log,
            "timestamp": datetime.now().isoformat()
        }