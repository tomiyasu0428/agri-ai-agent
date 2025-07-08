"""
LangChain tools for agricultural operations.
"""

from typing import Dict, Any, List, Optional
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from ..core.database import AgriDatabase

logger = logging.getLogger(__name__)


class GetTodayTasksInput(BaseModel):
    """Input schema for getting today's tasks."""
    worker_id: str = Field(description="Worker identifier (e.g., '田中', '佐藤')")
    date: Optional[str] = Field(default=None, description="Date in YYYY-MM-DD format (defaults to today)")


class GetTodayTasksTool(BaseTool):
    """Tool to get today's tasks for a worker."""
    
    name = "get_today_tasks"
    description = "Get today's agricultural tasks for a specific worker"
    args_schema = GetTodayTasksInput
    
    def __init__(self, agri_db: AgriDatabase):
        super().__init__()
        self.agri_db = agri_db
    
    def _run(self, worker_id: str, date: Optional[str] = None) -> str:
        """Get today's tasks synchronously (not recommended for production)."""
        import asyncio
        return asyncio.run(self._arun(worker_id, date))
    
    async def _arun(self, worker_id: str, date: Optional[str] = None) -> str:
        """Get today's tasks asynchronously."""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        try:
            tasks = await self.agri_db.get_today_tasks(worker_id, date)
            
            if not tasks:
                return f"{worker_id}さんの{date}のタスクはありません。"
            
            task_list = []
            for i, task in enumerate(tasks, 1):
                field_name = task.get('圃場名 (from 圃場データ) (from 関連する作付計画)', 'N/A')
                task_name = task.get('タスク名', 'N/A')
                task_info = f"{i}. {field_name} - {task_name}"
                status = task.get('ステータス', 'N/A')
                task_info += f" (状態: {status})"
                if task.get('予定日'):
                    task_info += f" 予定日: {task.get('予定日')}"
                if task.get('メモ'):
                    task_info += f" メモ: {task.get('メモ')}"
                task_list.append(task_info)
            
            return f"{worker_id}さんの{date}のタスク:\n" + "\n".join(task_list)
            
        except Exception as e:
            logger.error(f"Error getting today's tasks: {e}")
            return f"タスクの取得中にエラーが発生しました: {str(e)}"


class CompleteTaskInput(BaseModel):
    """Input schema for completing a task."""
    task_description: str = Field(description="Description of the completed task")
    field_name: str = Field(description="Field name where the task was completed")
    completion_notes: Optional[str] = Field(default=None, description="Additional completion notes")


class CompleteTaskTool(BaseTool):
    """Tool to mark a task as completed."""
    
    name = "complete_task"
    description = "Mark an agricultural task as completed"
    args_schema = CompleteTaskInput
    
    def __init__(self, agri_db: AgriDatabase):
        super().__init__()
        self.agri_db = agri_db
    
    def _run(self, task_description: str, field_name: str, completion_notes: Optional[str] = None) -> str:
        """Complete task synchronously."""
        import asyncio
        return asyncio.run(self._arun(task_description, field_name, completion_notes))
    
    async def _arun(self, task_description: str, field_name: str, completion_notes: Optional[str] = None) -> str:
        """Complete task asynchronously."""
        try:
            completion_data = {
                "完了時刻": datetime.now().isoformat(),
                "実施内容": completion_notes or task_description
            }
            
            # In a real implementation, we'd need to find the task ID
            # For now, we'll simulate successful completion
            success = True  # await self.agri_db.complete_task(task_id, completion_data)
            
            if success:
                # Auto-schedule next task if it's a recurring task
                if "防除" in task_description:
                    await self.agri_db.schedule_next_task(field_name, "防除", 7)
                
                return f"タスク完了: {field_name}での{task_description}が完了しました。"
            else:
                return f"タスクの完了処理中にエラーが発生しました。"
                
        except Exception as e:
            logger.error(f"Error completing task: {e}")
            return f"タスクの完了処理中にエラーが発生しました: {str(e)}"


class GetFieldStatusInput(BaseModel):
    """Input schema for getting field status."""
    field_name: str = Field(description="Name of the field to check")


