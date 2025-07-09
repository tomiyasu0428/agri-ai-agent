"""
Optimized message handler for LINE Bot.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from dataclasses import dataclass

from linebot import LineBotApi
from linebot.exceptions import LineBotApiError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    FollowEvent, UnfollowEvent, JoinEvent, LeaveEvent
)

from ..core.agent import AgentManager, OptimizedAgentManager
from ..core.agent_pool import get_agent_pool
from ..exceptions import LINEBotError, ValidationError
from ..utils.error_handling import LINEBotErrorHandler, error_handler
from ..utils.config import get_settings
from .utils import (
    format_agent_response, create_welcome_message, create_error_message,
    parse_command, clean_message, is_work_report
)

logger = logging.getLogger(__name__)


@dataclass
class MessageProcessingStats:
    """メッセージ処理統計"""
    total_messages: int = 0
    successful_messages: int = 0
    failed_messages: int = 0
    total_processing_time: float = 0.0
    average_processing_time: float = 0.0
    work_reports_processed: int = 0
    commands_processed: int = 0


class OptimizedLineMessageHandler:
    """最適化されたLINE Bot メッセージハンドラー"""
    
    def __init__(self, agent_manager: Union[AgentManager, OptimizedAgentManager], line_bot_api: LineBotApi):
        self.agent_manager = agent_manager
        self.line_bot_api = line_bot_api
        self.settings = get_settings()
        
        # セッション管理
        self.user_sessions: Dict[str, Dict[str, Any]] = {}
        
        # 統計情報
        self.stats = MessageProcessingStats()
        
        # メッセージキュー（負荷分散用）
        self.message_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self.processing_tasks: List[asyncio.Task] = []
        
        # レート制限
        self.rate_limiter: Dict[str, List[datetime]] = {}
        self.rate_limit_window = 60  # 1分間
        self.rate_limit_count = 30   # 30メッセージ/分
        
        # キャッシュ
        self.response_cache: Dict[str, tuple] = {}  # (response, timestamp)
        self.cache_ttl = 300  # 5分
    
    async def initialize(self):
        """ハンドラーを初期化"""
        logger.info("Initializing optimized LINE message handler...")
        
        # バックグラウンドタスクを開始
        for i in range(3):  # 3つの並列処理タスク
            task = asyncio.create_task(self._process_message_queue())
            self.processing_tasks.append(task)
        
        logger.info("LINE message handler initialized")
    
    async def shutdown(self):
        """ハンドラーをシャットダウン"""
        logger.info("Shutting down LINE message handler...")
        
        # 処理タスクを停止
        for task in self.processing_tasks:
            task.cancel()
        
        # 残っているタスクを待機
        if self.processing_tasks:
            await asyncio.gather(*self.processing_tasks, return_exceptions=True)
        
        logger.info("LINE message handler shutdown complete")
    
    async def handle_text_message(self, event: MessageEvent):
        """テキストメッセージをハンドル（キューに追加）"""
        try:
            # メッセージをキューに追加
            message_data = {
                "type": "text_message",
                "event": event,
                "timestamp": datetime.now(),
                "user_id": event.source.user_id,
                "message_text": event.message.text
            }
            
            await self.message_queue.put(message_data)
            logger.debug(f"Message queued from {event.source.user_id}")
            
        except asyncio.QueueFull:
            logger.error("Message queue is full, dropping message")
            await self._send_error_message(event.reply_token)
        except Exception as e:
            logger.error(f"Error queueing message: {e}")
            await self._send_error_message(event.reply_token)
    
    async def _process_message_queue(self):
        """メッセージキューを処理"""
        while True:
            try:
                # メッセージをキューから取得
                message_data = await self.message_queue.get()
                
                # メッセージを処理
                await self._process_text_message(message_data)
                
                # タスク完了を通知
                self.message_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing message queue: {e}")
                await asyncio.sleep(1)  # エラー時は少し待機
    
    @LINEBotErrorHandler.handle_message_error(logger)
    async def _process_text_message(self, message_data: Dict[str, Any]):
        """テキストメッセージを実際に処理"""
        start_time = time.time()
        self.stats.total_messages += 1
        
        try:
            event = message_data["event"]
            user_id = message_data["user_id"]
            message_text = message_data["message_text"]
            
            logger.info(f"📝 Processing message from {user_id}: {message_text[:50]}...")
            
            # レート制限チェック
            if not self._check_rate_limit(user_id):
                await self._send_rate_limit_message(event.reply_token)
                return
            
            # メッセージを清浄化
            cleaned_message = clean_message(message_text)
            
            # バリデーション
            if not self._validate_message(cleaned_message):
                await self._send_validation_error(event.reply_token)
                return
            
            # コマンドチェック
            command = parse_command(cleaned_message)
            if command:
                await self._handle_command(event, user_id, command)
                self.stats.commands_processed += 1
                return
            
            # セッション更新
            self._update_user_session(user_id, cleaned_message)
            
            # キャッシュチェック
            cached_response = self._get_cached_response(user_id, cleaned_message)
            if cached_response:
                await self._send_message(event.reply_token, cached_response)
                logger.debug(f"Cache hit for user {user_id}")
                return
            
            # AI処理
            response = await self._process_with_agent(user_id, cleaned_message)
            
            # 作業報告の場合は統計を更新
            if is_work_report(cleaned_message):
                self.stats.work_reports_processed += 1
            
            # レスポンスをフォーマット
            formatted_response = format_agent_response(response)
            
            # キャッシュに保存
            self._cache_response(user_id, cleaned_message, formatted_response)
            
            # レスポンスを送信
            await self._send_message(event.reply_token, formatted_response)
            
            # 統計更新
            self.stats.successful_messages += 1
            processing_time = time.time() - start_time
            self.stats.total_processing_time += processing_time
            self.stats.average_processing_time = (
                self.stats.total_processing_time / self.stats.successful_messages
            )
            
            logger.info(f"✅ Message processed for {user_id} in {processing_time:.2f}s")
            
        except Exception as e:
            self.stats.failed_messages += 1
            logger.error(f"❌ Error processing text message: {e}")
            
            if hasattr(message_data, 'event'):
                await self._send_error_message(message_data['event'].reply_token)
    
    def _check_rate_limit(self, user_id: str) -> bool:
        """レート制限をチェック"""
        now = datetime.now()
        
        # ユーザーのリクエスト履歴を取得
        if user_id not in self.rate_limiter:
            self.rate_limiter[user_id] = []
        
        user_requests = self.rate_limiter[user_id]
        
        # 古いリクエストを削除
        cutoff_time = now - timedelta(seconds=self.rate_limit_window)
        user_requests[:] = [req_time for req_time in user_requests if req_time > cutoff_time]
        
        # レート制限チェック
        if len(user_requests) >= self.rate_limit_count:
            logger.warning(f"Rate limit exceeded for user {user_id}")
            return False
        
        # 新しいリクエストを記録
        user_requests.append(now)
        return True
    
    def _validate_message(self, message: str) -> bool:
        """メッセージを検証"""
        if not message or not message.strip():
            return False
        
        if len(message) > self.settings.max_message_length:
            return False
        
        # 禁止語句チェック（必要に応じて実装）
        # prohibited_words = ["spam", "advertisement"]
        # if any(word in message.lower() for word in prohibited_words):
        #     return False
        
        return True
    
    def _get_cached_response(self, user_id: str, message: str) -> Optional[str]:
        """キャッシュされたレスポンスを取得"""
        cache_key = f"{user_id}:{hash(message)}"
        
        if cache_key in self.response_cache:
            response, timestamp = self.response_cache[cache_key]
            
            # TTL チェック
            if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                return response
            else:
                # 期限切れなので削除
                del self.response_cache[cache_key]
        
        return None
    
    def _cache_response(self, user_id: str, message: str, response: str):
        """レスポンスをキャッシュ"""
        cache_key = f"{user_id}:{hash(message)}"
        self.response_cache[cache_key] = (response, datetime.now())
        
        # キャッシュサイズ制限（簡単な実装）
        if len(self.response_cache) > 1000:
            # 最も古いエントリを削除
            oldest_key = min(self.response_cache.keys(), 
                           key=lambda k: self.response_cache[k][1])
            del self.response_cache[oldest_key]
    
    async def _handle_command(self, event: MessageEvent, user_id: str, command: str):
        """特殊コマンドを処理"""
        try:
            if command == "help":
                from .utils import create_help_message
                help_message = create_help_message()
                await self._send_message(event.reply_token, help_message)
            
            elif command == "reset":
                # メモリをリセット
                self.agent_manager.clear_user_memory(user_id)
                # セッションもリセット
                self._cleanup_user_session(user_id)
                await self._send_message(event.reply_token, "会話履歴をリセットしました。")
            
            elif command == "status":
                # ユーザー統計を表示
                session = self.user_sessions.get(user_id, {})
                status_info = f"""📊 ユーザー状況:
メッセージ数: {session.get('message_count', 0)}
最終活動: {session.get('last_activity', 'N/A')}
セッション開始: {session.get('first_interaction', 'N/A')}"""
                await self._send_message(event.reply_token, status_info)
            
            else:
                await self._send_message(event.reply_token, "不明なコマンドです。")
                
        except Exception as e:
            logger.error(f"Error handling command {command}: {e}")
            await self._send_error_message(event.reply_token)
    
    async def _send_rate_limit_message(self, reply_token: str):
        """レート制限メッセージを送信"""
        message = "メッセージの送信が多すぎます。しばらく待ってから再度お試しください。"
        await self._send_message(reply_token, message)
    
    async def _send_validation_error(self, reply_token: str):
        """バリデーションエラーメッセージを送信"""
        message = "メッセージの形式が正しくありません。もう一度お試しください。"
        await self._send_message(reply_token, message)
    
    async def handle_follow_event(self, event: FollowEvent):
        """Handle follow events (user adds bot as friend)."""
        try:
            user_id = event.source.user_id
            
            # Get user profile
            try:
                profile = self.line_bot_api.get_profile(user_id)
                user_name = profile.display_name
            except LineBotApiError:
                user_name = "ユーザー"
            
            logger.info(f"👤 New follow from {user_id} ({user_name})")
            
            # Initialize user session
            self._initialize_user_session(user_id, user_name)
            
            # Send welcome message
            welcome_message = create_welcome_message(user_name)
            await self._send_message(event.reply_token, welcome_message)
            
        except Exception as e:
            logger.error(f"❌ Error handling follow event: {e}")
            await self._send_error_message(event.reply_token)
    
    async def handle_unfollow_event(self, event: UnfollowEvent):
        """Handle unfollow events (user removes bot)."""
        try:
            user_id = event.source.user_id
            
            logger.info(f"👋 User unfollowed: {user_id}")
            
            # Clean up user session
            self._cleanup_user_session(user_id)
            
            # Remove agent for user
            self.agent_manager.remove_agent(user_id)
            
        except Exception as e:
            logger.error(f"❌ Error handling unfollow event: {e}")
    
    async def handle_join_event(self, event: JoinEvent):
        """Handle join events (bot added to group)."""
        try:
            group_id = event.source.group_id if hasattr(event.source, 'group_id') else None
            room_id = event.source.room_id if hasattr(event.source, 'room_id') else None
            
            logger.info(f"🏢 Bot joined group/room: {group_id or room_id}")
            
            # Send group welcome message
            welcome_message = """こんにちは！農業AIアシスタントです🌾

