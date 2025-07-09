"""
最適化されたAgriDatabaseクラス
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from .database_pool import DatabasePool
from ..exceptions import DatabaseQueryError
from ..utils.error_handling import DatabaseErrorHandler

logger = logging.getLogger(__name__)


class OptimizedAgriDatabase:
    """最適化されたAgriDatabaseクラス"""
    
    def __init__(self, db_pool: DatabasePool):
        self.db_pool = db_pool
        
        # コレクション名の定数
        self.COLLECTIONS = {
            "tasks": "作業計画",
            "fields": "圃場データ",
            "planting_plans": "作付計画",
            "materials": "資材データ",
            "material_usage": "資材使用記録",
            "crops": "作物データ",
            "work_records": "作業記録"
        }
    
    @DatabaseErrorHandler.handle_query_error(logger)
    async def get_today_tasks(self, worker_id: str, date: str) -> List[Dict[str, Any]]:
        """今日のタスクを取得（最適化版）"""
        try:
            # 集約パイプラインでJOIN操作を一度に実行
            pipeline = [
                {
                    "$match": {
                        "担当者": worker_id,
                        "予定日": date,
                        "ステータス": {"$ne": "✅ 完了"}
                    }
                },
                {
                    "$lookup": {
                        "from": "作付計画",
                        "localField": "関連する作付計画",
                        "foreignField": "作付計画ID",
                        "as": "planting_info"
                    }
                },
                {
                    "$lookup": {
                        "from": "圃場データ",
                        "localField": "planting_info.圃場",
                        "foreignField": "圃場ID",
                        "as": "field_info"
                    }
                },
                {
                    "$addFields": {
                        "圃場名 (from 圃場データ) (from 関連する作付計画)": {
                            "$arrayElemAt": ["$field_info.圃場名", 0]
                        },
                        "作物名": {
                            "$arrayElemAt": ["$planting_info.作物", 0]
                        }
                    }
                },
                {
                    "$sort": {"予定日": 1, "作業計画ID": 1}
                }
            ]
            
            tasks = await self.db_pool.aggregate_cached(
                self.COLLECTIONS["tasks"],
                pipeline,
                use_cache=True
            )
            
            logger.info(f"Retrieved {len(tasks)} tasks for worker {worker_id} on {date}")
            return tasks
            
        except Exception as e:
            logger.error(f"Error retrieving today's tasks: {e}")
            raise DatabaseQueryError(
                f"今日のタスク取得中にエラーが発生しました: {str(e)}",
                context={"worker_id": worker_id, "date": date}
            )
    
    @DatabaseErrorHandler.handle_query_error(logger)
    async def get_field_status(self, field_name: str) -> Optional[Dict[str, Any]]:
        """圃場ステータスを取得（最適化版）"""
        try:
            # 圃場データと関連する作付計画を一度に取得
            pipeline = [
                {
                    "$match": {"圃場名": field_name}
                },
                {
                    "$lookup": {
                        "from": "作付計画",
                        "localField": "圃場ID",
                        "foreignField": "圃場",
                        "as": "planting_plans"
                    }
                },
                {
                    "$lookup": {
                        "from": "資材使用記録",
                        "let": {"field_id": "$圃場ID"},
                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {"$eq": ["$圃場", "$$field_id"]},
                                    "使用日": {
                                        "$gte": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                                    }
                                }
                            },
                            {"$sort": {"使用日": -1}},
                            {"$limit": 5}
                        ],
                        "as": "recent_material_usage"
                    }
                }
            ]
            
            results = await self.db_pool.aggregate_cached(
                self.COLLECTIONS["fields"],
                pipeline,
                use_cache=True
            )
            
            if not results:
                logger.warning(f"Field not found: {field_name}")
                return None
            
            field_data = results[0]
            logger.info(f"Retrieved field status for: {field_name}")
            return field_data
            
        except Exception as e:
            logger.error(f"Error retrieving field status: {e}")
            raise DatabaseQueryError(
                f"圃場ステータス取得中にエラーが発生しました: {str(e)}",
                context={"field_name": field_name}
            )
    
    @DatabaseErrorHandler.handle_query_error(logger)
    async def get_pesticide_recommendations(
        self, 
        field_name: str, 
        crop: str
    ) -> List[Dict[str, Any]]:
        """農薬推奨を取得（最適化版）"""
        try:
            # 作物と圃場に基づいて資材を検索
            pipeline = [
                {
                    "$match": {
                        "$or": [
                            {"対象作物": {"$regex": crop, "$options": "i"}},
                            {"資材分類": {"$in": ["農薬", "防除剤", "殺虫剤", "殺菌剤"]}}
                        ]
                    }
                },
                {
                    "$lookup": {
                        "from": "資材使用記録",
                        "let": {"material_name": "$資材名"},
                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {"$eq": ["$資材名", "$$material_name"]},
                                    "使用日": {
                                        "$gte": (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
                                    }
                                }
                            }
                        ],
                        "as": "usage_history"
                    }
                },
                {
                    "$addFields": {
                        "recent_usage_count": {"$size": "$usage_history"},
                        "last_used": {
                            "$max": "$usage_history.使用日"
                        }
                    }
                },
                {
                    "$sort": {
                        "recent_usage_count": -1,
                        "資材名": 1
                    }
                },
                {
                    "$limit": 10
                }
            ]
            
            recommendations = await self.db_pool.aggregate_cached(
                self.COLLECTIONS["materials"],
                pipeline,
                use_cache=True
            )
            
            logger.info(f"Retrieved {len(recommendations)} pesticide recommendations for {crop} in {field_name}")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error retrieving pesticide recommendations: {e}")
            raise DatabaseQueryError(
                f"農薬推奨取得中にエラーが発生しました: {str(e)}",
                context={"field_name": field_name, "crop": crop}
            )
    
    @DatabaseErrorHandler.handle_query_error(logger)
    async def get_recent_material_usage(
        self, 
        field_name: str, 
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """最近の資材使用履歴を取得（最適化版）"""
        try:
            # 圃場IDを取得
            field_data = await self.db_pool.find_one_cached(
                self.COLLECTIONS["fields"],
                {"圃場名": field_name},
                {"圃場ID": 1}
            )
            
            if not field_data:
                return []
            
            field_id = field_data.get("圃場ID")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            # 資材使用記録を取得
            pipeline = [
                {
                    "$match": {
                        "圃場": field_id,
                        "使用日": {"$gte": start_date}
                    }
                },
                {
                    "$lookup": {
                        "from": "資材データ",
                        "localField": "資材名",
                        "foreignField": "資材名",
                        "as": "material_info"
                    }
                },
                {
                    "$addFields": {
                        "資材分類": {
                            "$arrayElemAt": ["$material_info.資材分類", 0]
                        }
                    }
                },
                {
                    "$sort": {"使用日": -1}
                }
            ]
            
            usage_records = await self.db_pool.aggregate_cached(
                self.COLLECTIONS["material_usage"],
                pipeline,
                use_cache=True
            )
            
            logger.info(f"Retrieved {len(usage_records)} material usage records for {field_name}")
            return usage_records
            
        except Exception as e:
            logger.error(f"Error retrieving material usage: {e}")
            raise DatabaseQueryError(
                f"資材使用履歴取得中にエラーが発生しました: {str(e)}",
                context={"field_name": field_name, "days": days}
            )
    
    @DatabaseErrorHandler.handle_query_error(logger)
    async def complete_task(
        self, 
        task_id: str, 
        completion_data: Dict[str, Any]
    ) -> bool:
        """タスクを完了（最適化版）"""
        try:
            update_data = {
                "$set": {
                    "ステータス": "✅ 完了",
                    "完了日": datetime.now().strftime("%Y-%m-%d"),
                    **completion_data
                }
            }
            
            success = await self.db_pool.update_one(
                self.COLLECTIONS["tasks"],
                {"作業計画ID": task_id},
                update_data
            )
            
            if success:
                logger.info(f"Task completed successfully: {task_id}")
            else:
                logger.warning(f"Task not found or not updated: {task_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error completing task: {e}")
            raise DatabaseQueryError(
                f"タスク完了処理中にエラーが発生しました: {str(e)}",
                context={"task_id": task_id, "completion_data": completion_data}
            )
    
    @DatabaseErrorHandler.handle_query_error(logger)
    async def schedule_next_task(
        self, 
        field_name: str, 
        task_type: str, 
        days_offset: int
    ) -> str:
        """次回タスクをスケジュール（最適化版）"""
        try:
            # 圃場データを取得
            field_data = await self.db_pool.find_one_cached(
                self.COLLECTIONS["fields"],
                {"圃場名": field_name},
                {"圃場ID": 1}
            )
            
            if not field_data:
                raise DatabaseQueryError(f"圃場が見つかりません: {field_name}")
            
            # 次回実施日を計算
            next_date = (datetime.now() + timedelta(days=days_offset)).strftime("%Y-%m-%d")
            
            # 新しいタスクを作成
            new_task = {
                "作業計画ID": f"AUTO_{field_name}_{task_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "タスク名": f"{task_type}({days_offset}日後)",
                "圃場": field_data["圃場ID"],
                "予定日": next_date,
                "ステータス": "🗓️ 予定",
                "作成日": datetime.now().strftime("%Y-%m-%d"),
                "自動生成": True
            }
            
            task_id = await self.db_pool.insert_one(
                self.COLLECTIONS["tasks"],
                new_task
            )
            
            logger.info(f"Next task scheduled: {task_id} for {field_name} on {next_date}")
            return task_id
            
        except Exception as e:
            logger.error(f"Error scheduling next task: {e}")
            raise DatabaseQueryError(
                f"次回タスクスケジュール中にエラーが発生しました: {str(e)}",
                context={"field_name": field_name, "task_type": task_type, "days_offset": days_offset}
            )
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """データベース統計を取得"""
        try:
            stats = {}
            
            for name, collection_name in self.COLLECTIONS.items():
                try:
                    collection = await self.db_pool.get_collection(collection_name)
                    count = await collection.count_documents({})
                    stats[name] = count
                except Exception as e:
                    logger.warning(f"Failed to get stats for {collection_name}: {e}")
                    stats[name] = -1
            
            # キャッシュ統計も追加
            stats["cache_stats"] = self.db_pool.get_cache_stats()
            
            return stats
            
        except Exception as e:
            logger.error(f"Error retrieving database stats: {e}")
            return {"error": str(e)}
    
    async def clear_cache(self):
        """キャッシュをクリア"""
        self.db_pool.clear_cache()
        logger.info("Database cache cleared")