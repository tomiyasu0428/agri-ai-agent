"""
Tests for the agricultural AI agent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.agri_ai.core.agent import AgriAIAgent, AgentManager
from src.agri_ai.core.database import AgriDatabase


class TestAgriAIAgent:
    """Test the agricultural AI agent."""
    
    @pytest.fixture
    def mock_agri_db(self):
        """Create a mock agricultural database."""
        return AsyncMock(spec=AgriDatabase)
    
    @pytest.fixture
    def mock_agent(self, mock_agri_db):
        """Create a mock agent."""
        with patch('src.agri_ai.core.agent.get_settings') as mock_settings:
            mock_settings.return_value.openai_api_key = "test_key"
            
            with patch('src.agri_ai.core.agent.ChatOpenAI') as mock_llm:
                with patch('src.agri_ai.core.agent.initialize_agent') as mock_init_agent:
                    mock_init_agent.return_value = AsyncMock()
                    agent = AgriAIAgent(mock_agri_db)
                    return agent
    
    @pytest.mark.asyncio
    async def test_process_message_success(self, mock_agent):
        """Test successful message processing."""
        mock_agent.agent.arun.return_value = "今日のタスクを確認しました。"
        
        response = await mock_agent.process_message("今日のタスクは？", "田中")
        
        assert "今日のタスクを確認しました。" in response
        mock_agent.agent.arun.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_message_error(self, mock_agent):
        """Test message processing with error."""
        mock_agent.agent.arun.side_effect = Exception("API Error")
        
        response = await mock_agent.process_message("今日のタスクは？", "田中")
        
        assert "申し訳ございません" in response
        assert "エラーが発生しました" in response
    
    def test_clear_memory(self, mock_agent):
        """Test memory clearing."""
        mock_agent.clear_memory()
        mock_agent.memory.clear.assert_called_once()
    
    def test_get_conversation_history(self, mock_agent):
        """Test conversation history retrieval."""
        # Mock memory messages
        mock_message = MagicMock()
        mock_message.content = "Test message"
        mock_message.__class__.__name__ = "HumanMessage"
        
        mock_agent.memory.chat_memory.messages = [mock_message]
        
        history = mock_agent.get_conversation_history()
        
        assert len(history) == 1
        assert history[0]["content"] == "Test message"
        assert history[0]["type"] == "HumanMessage"


class TestAgentManager:
    """Test the agent manager."""
    
    @pytest.fixture
    def mock_agri_db(self):
        """Create a mock agricultural database."""
        return AsyncMock(spec=AgriDatabase)
    
    @pytest.fixture
    def agent_manager(self, mock_agri_db):
        """Create an agent manager."""
        return AgentManager(mock_agri_db)
    
    def test_get_agent_creates_new(self, agent_manager):
        """Test that get_agent creates a new agent for new users."""
        with patch('src.agri_ai.core.agent.AgriAIAgent') as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent_class.return_value = mock_agent
            
            agent = agent_manager.get_agent("田中")
            
            assert agent == mock_agent
            assert "田中" in agent_manager.agents
    
    def test_get_agent_returns_existing(self, agent_manager):
        """Test that get_agent returns existing agent for known users."""
        mock_agent = MagicMock()
        agent_manager.agents["田中"] = mock_agent
        
        agent = agent_manager.get_agent("田中")
        
        assert agent == mock_agent
    
    def test_remove_agent(self, agent_manager):
        """Test agent removal."""
        mock_agent = MagicMock()
        agent_manager.agents["田中"] = mock_agent
        
        agent_manager.remove_agent("田中")
        
        assert "田中" not in agent_manager.agents
    
    def test_get_active_users(self, agent_manager):
        """Test getting active users."""
        agent_manager.agents["田中"] = MagicMock()
        agent_manager.agents["佐藤"] = MagicMock()
        
        users = agent_manager.get_active_users()
        
        assert set(users) == {"田中", "佐藤"}
    
    @pytest.mark.asyncio
    async def test_process_user_message(self, agent_manager):
        """Test processing user message."""
        mock_agent = MagicMock()
        mock_agent.process_message.return_value = "Test response"
        
        with patch.object(agent_manager, 'get_agent', return_value=mock_agent):
            response = await agent_manager.process_user_message("田中", "Test message")
            
            assert response == "Test response"
            mock_agent.process_message.assert_called_once_with("Test message", "田中")
    
    def test_get_agent_stats(self, agent_manager):
        """Test getting agent statistics."""
        mock_agent1 = MagicMock()
        mock_agent1.get_conversation_history.return_value = [{"msg": "1"}, {"msg": "2"}]
        
        mock_agent2 = MagicMock()
        mock_agent2.get_conversation_history.return_value = [{"msg": "1"}]
        
        agent_manager.agents["田中"] = mock_agent1
        agent_manager.agents["佐藤"] = mock_agent2
        
        stats = agent_manager.get_agent_stats()
        
        assert stats["total_agents"] == 2
        assert set(stats["active_users"]) == {"田中", "佐藤"}
        assert stats["memory_usage"]["田中"] == 2
        assert stats["memory_usage"]["佐藤"] == 1