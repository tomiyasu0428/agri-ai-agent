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
    
    def list_tables_via_meta_api(self) -> List[str]:
        """List all tables using Airtable Meta API."""
        try:
            import requests
            
            url = f"https://api.airtable.com/v0/meta/bases/{self.base_id}/tables"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            tables = [table["name"] for table in data.get("tables", [])]
            
            logger.info(f"Found {len(tables)} tables via Meta API: {tables}")
            return tables
            
        except Exception as e:
            logger.warning(f"Meta API failed: {e}, falling back to manual detection")
            return self.list_tables_manual()
    
    def list_tables_manual(self) -> List[str]:
        """Manually try common table names."""
        # Extended list based on screenshots and common patterns
        potential_table_names = [
            "圃場データ",
            "作物マスター", 
            "作付計画",
            "Crop Task Template",
            "作業タスク",
            "資材マスター",
            "資材使用ログ",
            "作業者マスター",
            "ナレッジベース",
            "収穫ログ",
            "日報ログ",
            "天候データ",
            "農薬マスター",
            "病害虫記録",
            "売上記録",
            "スケジュール",
            "在庫管理",
            "品質記録"
        ]
        
        existing_tables = []
        for table_name in potential_table_names:
            try:
                table = self.get_table(table_name)
                # Try to get schema to verify table exists
                table.all(max_records=1)
                existing_tables.append(table_name)
                logger.info(f"Found table: {table_name}")
            except Exception as e:
                logger.debug(f"Table '{table_name}' not found: {e}")
                continue
        
        return existing_tables
    
    def list_tables(self) -> List[str]:
        """List all tables in the base using the best available method."""
        try:
            # First try Meta API
            tables = self.list_tables_via_meta_api()
            if tables:
                return tables
            
            # Fallback to manual detection
            return self.list_tables_manual()
            
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
        if table_name == "圃場データ":
            mongo_doc = self._transform_field_data(mongo_doc)
        elif table_name == "作物マスター":
            mongo_doc = self._transform_crop_master(mongo_doc)
        elif table_name == "作付計画":
            mongo_doc = self._transform_planting_plan(mongo_doc)
        elif table_name == "Crop Task Template":
            mongo_doc = self._transform_crop_task_template(mongo_doc)
        elif table_name == "作業タスク":
            mongo_doc = self._transform_work_task(mongo_doc)
        elif table_name == "資材マスター":
            mongo_doc = self._transform_material_master(mongo_doc)
        elif table_name == "資材使用ログ":
            mongo_doc = self._transform_material_usage_log(mongo_doc)
        elif table_name == "作業者マスター":
            mongo_doc = self._transform_worker_master(mongo_doc)
        elif table_name == "ナレッジベース":
            mongo_doc = self._transform_knowledge_base(mongo_doc)
        elif table_name == "収穫ログ":
            mongo_doc = self._transform_harvest_log(mongo_doc)
        elif table_name == "日報ログ":
            mongo_doc = self._transform_daily_log(mongo_doc)
        else:
            # Generic transformation for unknown tables
            mongo_doc = self._transform_generic(mongo_doc)
        
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
        """Transform crop master record based on actual Airtable field names."""
        return {
            "airtable_id": doc.get("airtable_id"),
            "created_time": doc.get("created_time"),
            "table_source": doc.get("table_source"),
            "migrated_at": doc.get("migrated_at"),
            
            # Map actual Airtable field names to MongoDB document  
            "作物名": doc.get("作物名"),
            "分類": doc.get("分類"),
            "作付計画": doc.get("作付計画"),
            "Crop Task Template": doc.get("Crop Task Template")
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
    
    def _transform_field_data(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Transform field data record."""
        return {
            "airtable_id": doc.get("airtable_id"),
            "圃場ID": doc.get("圃場ID"),
            "エリア": doc.get("エリア"),
            "圃場名": doc.get("圃場名"),
            "面積(ha)": doc.get("面積(ha)"),
            "作付詳細": doc.get("作付詳細"),
            "大豆播種管理 2": doc.get("大豆播種管理 2"),
            "migrated_at": doc.get("migrated_at")
        }
    
    def _transform_planting_plan(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Transform planting plan record."""
        return {
            "airtable_id": doc.get("airtable_id"),
            "播種回次": doc.get("播種回次"),
            "品種名": doc.get("品種名"),
            "播種予定日": doc.get("播種予定日"),
            "播種実施日": doc.get("播種実施日"),
            "播種量/枚数": doc.get("播種量/枚数"),
            "定植予定日": doc.get("定植予定日"),
            "作つけ面積 (ha)": doc.get("作つけ面積 (ha)"),
            "元肥計画 (肥料名 kg/10a)": doc.get("元肥計画 (肥料名 kg/10a)"),
            "収穫予定": doc.get("収穫予定"),
            "圃場データ": doc.get("圃場データ"),
            "圃場名 (from 圃場データ)": doc.get("圃場名 (from 圃場データ)"),
            "作物マスター": doc.get("作物マスター"),
            "ID": doc.get("ID"),
            "資材使用量": doc.get("資材使用量"),
            "面積(ha) (from 圃場データ)": doc.get("面積(ha) (from 圃場データ)"),
            "作業タスク 3": doc.get("作業タスク 3"),
            "migrated_at": doc.get("migrated_at")
        }
    
    def _transform_crop_task_template(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Transform crop task template record."""
        return {
            "airtable_id": doc.get("airtable_id"),
            "タスク名": doc.get("タスク名"),
            "基準日": doc.get("基準日"),
            "オフセット(日)": doc.get("オフセット(日)"),
            "作物マスター": doc.get("作物マスター"),
            "migrated_at": doc.get("migrated_at")
        }
    
    def _transform_work_task(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Transform work task record."""
        return {
            "airtable_id": doc.get("airtable_id"),
            "タスク名": doc.get("タスク名"),
            "関連する作付計画": doc.get("関連する作付計画"),
            "ステータス": doc.get("ステータス"),
            "予定日": doc.get("予定日"),
            "メモ": doc.get("メモ"),
            "圃場名 (from 圃場データ) (from 関連する作付計画)": doc.get("圃場名 (from 圃場データ) (from 関連する作付計画)"),
            "migrated_at": doc.get("migrated_at")
        }
    
    def _transform_material_master(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Transform material master record."""
        return {
            "airtable_id": doc.get("airtable_id"),
            "資材名": doc.get("資材名"),
            "資材分類": doc.get("資材分類"),
            "migrated_at": doc.get("migrated_at")
        }
    
    def _transform_material_usage_log(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Transform material usage log record."""
        return {
            "airtable_id": doc.get("airtable_id"),
            "使用日": doc.get("使用日"),
            "資材名": doc.get("資材名"),
            "圃場名": doc.get("圃場名"),
            "作物名": doc.get("作物名"),
            "使用量": doc.get("使用量"),
            "単位": doc.get("単位"),
            "単価": doc.get("単価"),
            "使用金額": doc.get("使用金額"),
            "作業者": doc.get("作業者"),
            "作業内容": doc.get("作業内容"),
            "メモ": doc.get("メモ"),
            "migrated_at": doc.get("migrated_at")
        }
    
    def _transform_worker_master(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Transform worker master record."""
        return {
            "airtable_id": doc.get("airtable_id"),
            "作業者名": doc.get("作業者名"),
            "役割": doc.get("役割"),
            "所属": doc.get("所属"),
            "電話番号": doc.get("電話番号"),
            "メール": doc.get("メール"),
            "資格・免許": doc.get("資格・免許"),
            "メモ": doc.get("メモ"),
            "migrated_at": doc.get("migrated_at")
        }
    
    def _transform_knowledge_base(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Transform knowledge base record."""
        return {
            "airtable_id": doc.get("airtable_id"),
            "タイトル": doc.get("タイトル"),
            "カテゴリ": doc.get("カテゴリ"),
            "詳細": doc.get("詳細"),
            "登録日": doc.get("登録日"),
            "migrated_at": doc.get("migrated_at")
        }
    
    def _transform_harvest_log(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Transform harvest log record."""
        return {
            "airtable_id": doc.get("airtable_id"),
            "収穫日": doc.get("収穫日"),
            "作物名": doc.get("作物名"),
            "圃場名": doc.get("圃場名"),
            "サイズ": doc.get("サイズ"),
            "単価(円/個)": doc.get("単価(円/個)"),
            "売上": doc.get("売上"),
            "メモ": doc.get("メモ"),
            "migrated_at": doc.get("migrated_at")
        }
    
    def _transform_daily_log(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Transform daily log record based on actual Airtable field names."""
        # Actual field names in the 日報ログ table:
        # - 'Name' (Type: singleLineText)
        # - '報告日' (Type: date)
        # - '報告者' (Type: singleLineText)
        # - '報告内容' (Type: multilineText)
        
        return {
            "airtable_id": doc.get("airtable_id"),
            "created_time": doc.get("created_time"),
            "table_source": doc.get("table_source"),
            "migrated_at": doc.get("migrated_at"),
            
            # Map actual Airtable field names to MongoDB document
            "name": doc.get("Name"),
            "報告日": doc.get("報告日"),
            "報告者": doc.get("報告者"),
            "報告内容": doc.get("報告内容"),
            
            # Keep original field names for backward compatibility
            "日付": doc.get("報告日"),  # Map 報告日 to 日付 for compatibility
            "作業者": doc.get("報告者"),  # Map 報告者 to 作業者 for compatibility
            "作業内容": doc.get("報告内容"),  # Map 報告内容 to 作業内容 for compatibility
        }
    
    def _transform_generic(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Generic transformation for unknown table types."""
        # Simply preserve all fields as-is with minimal processing
        transformed = {
            "airtable_id": doc.get("airtable_id"),
            "created_time": doc.get("created_time"),
            "table_source": doc.get("table_source"),
            "migrated_at": doc.get("migrated_at")
        }
        
        # Add all other fields
        for key, value in doc.items():
            if key not in ["airtable_id", "created_time", "table_source", "migrated_at"]:
                transformed[key] = value
        
        return transformed
    
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