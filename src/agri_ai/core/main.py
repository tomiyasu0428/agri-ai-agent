"""
Main entry point for the Agricultural AI Agent.
"""

import asyncio
import logging
from typing import Optional

from .database import MongoDBClient, AgriDatabase
from .agent import AgentManager
from ..utils.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AgriAISystem:
    """Main system class for the Agricultural AI Agent."""
    
    def __init__(self):
        self.settings = get_settings()
        self.mongo_client: Optional[MongoDBClient] = None
        self.agri_db: Optional[AgriDatabase] = None
        self.agent_manager: Optional[AgentManager] = None
        
    async def initialize(self):
        """Initialize the system components."""
        try:
            # Initialize database
            self.mongo_client = MongoDBClient()
            await self.mongo_client.connect()
            
            self.agri_db = AgriDatabase(self.mongo_client)
            
            # Initialize agent manager
            self.agent_manager = AgentManager(self.agri_db)
            
            logger.info("Agricultural AI System initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize system: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown the system gracefully."""
        if self.mongo_client:
            await self.mongo_client.disconnect()
        
        logger.info("Agricultural AI System shutdown complete")
    
    async def process_message(self, user_id: str, message: str) -> str:
        """Process a message from a user."""
        if not self.agent_manager:
            raise RuntimeError("System not initialized")
        
        return await self.agent_manager.process_user_message(user_id, message)
    
    async def health_check(self) -> dict:
        """Perform system health check."""
        health_status = {
            "status": "healthy",
            "database": False,
            "agents": 0
        }
        
        # Check database connection
        if self.mongo_client:
            health_status["database"] = await self.mongo_client.health_check()
        
        # Check agent manager
        if self.agent_manager:
            stats = self.agent_manager.get_agent_stats()
            health_status["agents"] = stats["total_agents"]
        
        # Overall status
        if not health_status["database"]:
            health_status["status"] = "unhealthy"
        
        return health_status


# Global system instance
agri_system = AgriAISystem()


async def main():
    """Main function for testing the system."""
    try:
        # Initialize system
        await agri_system.initialize()
        
        # Test basic functionality
        print("=== Agricultural AI Agent Test ===")
        
        # Health check
        health = await agri_system.health_check()
        print(f"Health check: {health}")
        
        # Test user interaction
        test_user = "田中"
        test_messages = [
            "こんにちは、今日のタスクを教えてください",
            "鴨川家裏の状況を確認してください",
            "大豆の防除におすすめの農薬を教えてください"
        ]
        
        for message in test_messages:
            print(f"\nUser: {message}")
            response = await agri_system.process_message(test_user, message)
            print(f"AI: {response}")
        
        # Agent statistics
        if agri_system.agent_manager:
            stats = agri_system.agent_manager.get_agent_stats()
            print(f"\nAgent Statistics: {stats}")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        
    finally:
        await agri_system.shutdown()


if __name__ == "__main__":
    asyncio.run(main())