グループでご利用いただきありがとうございます。

主な機能：
• 今日の作業確認
• 作業報告の記録
• 圃場情報の確認
• 農薬・資材の推奨

何かご質問がありましたら、お気軽にお声がけください！"""
            
            await self._send_message(event.reply_token, welcome_message)
            
        except Exception as e:
            logger.error(f"❌ Error handling join event: {e}")
            await self._send_error_message(event.reply_token)
    
    async def handle_leave_event(self, event: LeaveEvent):
        """Handle leave events (bot removed from group)."""
        try:
            group_id = event.source.group_id if hasattr(event.source, 'group_id') else None
            room_id = event.source.room_id if hasattr(event.source, 'room_id') else None
            
            logger.info(f"👋 Bot left group/room: {group_id or room_id}")
            
            # Clean up group sessions if needed
            # For now, just log the event
            
        except Exception as e:
            logger.error(f"❌ Error handling leave event: {e}")
    
    async def _process_with_agent(self, user_id: str, message: str) -> str:
        """Process message with AI agent."""
        try:
            # Get response from agent
            response = await self.agent_manager.process_user_message(user_id, message)
            
            # Update user session with response
            self._update_user_session(user_id, None, response)
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error processing with agent: {e}")
            return "申し訳ございません。処理中にエラーが発生しました。しばらくしてからもう一度お試しください。"
    
    async def _send_message(self, reply_token: str, message: str):
        """Send message to LINE."""
        try:
            # Split long messages if needed
            messages = self._split_long_message(message)
            
            # Send messages
            for msg in messages:
                self.line_bot_api.reply_message(
                    reply_token,
                    TextSendMessage(text=msg)
                )
                
                # Small delay between messages
                if len(messages) > 1:
                    await asyncio.sleep(0.5)
                    
        except LineBotApiError as e:
            logger.error(f"❌ LINE API error: {e}")
            raise
    
    async def _send_error_message(self, reply_token: str):
        """Send error message to LINE."""
        try:
            error_message = create_error_message()
            await self._send_message(reply_token, error_message)
        except Exception as e:
            logger.error(f"❌ Failed to send error message: {e}")
    
    def _split_long_message(self, message: str, max_length: int = 2000) -> list:
        """Split long messages into chunks."""
        if len(message) <= max_length:
            return [message]
        
        chunks = []
        current_chunk = ""
        
        for line in message.split('\n'):
            if len(current_chunk) + len(line) + 1 <= max_length:
                current_chunk += line + '\n'
            else:
                if current_chunk:
                    chunks.append(current_chunk.rstrip())
                current_chunk = line + '\n'
        
        if current_chunk:
            chunks.append(current_chunk.rstrip())
        
        return chunks
    
    def _initialize_user_session(self, user_id: str, user_name: str):
        """Initialize user session."""
        self.user_sessions[user_id] = {
            "user_name": user_name,
            "first_interaction": datetime.now(),
            "last_activity": datetime.now(),
            "message_count": 0
        }
    
    def _update_user_session(self, user_id: str, message: Optional[str] = None, response: Optional[str] = None):
        """Update user session."""
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {
                "user_name": "ユーザー",
                "first_interaction": datetime.now(),
                "last_activity": datetime.now(),
                "message_count": 0
            }
        
        session = self.user_sessions[user_id]
        session["last_activity"] = datetime.now()
        
        if message:
            session["message_count"] += 1
            session["last_message"] = message
        
        if response:
            session["last_response"] = response
    
    def _cleanup_user_session(self, user_id: str):
        """Clean up user session."""
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
    
    def get_user_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get all user sessions."""
        return self.user_sessions.copy()
    
    def get_active_users_count(self) -> int:
        """Get count of active users."""
        return len(self.user_sessions)
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """処理統計を取得"""
        return {
            "total_messages": self.stats.total_messages,
            "successful_messages": self.stats.successful_messages,
            "failed_messages": self.stats.failed_messages,
            "success_rate": (
                self.stats.successful_messages / self.stats.total_messages 
                if self.stats.total_messages > 0 else 0
            ),
            "average_processing_time": self.stats.average_processing_time,
            "total_processing_time": self.stats.total_processing_time,
            "work_reports_processed": self.stats.work_reports_processed,
            "commands_processed": self.stats.commands_processed,
            "cache_size": len(self.response_cache),
            "queue_size": self.message_queue.qsize(),
            "active_users": len(self.user_sessions)
        }
    
    def get_user_stats(self, user_id: str) -> Optional[Dict[str, Any]]:
        """ユーザー統計を取得"""
        if user_id not in self.user_sessions:
            return None
        
        session = self.user_sessions[user_id]
        return {
            "user_id": user_id,
            "user_name": session.get("user_name", "不明"),
            "first_interaction": session.get("first_interaction"),
            "last_activity": session.get("last_activity"),
            "message_count": session.get("message_count", 0),
            "last_message": session.get("last_message", ""),
            "last_response": session.get("last_response", "")
        }
    
    def clear_cache(self):
        """キャッシュをクリア"""
        self.response_cache.clear()
        logger.info("Response cache cleared")
    
    def cleanup_expired_cache(self):
        """期限切れキャッシュをクリーンアップ"""
        now = datetime.now()
        expired_keys = []
        
        for key, (response, timestamp) in self.response_cache.items():
            if now - timestamp > timedelta(seconds=self.cache_ttl):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.response_cache[key]
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")


# 後方互換性のために元のクラスも保持
class LineMessageHandler(OptimizedLineMessageHandler):
    """LINE Bot メッセージハンドラー（後方互換性）"""
    
    def __init__(self, agent_manager: AgentManager, line_bot_api: LineBotApi):
        super().__init__(agent_manager, line_bot_api)
        logger.info("Using legacy LineMessageHandler")