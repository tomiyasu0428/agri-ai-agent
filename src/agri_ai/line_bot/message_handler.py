"""
Message handler for LINE Bot.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from linebot import LineBotApi
from linebot.exceptions import LineBotApiError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    FollowEvent, UnfollowEvent, JoinEvent, LeaveEvent
)

from ..core.agent import AgentManager
from .utils import format_agent_response, create_welcome_message, create_error_message

logger = logging.getLogger(__name__)


class LineMessageHandler:
    """Handler for LINE Bot messages and events."""
    
    def __init__(self, agent_manager: AgentManager, line_bot_api: LineBotApi):
        self.agent_manager = agent_manager
        self.line_bot_api = line_bot_api
        self.user_sessions: Dict[str, Dict[str, Any]] = {}
    
    async def handle_text_message(self, event: MessageEvent):
        """Handle text messages from users."""
        try:
            user_id = event.source.user_id
            message_text = event.message.text
            
            logger.info(f"📝 Message from {user_id}: {message_text}")
            
            # Update user session
            self._update_user_session(user_id, message_text)
            
            # Process message with AI agent
            response = await self._process_with_agent(user_id, message_text)
            
            # Format response for LINE
            formatted_response = format_agent_response(response)
            
            # Send response
            await self._send_message(event.reply_token, formatted_response)
            
            logger.info(f"✅ Response sent to {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error handling text message: {e}")
            await self._send_error_message(event.reply_token)
    
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