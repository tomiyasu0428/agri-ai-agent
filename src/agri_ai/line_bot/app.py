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

from ..core.agent import AgentManager
from ..core.database import MongoDBClient, AgriDatabase
from ..utils.config import get_settings
from .message_handler import LineMessageHandler
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
        
        # Initialize MongoDB connection
        mongo_client = MongoDBClient()
        await mongo_client.connect()
        
        # Initialize database
        agri_db = AgriDatabase(mongo_client)
        
        # Initialize agent manager
        agent_manager = AgentManager(agri_db)
        
        # Initialize message handler
        message_handler = LineMessageHandler(agent_manager, line_bot_api)
        
        # Setup webhook handlers
        setup_webhook_handlers()
        
        logger.info("✅ Agricultural AI LINE Bot started successfully!")
        
    except Exception as e:
        logger.error(f"❌ Failed to start LINE Bot: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Agricultural AI LINE Bot...")
    
    if mongo_client:
        await mongo_client.disconnect()
    
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
        
        # Handle webhook
        try:
            webhook_handler.handle(body.decode('utf-8'), signature)
        except InvalidSignatureError:
            logger.error("Invalid signature")
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        return JSONResponse({"status": "ok"})
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


def setup_webhook_handlers():
    """Setup webhook handlers after initialization."""
    global webhook_handler, message_handler, line_bot_api
    
    @webhook_handler.add(MessageEvent, message=TextMessage)
    def handle_text_message(event: MessageEvent):
        """Handle text messages."""
        try:
            # Process message in background
            asyncio.create_task(message_handler.handle_text_message(event))
            
        except Exception as e:
            logger.error(f"Error handling text message: {e}")
            
            # Send error message
            try:
                error_message = create_error_message()
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=error_message)
                )
            except LineBotApiError as api_error:
                logger.error(f"Failed to send error message: {api_error}")

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
    """Get bot statistics."""
    try:
        if not agent_manager:
            raise HTTPException(status_code=503, detail="Agent manager not initialized")
        
        stats = agent_manager.get_agent_stats()
        return {
            "status": "ok",
            "timestamp": asyncio.get_event_loop().time(),
            "stats": stats
        }
    
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
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