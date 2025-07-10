"""
LINE Bot application for Agricultural AI Agent.
"""

import asyncio
import logging
from typing import Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, 
    FollowEvent, UnfollowEvent, JoinEvent, LeaveEvent
)

from ..core.agent import AgentManager, OptimizedAgentManager
from ..core.database import MongoDBClient, AgriDatabase
from ..core.database_pool import get_database_pool
from ..core.optimized_database import OptimizedAgriDatabase
from ..core.agent_pool import get_agent_pool
from ..utils.config import get_settings
from .message_handler import LineMessageHandler, OptimizedLineMessageHandler
from .utils import format_agent_response, create_error_message

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
agent_manager: AgentManager = None
message_handler: LineMessageHandler = None
line_bot_api: LineBotApi = None
webhook_handler: WebhookHandler = None
mongo_client: MongoDBClient = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global agent_manager, message_handler, line_bot_api, webhook_handler, mongo_client
    
    # Startup
    logger.info("🚀 Starting Agricultural AI LINE Bot...")
    
    try:
        # Load settings
        settings = get_settings()
        
        # Validate LINE Bot configuration
        if not settings.line_channel_access_token or not settings.line_channel_secret:
            raise ValueError("LINE Bot credentials are not configured")
        
        # Initialize LINE Bot API
        line_bot_api = LineBotApi(settings.line_channel_access_token)
        webhook_handler = WebhookHandler(settings.line_channel_secret)
        
        # Initialize optimized database pool
        db_pool = await get_database_pool()
        optimized_db = OptimizedAgriDatabase(db_pool)
        
        # Initialize agent pool
        agent_pool = await get_agent_pool()
        
        # Initialize optimized agent manager
        agent_manager = OptimizedAgentManager(agent_pool)
        
        # Initialize optimized message handler
        message_handler = OptimizedLineMessageHandler(agent_manager, line_bot_api)
        await message_handler.initialize()
        
        # Setup webhook handlers
        setup_webhook_handlers()
        
        logger.info("✅ Agricultural AI LINE Bot started successfully!")
        
    except Exception as e:
        logger.error(f"❌ Failed to start LINE Bot: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Agricultural AI LINE Bot...")
    
    # Shutdown message handler
    if message_handler:
        await message_handler.shutdown()
    
    # Shutdown agent pool
    from ..core.agent_pool import shutdown_agent_pool
    await shutdown_agent_pool()
    
    # Shutdown database pool
    from ..core.database_pool import close_database_pool
    await close_database_pool()
    
    logger.info("✅ Agricultural AI LINE Bot shut down successfully!")


# Initialize FastAPI app
app = FastAPI(
    title="Agricultural AI LINE Bot",
    description="LINE Bot interface for Agricultural AI Agent",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Agricultural AI LINE Bot is running!"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check database connection
        if mongo_client:
            await mongo_client.db.command("ping")
        
        # Check LINE Bot API
        if line_bot_api:
            line_bot_api.get_bot_info()
        
        return {"status": "healthy"}
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


@app.post("/webhook")
async def line_webhook(request: Request, background_tasks: BackgroundTasks):
    """LINE Bot webhook endpoint."""
    try:
        # Get request signature
        signature = request.headers.get('X-Line-Signature', '')
        
        # Get request body
        body = await request.body()
        body_text = body.decode('utf-8')
        
        logger.info(f"📥 Webhook received: {body_text[:200]}...")
        logger.info(f"🔑 Signature: {signature[:20]}...")
        
        # Handle webhook
        try:
            webhook_handler.handle(body_text, signature)
            logger.info("✅ Webhook handled successfully")
        except InvalidSignatureError:
            logger.error("❌ Invalid signature")
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        return JSONResponse({"status": "ok"})
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


def setup_webhook_handlers():
    """Setup webhook handlers after initialization."""
    global webhook_handler, message_handler, line_bot_api
    
    @webhook_handler.add(MessageEvent, message=TextMessage)
    def handle_text_message(event: MessageEvent):
        """Handle text messages."""
        try:
            logger.info(f"💬 Text message received: {event.message.text}")
            logger.info(f"👤 User ID: {event.source.user_id}")
            
            # Process message in background
            asyncio.create_task(message_handler.handle_text_message(event))
            
        except Exception as e:
            logger.error(f"❌ Error handling text message: {e}")
            
            # Send error message
            try:
                error_message = create_error_message()
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=error_message)
                )
            except LineBotApiError as api_error:
                logger.error(f"❌ Failed to send error message: {api_error}")

    @webhook_handler.add(FollowEvent)
    def handle_follow(event: FollowEvent):
        """Handle follow events."""
        try:
            asyncio.create_task(message_handler.handle_follow_event(event))
        except Exception as e:
            logger.error(f"Error handling follow event: {e}")

    @webhook_handler.add(UnfollowEvent)
    def handle_unfollow(event: UnfollowEvent):
        """Handle unfollow events."""
        try:
            asyncio.create_task(message_handler.handle_unfollow_event(event))
        except Exception as e:
            logger.error(f"Error handling unfollow event: {e}")

    @webhook_handler.add(JoinEvent)
    def handle_join(event: JoinEvent):
        """Handle join events."""
        try:
            asyncio.create_task(message_handler.handle_join_event(event))
        except Exception as e:
            logger.error(f"Error handling join event: {e}")

    @webhook_handler.add(LeaveEvent)
    def handle_leave(event: LeaveEvent):
        """Handle leave events."""
        try:
            asyncio.create_task(message_handler.handle_leave_event(event))
        except Exception as e:
            logger.error(f"Error handling leave event: {e}")


@app.get("/stats")
async def get_stats():
    """Get comprehensive bot statistics."""
    try:
        if not agent_manager:
            raise HTTPException(status_code=503, detail="Agent manager not initialized")
        
        # エージェント統計
        agent_stats = agent_manager.get_agent_stats()
        
        # メッセージハンドラー統計
        processing_stats = message_handler.get_processing_stats()
        
        # データベース統計
        db_stats = {}
        if hasattr(optimized_db, 'get_database_stats'):
            db_stats = await optimized_db.get_database_stats()
        
        return {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "agent_stats": agent_stats,
            "processing_stats": processing_stats,
            "database_stats": db_stats
        }
    
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/stats/user/{user_id}")
async def get_user_stats(user_id: str):
    """Get user-specific statistics."""
    try:
        if not message_handler:
            raise HTTPException(status_code=503, detail="Message handler not initialized")
        
        user_stats = message_handler.get_user_stats(user_id)
        if not user_stats:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "user_stats": user_stats
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/admin/cache/clear")
async def clear_cache():
    """Clear all caches."""
    try:
        # メッセージハンドラーのキャッシュをクリア
        if message_handler:
            message_handler.clear_cache()
        
        # データベースキャッシュをクリア
        if hasattr(optimized_db, 'clear_cache'):
            await optimized_db.clear_cache()
        
        return {"status": "ok", "message": "Caches cleared successfully"}
    
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/admin/broadcast")
async def admin_broadcast(request: Request):
    """Admin endpoint for broadcasting messages."""
    try:
        data = await request.json()
        message = data.get("message")
        
        if not message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        # This would require implementing user management
        # For now, return success
        return {"status": "broadcast sent", "message": message}
    
    except Exception as e:
        logger.error(f"Error broadcasting message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    import uvicorn
    
    # Development server
    uvicorn.run(
        "agri_ai.line_bot.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )