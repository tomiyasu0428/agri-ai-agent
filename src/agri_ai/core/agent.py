"""
LangChain agent for agricultural AI system.
"""

import logging
from typing import Dict, Any, List, Optional
from langchain.agents import AgentType, initialize_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import ConversationBufferMemory
from langchain.tools import BaseTool
from langchain.schema import SystemMessage

from ..tools.agricultural_tools import create_agricultural_tools
from ..core.database import AgriDatabase
from ..utils.config import get_settings
from ..nlp.report_parser import WorkReportParser
from ..nlp.context_manager import ContextManager

logger = logging.getLogger(__name__)


class AgriAIAgent:
    """Agricultural AI Agent using LangChain."""
    
    def __init__(self, agri_db: AgriDatabase):
        self.agri_db = agri_db
        self.settings = get_settings()
        
        # Initialize NLP modules
        self.report_parser = WorkReportParser()
        self.context_manager = ContextManager()
        
        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            temperature=0.1,
            google_api_key=self.settings.google_api_key
        )
        
        # Initialize memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Create tools
        self.tools = create_agricultural_tools(agri_db)
        
        # Initialize agent
        self.agent = self._create_agent()
    
    def _create_agent(self):
        """Create the LangChain agent with agricultural tools."""
        system_message = """あなたは農業管理AIエージェントです。ダチョウファームの農作業員や管理者をサポートします。

あなたの役割:
1. 農作業員の質問に対して具体的で実用的な回答を提供する
2. 作業タスクの管理と進捗確認をサポートする
3. 圃場の状況に基づいた農薬や作業の提案を行う
4. 作業完了報告を処理し、次回作業を自動スケジューリングする

応答の際の注意点:
- 常に安全第一で、農薬使用時は希釈倍率や天候条件を確認するよう指導する
- 作業員のスキルレベルに関わらず、分かりやすい説明を心がける
- 不明な点がある場合は、適切なツールを使用して情報を取得する
- 緊急時や判断に迷う場合は、熟練者に相談するよう促す

利用可能なツール:
- get_today_tasks: 今日のタスクを取得
- complete_task: 作業完了を記録
- get_field_status: 圃場の現在の状況を確認
- recommend_pesticide: 農薬の推奨を提供

常に親切で専門的な態度で、農作業員が自信を持って作業できるようサポートしてください。"""
        
        return initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            memory=self.memory,
            verbose=True,
            agent_kwargs={"system_message": system_message},
            handle_parsing_errors=True
        )
    
    async def process_message(self, user_message: str, user_id: str) -> str:
        """Process a user message and return AI response."""
        try:
            # Add message to conversation history
            self.context_manager.add_question_to_history(user_id, user_message)
            
            # Resolve ellipsis using context
            resolved_message = self.context_manager.resolve_ellipsis(user_id, user_message)
            
            # Infer context from message
            inferred_context = self.context_manager.infer_context_from_message(user_id, resolved_message)
            if inferred_context:
                self.context_manager.update_context(user_id, **inferred_context)
            
            # Get relevant context
            relevant_context = self.context_manager.get_relevant_context(user_id, resolved_message)
            
            # Check if message is a work report
            if self._is_work_report(resolved_message):
                return await self._process_work_report(resolved_message, user_id)
            
            # Prepare contextualized message
            context_info = ""
            if relevant_context:
                context_info = f"文脈情報: {relevant_context}\n"
            
            contextualized_message = f"ユーザーID: {user_id}\n{context_info}メッセージ: {resolved_message}"
            
            # Get agent response
            response = await self.agent.arun(input=contextualized_message)
            
            logger.info(f"Agent response for user {user_id}: {response}")
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"申し訳ございません。処理中にエラーが発生しました。もう一度お試しください。\nエラー詳細: {str(e)}"
    
    def _is_work_report(self, message: str) -> bool:
        """Check if the message is a work report."""
        report_indicators = [
            "完了", "終了", "実施", "やった", "行った", "散布", "収穫", "播種", "防除"
        ]
        return any(indicator in message for indicator in report_indicators)
    
    async def _process_work_report(self, message: str, user_id: str) -> str:
        """Process a work report message."""
        try:
            # Parse the work report
            parsed_report = self.report_parser.parse_report(message)
            
            # Validate the report
            issues = self.report_parser.validate_report(parsed_report)
            
            # Update context with work information
            if parsed_report.task_name:
                self.context_manager.update_context(user_id, current_task=parsed_report.task_name)
            if parsed_report.field_name:
                self.context_manager.update_context(user_id, current_field=parsed_report.field_name)
            if parsed_report.crop_name:
                self.context_manager.update_context(user_id, current_crop=parsed_report.crop_name)
            
            # Add to work history
            work_info = {
                "task": parsed_report.task_name,
                "field": parsed_report.field_name,
                "crop": parsed_report.crop_name,
                "status": parsed_report.completion_status,
                "materials": parsed_report.materials_used,
                "confidence": parsed_report.confidence_score
            }
            self.context_manager.add_work_to_history(user_id, work_info)
            
            # Format response
            response_parts = []
            
            # Report summary
            summary = self.report_parser.format_report_summary(parsed_report)
            response_parts.append(f"📋 作業報告を受付ました:\n{summary}")
            
            # Issues and suggestions
            if issues['errors']:
                response_parts.append(f"❌ エラー: {', '.join(issues['errors'])}")
            if issues['warnings']:
                response_parts.append(f"⚠️ 注意: {', '.join(issues['warnings'])}")
            if issues['suggestions']:
                response_parts.append(f"💡 提案: {', '.join(issues['suggestions'])}")
            
            # Next task suggestion
            if parsed_report.next_task_suggestion:
                response_parts.append(f"🔮 次回作業提案: {parsed_report.next_task_suggestion}")
            
            # Confidence score
            if parsed_report.confidence_score < 0.7:
                response_parts.append(f"📊 解析信頼度: {parsed_report.confidence_score:.1%} - より詳細な情報があると助かります")
            
            return "\n\n".join(response_parts)
            
        except Exception as e:
            logger.error(f"Error processing work report: {e}")
            return f"作業報告の処理中にエラーが発生しました: {str(e)}"
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get the conversation history."""
        try:
            messages = self.memory.chat_memory.messages
            history = []
            
            for msg in messages:
                if hasattr(msg, 'content'):
                    history.append({
                        "type": msg.__class__.__name__,
                        "content": msg.content,
                        "timestamp": getattr(msg, 'timestamp', None)
                    })
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []
    
    def clear_memory(self):
        """Clear the conversation memory."""
        self.memory.clear()
        logger.info("Conversation memory cleared")
    
    def add_user_context(self, user_id: str, context: Dict[str, Any]):
        """Add user-specific context to memory."""
        try:
            context_message = f"ユーザー {user_id} の情報: {context}"
            self.memory.chat_memory.add_user_message(context_message)
            logger.info(f"Added context for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error adding user context: {e}")


class AgentManager:
    """Manages multiple agent instances for different users."""
    
    def __init__(self, agri_db: AgriDatabase):
        self.agri_db = agri_db
        self.agents: Dict[str, AgriAIAgent] = {}
    
    def get_agent(self, user_id: str) -> AgriAIAgent:
        """Get or create an agent for a specific user."""
        if user_id not in self.agents:
            self.agents[user_id] = AgriAIAgent(self.agri_db)
            logger.info(f"Created new agent for user {user_id}")
        
        return self.agents[user_id]
    
    def remove_agent(self, user_id: str):
        """Remove an agent for a specific user."""
        if user_id in self.agents:
            del self.agents[user_id]
            logger.info(f"Removed agent for user {user_id}")
    
    def get_active_users(self) -> List[str]:
        """Get list of users with active agents."""
        return list(self.agents.keys())
    
    async def process_user_message(self, user_id: str, message: str) -> str:
        """Process a message for a specific user."""
        agent = self.get_agent(user_id)
        return await agent.process_message(message, user_id)
    
    def clear_user_memory(self, user_id: str):
        """Clear memory for a specific user."""
        if user_id in self.agents:
            self.agents[user_id].clear_memory()
    
    def get_agent_stats(self) -> Dict[str, Any]:
        """Get statistics about active agents."""
        return {
            "total_agents": len(self.agents),
            "active_users": list(self.agents.keys()),
            "memory_usage": {
                user_id: len(agent.get_conversation_history())
                for user_id, agent in self.agents.items()
            }
        }