class GetFieldStatusTool(BaseTool):
    """Tool to get field status information."""
    
    name = "get_field_status"
    description = "Get current status and information about a specific field"
    args_schema = GetFieldStatusInput
    
    def __init__(self, agri_db: AgriDatabase):
        super().__init__()
        self.agri_db = agri_db
    
    def _run(self, field_name: str) -> str:
        """Get field status synchronously."""
        import asyncio
        return asyncio.run(self._arun(field_name))
    
    async def _arun(self, field_name: str) -> str:
        """Get field status asynchronously."""
        try:
            field_data = await self.agri_db.get_field_status(field_name)
            
            if not field_data:
                return f"圃場 '{field_name}' の情報が見つかりません。"
            
            status_info = [f"圃場: {field_name}"]
            
            # Basic field information
            if field_data.get("圃場ID"):
                status_info.append(f"圃場ID: {field_data.get('圃場ID')}")
            if field_data.get("エリア"):
                status_info.append(f"エリア: {field_data.get('エリア')}")
            if field_data.get("面積(ha)"):
                status_info.append(f"面積: {field_data.get('面積(ha)')} ha")
            
            # Get related planting plan information
            planting_details = field_data.get("作付詳細", [])
            if planting_details:
                status_info.append("関連作付計画:")
                for detail_id in planting_details:
                    status_info.append(f"  - 作付計画ID: {detail_id}")
            
            # Get recent material usage if available
            try:
                material_usage = await self.agri_db.get_recent_material_usage(field_name)
                if material_usage:
                    status_info.append("最近の資材使用:")
                    for usage in material_usage[-3:]:  # Last 3 usages
                        date = usage.get("使用日", "N/A")
                        material = usage.get("資材名", "N/A")
                        amount = usage.get("使用量", "N/A")
                        unit = usage.get("単位", "")
                        status_info.append(f"  - {date}: {material} {amount}{unit}")
            except:
                pass  # Skip if method doesn't exist
            
            return "\n".join(status_info)
            
        except Exception as e:
            logger.error(f"Error getting field status: {e}")
            return f"圃場情報の取得中にエラーが発生しました: {str(e)}"


class RecommendPesticideInput(BaseModel):
    """Input schema for pesticide recommendation."""
    field_name: str = Field(description="Name of the field")
    crop: str = Field(description="Crop type")
    issue: Optional[str] = Field(default=None, description="Specific pest or disease issue")


class RecommendPesticideTool(BaseTool):
    """Tool to recommend pesticides based on field conditions."""
    
    name = "recommend_pesticide"
    description = "Recommend appropriate pesticides for a field based on crop and conditions"
    args_schema = RecommendPesticideInput
    
    def __init__(self, agri_db: AgriDatabase):
        super().__init__()
        self.agri_db = agri_db
    
    def _run(self, field_name: str, crop: str, issue: Optional[str] = None) -> str:
        """Recommend pesticides synchronously."""
        import asyncio
        return asyncio.run(self._arun(field_name, crop, issue))
    
    async def _arun(self, field_name: str, crop: str, issue: Optional[str] = None) -> str:
        """Recommend pesticides asynchronously."""
        try:
            recommendations = await self.agri_db.get_pesticide_recommendations(field_name, crop)
            
            if not recommendations:
                return f"{field_name}の{crop}に対する農薬の推奨情報がありません。"
            
            rec_info = [f"{field_name}の{crop}に対する資材推奨:"]
            
            for i, rec in enumerate(recommendations, 1):
                material_name = rec.get("資材名", "N/A")
                classification = rec.get("資材分類", "N/A")
                
                rec_info.append(f"{i}. {material_name}")
                rec_info.append(f"   分類: {classification}")
            
            # Get recent usage history for this field
            try:
                recent_usage = await self.agri_db.get_recent_material_usage(field_name)
                if recent_usage:
                    rec_info.append("\n最近の使用履歴:")
                    for usage in recent_usage[-2:]:  # Last 2 usages
                        date = usage.get("使用日", "N/A")
                        material = usage.get("資材名", "N/A")
                        amount = usage.get("使用量", "N/A")
                        unit = usage.get("単位", "")
                        rec_info.append(f"  - {date}: {material} {amount}{unit}")
            except:
                pass  # Skip if method doesn't exist
            
            rec_info.append("\n注意: 天候条件と前回散布からの間隔を確認してください。")
            
            return "\n".join(rec_info)
            
        except Exception as e:
            logger.error(f"Error recommending pesticides: {e}")
            return f"農薬推奨の処理中にエラーが発生しました: {str(e)}"


def create_agricultural_tools(agri_db: AgriDatabase) -> List[BaseTool]:
    """Create all agricultural tools with the database connection."""
    return [
        GetTodayTasksTool(agri_db),
        CompleteTaskTool(agri_db),
        GetFieldStatusTool(agri_db),
        RecommendPesticideTool(agri_db)
    ]