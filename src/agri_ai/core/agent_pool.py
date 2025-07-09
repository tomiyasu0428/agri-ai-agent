"""
エージェントプールとライフサイクル管理
"""

import asyncio
import logging
from typing import Dict, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from weakref import WeakValueDictionary

from .optimized_database import OptimizedAgriDatabase
from .database_pool import get_database_pool
from ..exceptions import AgentProcessingError
from ..utils.error_handling import AgentErrorHandler
from ..utils.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class AgentStats:
    """エージェント統計情報"""
    created_at: datetime
    last_used: datetime
    message_count: int
    total_processing_time: float
    error_count: int


class AgentPool:
    """エージェントプールとライフサイクル管理"""
    
    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        
        # プール設定
        self.max_agents = self.settings.max_agents
        self.agent_ttl = timedelta(minutes=self.settings.agent_ttl_minutes)
        
        # エージェント管理
        self.agents: Dict[str, 'AgriAIAgent'] = {}
        self.agent_stats: Dict[str, AgentStats] = {}
        self.agent_locks: Dict[str, asyncio.Lock] = {}
        
        # バックグラウンドタスク
        self.cleanup_task: Optional[asyncio.Task] = None
        self.cleanup_interval = timedelta(minutes=5)
        
        # 統計
        self.total_agents_created = 0
        self.total_agents_removed = 0
        
        # データベースプール
        self.db_pool = None
        self.optimized_db = None
        
        # 弱参照でメモリリークを防止
        self.active_conversations: WeakValueDictionary = WeakValueDictionary()
    
    async def initialize(self):
        """プールを初期化"""
        logger.info("Initializing agent pool...")
        
        # データベースプールを初期化
        self.db_pool = await get_database_pool()
        self.optimized_db = OptimizedAgriDatabase(self.db_pool)
        
        # クリーンアップタスクを開始
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info(f"Agent pool initialized with max_agents={self.max_agents}, ttl={self.agent_ttl}")
    
    async def shutdown(self):
        """プールをシャットダウン"""
        logger.info("Shutting down agent pool...")
        
        # クリーンアップタスクを停止
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        # 全エージェントをクリーンアップ
        await self._cleanup_all_agents()
        
        logger.info("Agent pool shutdown complete")
    
    async def get_agent(self, user_id: str) -> 'AgriAIAgent':
        """ユーザー用エージェントを取得または作成"""
        # ユーザー固有のロックを取得
        if user_id not in self.agent_locks:
            self.agent_locks[user_id] = asyncio.Lock()
        
        async with self.agent_locks[user_id]:
            # 既存エージェントを確認
            if user_id in self.agents:
                agent = self.agents[user_id]
                stats = self.agent_stats[user_id]
                
                # TTL チェック
                if datetime.now() - stats.last_used < self.agent_ttl:
                    # エージェントが有効、統計を更新
                    stats.last_used = datetime.now()
                    logger.debug(f"Reusing existing agent for user {user_id}")
                    return agent
                else:
                    # TTL 期限切れ、エージェントを削除
                    logger.info(f"Agent TTL expired for user {user_id}, removing")
                    await self._remove_agent(user_id)
            
            # プールサイズをチェック
            if len(self.agents) >= self.max_agents:
                await self._cleanup_oldest_agent()
            
            # 新しいエージェントを作成
            agent = await self._create_agent(user_id)
            return agent
    
    async def _create_agent(self, user_id: str) -> 'AgriAIAgent':
        """新しいエージェントを作成"""
        try:
            from .agent import AgriAIAgent  # 循環インポートを避けるため遅延インポート
            
            # エージェントを作成
            agent = AgriAIAgent(self.optimized_db)
            
            # プールに追加
            self.agents[user_id] = agent
            
            # 統計を初期化
            now = datetime.now()
            self.agent_stats[user_id] = AgentStats(
                created_at=now,
                last_used=now,
                message_count=0,
                total_processing_time=0.0,
                error_count=0
            )
            
            self.total_agents_created += 1
            
            logger.info(f"Created new agent for user {user_id} (total: {len(self.agents)})")
            return agent
            
        except Exception as e:
            logger.error(f"Failed to create agent for user {user_id}: {e}")
            raise AgentProcessingError(
                f"エージェントの作成に失敗しました: {str(e)}",
                context={"user_id": user_id}
            )
    
    async def _remove_agent(self, user_id: str):
        """エージェントを削除"""
        if user_id in self.agents:
            try:
                agent = self.agents[user_id]
                
                # エージェントのクリーンアップ
                if hasattr(agent, 'clear_memory'):
                    agent.clear_memory()
                
                # プールから削除
                del self.agents[user_id]
                del self.agent_stats[user_id]
                
                # ロックも削除
                if user_id in self.agent_locks:
                    del self.agent_locks[user_id]
                
                self.total_agents_removed += 1
                
                logger.debug(f"Removed agent for user {user_id}")
                
            except Exception as e:
                logger.error(f"Error removing agent for user {user_id}: {e}")
    
    async def _cleanup_oldest_agent(self):
        """最も古いエージェントをクリーンアップ"""
        if not self.agents:
            return
        
        # 最も古いエージェントを見つける
        oldest_user = min(
            self.agent_stats.keys(),
            key=lambda u: self.agent_stats[u].last_used
        )
        
        logger.info(f"Removing oldest agent for user {oldest_user} to make space")
        await self._remove_agent(oldest_user)
    
    async def _cleanup_expired_agents(self):
        """期限切れエージェントをクリーンアップ"""
        now = datetime.now()
        expired_users = []
        
        for user_id, stats in self.agent_stats.items():
            if now - stats.last_used > self.agent_ttl:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            logger.info(f"Cleaning up expired agent for user {user_id}")
            await self._remove_agent(user_id)
        
        if expired_users:
            logger.info(f"Cleaned up {len(expired_users)} expired agents")
    
    async def _cleanup_all_agents(self):
        """全エージェントをクリーンアップ"""
        user_ids = list(self.agents.keys())
        for user_id in user_ids:
            await self._remove_agent(user_id)
    
    async def _cleanup_loop(self):
        """バックグラウンドクリーンアップループ"""
        try:
            while True:
                await asyncio.sleep(self.cleanup_interval.total_seconds())
                await self._cleanup_expired_agents()
        except asyncio.CancelledError:
            logger.info("Cleanup loop cancelled")
        except Exception as e:
            logger.error(f"Error in cleanup loop: {e}")
    
    def update_agent_stats(
        self, 
        user_id: str, 
        processing_time: float = 0.0, 
        error_occurred: bool = False
    ):
        """エージェント統計を更新"""
        if user_id in self.agent_stats:
            stats = self.agent_stats[user_id]
            stats.last_used = datetime.now()
            stats.message_count += 1
            stats.total_processing_time += processing_time
            
            if error_occurred:
                stats.error_count += 1
    
    def get_agent_info(self, user_id: str) -> Optional[Dict]:
        """エージェント情報を取得"""
        if user_id not in self.agents:
            return None
        
        stats = self.agent_stats[user_id]
        return {
            "user_id": user_id,
            "created_at": stats.created_at.isoformat(),
            "last_used": stats.last_used.isoformat(),
            "message_count": stats.message_count,
            "total_processing_time": stats.total_processing_time,
            "average_processing_time": (
                stats.total_processing_time / stats.message_count 
                if stats.message_count > 0 else 0
            ),
            "error_count": stats.error_count,
            "error_rate": (
                stats.error_count / stats.message_count 
                if stats.message_count > 0 else 0
            )
        }
    
    def get_pool_stats(self) -> Dict:
        """プール統計を取得"""
        now = datetime.now()
        active_agents = len(self.agents)
        
        # アクティブエージェントの統計
        if self.agent_stats:
            total_messages = sum(stats.message_count for stats in self.agent_stats.values())
            total_errors = sum(stats.error_count for stats in self.agent_stats.values())
            avg_processing_time = (
                sum(stats.total_processing_time for stats in self.agent_stats.values()) / 
                total_messages if total_messages > 0 else 0
            )
        else:
            total_messages = 0
            total_errors = 0
            avg_processing_time = 0
        
        return {
            "active_agents": active_agents,
            "max_agents": self.max_agents,
            "agent_ttl_minutes": self.agent_ttl.total_seconds() / 60,
            "total_agents_created": self.total_agents_created,
            "total_agents_removed": self.total_agents_removed,
            "total_messages_processed": total_messages,
            "total_errors": total_errors,
            "error_rate": total_errors / total_messages if total_messages > 0 else 0,
            "average_processing_time": avg_processing_time,
            "pool_utilization": active_agents / self.max_agents if self.max_agents > 0 else 0
        }
    
    def get_active_users(self) -> Set[str]:
        """アクティブユーザーIDのセットを取得"""
        return set(self.agents.keys())


# グローバルエージェントプールインスタンス
_agent_pool = None


async def get_agent_pool() -> AgentPool:
    """エージェントプールを取得"""
    global _agent_pool
    if _agent_pool is None:
        _agent_pool = AgentPool()
        await _agent_pool.initialize()
    return _agent_pool


async def shutdown_agent_pool():
    """エージェントプールをシャットダウン"""
    global _agent_pool
    if _agent_pool:
        await _agent_pool.shutdown()
        _agent_pool = None