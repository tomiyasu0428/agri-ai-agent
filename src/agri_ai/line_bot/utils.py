"""
Utility functions for LINE Bot.
"""

import re
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def format_agent_response(response: str) -> str:
    """Format AI agent response for LINE display."""
    try:
        # Remove excessive whitespace
        response = re.sub(r'\n\s*\n', '\n\n', response)
        
        # Convert markdown-style formatting to LINE-friendly format
        response = response.replace('**', '')
        response = response.replace('*', '•')
        
        # Add emoji to section headers
        response = response.replace('📋 作業報告', '📋 作業報告')
        response = response.replace('❌ エラー', '❌ エラー')
        response = response.replace('⚠️ 注意', '⚠️ 注意')
        response = response.replace('💡 提案', '💡 提案')
        response = response.replace('🔮 次回作業提案', '🔮 次回作業提案')
        response = response.replace('📊 解析信頼度', '📊 解析信頼度')
        
        # Limit response length
        if len(response) > 2000:
            response = response[:1950] + "...\n\n（応答が長すぎるため省略されました）"
        
        return response
        
    except Exception as e:
        logger.error(f"Error formatting response: {e}")
        return response


def create_welcome_message(user_name: str) -> str:
    """Create welcome message for new users."""
    return f"""こんにちは、{user_name}さん！🌾

農業AIアシスタントへようこそ！

主な機能：
📅 今日の作業確認
📝 作業報告の記録
🌾 圃場情報の確認
🧪 農薬・資材の推奨

使い方：
• 「今日の作業は？」
• 「F14で大豆の防除完了」
• 「F14の状況教えて」
• 「大豆の農薬について」

何かご質問がありましたら、お気軽にお声がけください！"""


def create_error_message() -> str:
    """Create error message."""
    return """申し訳ございません。
現在システムに問題が発生しております。

しばらくしてから再度お試しください。

問題が続く場合は、管理者にお問い合わせください。"""


def create_help_message() -> str:
    """Create help message."""
    return """🌾 農業AIアシスタント - ヘルプ

【基本的な使い方】

📅 今日の作業確認
• 「今日の作業は？」
• 「タスクを教えて」
• 「何をすればいい？」

📝 作業報告
• 「F14で大豆の防除完了」
• 「播種作業を午前中に実施」
• 「クプロシールドを1000倍で散布完了」

🌾 圃場情報
• 「F14の状況教えて」
• 「圃場の情報を確認」

🧪 農薬・資材
• 「大豆の農薬について」
• 「防除の推奨は？」

【その他のコマンド】
• 「ヘルプ」- このメッセージを表示
• 「リセット」- 会話履歴をリセット

何かご不明な点がございましたら、お気軽にお声がけください！"""


def parse_command(message: str) -> Optional[str]:
    """Parse special commands from message."""
    message = message.strip().lower()
    
    # Help commands
    if message in ['ヘルプ', 'help', '使い方', '説明']:
        return 'help'
    
    # Reset commands
    if message in ['リセット', 'reset', '初期化', 'クリア']:
        return 'reset'
    
    # Status commands
    if message in ['ステータス', 'status', '状態']:
        return 'status'
    
    return None


def extract_field_name(message: str) -> Optional[str]:
    """Extract field name from message."""
    # Look for field patterns like F14, F1, etc.
    field_match = re.search(r'[Ff](\d+)', message)
    if field_match:
        return f"F{field_match.group(1)}"
    
    # Look for other field patterns
    field_patterns = [
        r'鵡川.*?家裏',
        r'橋向こう.*?③',
        r'石谷.*?横',
        r'大豆.*?圃場',
        r'トマト.*?圃場'
    ]
    
    for pattern in field_patterns:
        match = re.search(pattern, message)
        if match:
            return match.group(0)
    
    return None


def extract_task_type(message: str) -> Optional[str]:
    """Extract task type from message."""
    task_keywords = {
        '防除': ['防除', '散布', '農薬', 'スプレー'],
        '播種': ['播種', '種まき', '種蒔き', '植え付け'],
        '収穫': ['収穫', '刈り取り', '採取'],
        '耕起': ['耕起', '耕す', '田起こし'],
        '施肥': ['施肥', '肥料', '追肥'],
        '除草': ['除草', '草刈り', '草取り'],
        '灌水': ['灌水', '水やり', '散水'],
        '管理': ['管理', '見回り', '点検']
    }
    
    for task_type, keywords in task_keywords.items():
        if any(keyword in message for keyword in keywords):
            return task_type
    
    return None


def format_time_ago(timestamp: datetime) -> str:
    """Format time ago from timestamp."""
    now = datetime.now()
    diff = now - timestamp
    
    if diff.days > 0:
        return f"{diff.days}日前"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours}時間前"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes}分前"
    else:
        return "たった今"


def is_work_report(message: str) -> bool:
    """Check if message is a work report."""
    report_indicators = [
        '完了', '終了', '実施', 'やった', '行った', 
        '散布', '収穫', '播種', '防除', '施肥', '除草',
        '終わり', '終わった', '済み', '済んだ'
    ]
    
    return any(indicator in message for indicator in report_indicators)


def clean_message(message: str) -> str:
    """Clean and normalize message."""
    # Remove extra whitespace
    message = re.sub(r'\s+', ' ', message).strip()
    
    # Remove special characters that might cause issues
    message = re.sub(r'[^\w\s\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF\u3400-\u4DBF]', '', message)
    
    return message