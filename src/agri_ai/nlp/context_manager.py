"""
対話の文脈管理機能
"""

import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConversationContext:
    """対話の文脈情報"""
    user_id: str
    current_task: Optional[str] = None
    current_field: Optional[str] = None
    current_crop: Optional[str] = None
    working_date: Optional[str] = None
    recent_questions: List[str] = None
    preferences: Dict[str, Any] = None
    work_history: List[Dict[str, Any]] = None
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.recent_questions is None:
            self.recent_questions = []
        if self.preferences is None:
            self.preferences = {}
        if self.work_history is None:
            self.work_history = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


class ContextManager:
    """対話の文脈を管理するクラス"""
    
    def __init__(self, max_history_size: int = 50):
        self.max_history_size = max_history_size
        self.contexts: Dict[str, ConversationContext] = {}
        
        # 文脈推測のためのキーワード
        self.context_keywords = {
            "task_related": {
                "播種": ["種", "まく", "播く", "タネ", "seeding"],
                "防除": ["薬", "散布", "農薬", "防除", "pest"],
                "収穫": ["採る", "収穫", "取る", "harvest"],
                "施肥": ["肥料", "養分", "栄養", "fertilizer"],
                "除草": ["草", "雑草", "除草", "weed"],
                "耕耘": ["耕す", "耕転", "tillage"],
                "定植": ["植える", "定植", "transplant"]
            },
            "status_related": {
                "進捗確認": ["どう", "状況", "進捗", "どんな感じ"],
                "完了報告": ["完了", "終わった", "できた", "終了"],
                "困っている": ["困って", "わからない", "どうしたら", "問題"],
                "提案依頼": ["どうしたら", "どうすれば", "提案", "おすすめ"]
            },
            "temporal": {
                "今日": ["今日", "きょう", "本日"],
                "昨日": ["昨日", "きのう"],
                "明日": ["明日", "あした", "あす"],
                "今週": ["今週", "こんしゅう"],
                "来週": ["来週", "らいしゅう"]
            }
        }
        
        # 省略表現のパターン
        self.ellipsis_patterns = {
            "それ": ["current_task", "current_field", "current_crop"],
            "あれ": ["recent_topic", "previous_subject"],
            "この": ["current_context"],
            "その": ["mentioned_item"],
            "どこ": ["current_field", "field_location"],
            "いつ": ["working_date", "schedule_time"],
            "誰": ["worker_name", "person_mentioned"]
        }
    
    def get_context(self, user_id: str) -> ConversationContext:
        """ユーザーの文脈を取得（存在しない場合は作成）"""
        if user_id not in self.contexts:
            self.contexts[user_id] = ConversationContext(user_id=user_id)
        
        return self.contexts[user_id]
    
    def update_context(self, user_id: str, **kwargs) -> None:
        """文脈情報を更新"""
        context = self.get_context(user_id)
        
        for key, value in kwargs.items():
            if hasattr(context, key):
                setattr(context, key, value)
        
        context.updated_at = datetime.now()
        logger.info(f"Updated context for user {user_id}: {kwargs}")
    
    def add_question_to_history(self, user_id: str, question: str) -> None:
        """質問を履歴に追加"""
        context = self.get_context(user_id)
        context.recent_questions.append({
            "question": question,
            "timestamp": datetime.now().isoformat()
        })
        
        # 履歴サイズの制限
        if len(context.recent_questions) > self.max_history_size:
            context.recent_questions = context.recent_questions[-self.max_history_size:]
        
        context.updated_at = datetime.now()
    
    def add_work_to_history(self, user_id: str, work_info: Dict[str, Any]) -> None:
        """作業情報を履歴に追加"""
        context = self.get_context(user_id)
        work_entry = {
            **work_info,
            "timestamp": datetime.now().isoformat()
        }
        context.work_history.append(work_entry)
        
        # 履歴サイズの制限
        if len(context.work_history) > self.max_history_size:
            context.work_history = context.work_history[-self.max_history_size:]
        
        context.updated_at = datetime.now()
    
    def infer_context_from_message(self, user_id: str, message: str) -> Dict[str, Any]:
        """メッセージから文脈を推測"""
        context = self.get_context(user_id)
        inferred = {}
        
        # タスク関連の推測
        for task, keywords in self.context_keywords["task_related"].items():
            if any(keyword in message.lower() for keyword in keywords):
                inferred["current_task"] = task
                break
        
        # 時間関連の推測
        for time_ref, keywords in self.context_keywords["temporal"].items():
            if any(keyword in message.lower() for keyword in keywords):
                if time_ref == "今日":
                    inferred["working_date"] = datetime.now().strftime("%Y-%m-%d")
                elif time_ref == "昨日":
                    inferred["working_date"] = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
                elif time_ref == "明日":
                    inferred["working_date"] = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                break
        
        # 圃場名の推測
        field_patterns = [
            r"([A-Z]\d+)",  # F14, A1 などの形式
            r"([^\s]+(?:圃場|畑|ハウス))",
            r"([^\s]+(?:家裏|家前|横|北|南|東|西))"
        ]
        
        import re
        for pattern in field_patterns:
            match = re.search(pattern, message)
            if match:
                inferred["current_field"] = match.group(1)
                break
        
        return inferred
    
    def resolve_ellipsis(self, user_id: str, message: str) -> str:
        """省略表現を解決"""
        context = self.get_context(user_id)
        resolved_message = message
        
        # 代名詞の解決
        for pronoun, context_keys in self.ellipsis_patterns.items():
            if pronoun in message:
                for key in context_keys:
                    if hasattr(context, key):
                        value = getattr(context, key)
                        if value:
                            resolved_message = resolved_message.replace(pronoun, str(value))
                            break
        
        # 「それ」「あれ」の解決
        if "それ" in message or "あれ" in message:
            # 直近の質問から推測
            if context.recent_questions:
                last_question = context.recent_questions[-1]["question"]
                # 最後の質問の主語を推測
                if context.current_task:
                    resolved_message = resolved_message.replace("それ", context.current_task)
                    resolved_message = resolved_message.replace("あれ", context.current_task)
        
        return resolved_message
    
    def get_relevant_context(self, user_id: str, message: str) -> Dict[str, Any]:
        """メッセージに関連する文脈情報を取得"""
        context = self.get_context(user_id)
        relevant_context = {}
        
        # 基本的な文脈情報
        if context.current_task:
            relevant_context["current_task"] = context.current_task
        if context.current_field:
            relevant_context["current_field"] = context.current_field
        if context.current_crop:
            relevant_context["current_crop"] = context.current_crop
        if context.working_date:
            relevant_context["working_date"] = context.working_date
        
        # メッセージの内容に応じた関連情報
        if any(word in message.lower() for word in ["前回", "この前", "昨日", "履歴"]):
            # 作業履歴から関連情報を取得
            if context.work_history:
                recent_work = context.work_history[-3:]  # 最新3件
                relevant_context["recent_work"] = recent_work
        
        if any(word in message.lower() for word in ["どこ", "場所", "圃場"]):
            # 圃場関連の情報
            if context.current_field:
                relevant_context["field_info"] = {
                    "name": context.current_field,
                    "crop": context.current_crop
                }
        
        if any(word in message.lower() for word in ["いつ", "時間", "日付"]):
            # 時間関連の情報
            relevant_context["temporal_info"] = {
                "working_date": context.working_date,
                "current_time": datetime.now().strftime("%H:%M")
            }
        
        return relevant_context
    
    def suggest_next_questions(self, user_id: str) -> List[str]:
        """次の質問候補を提案"""
        context = self.get_context(user_id)
        suggestions = []
        
        # 文脈に応じた提案
        if context.current_task:
            suggestions.append(f"{context.current_task}の進捗はどうですか？")
            suggestions.append(f"{context.current_task}で何か困っていることはありますか？")
        
        if context.current_field:
            suggestions.append(f"{context.current_field}の状況を教えてください")
            suggestions.append(f"{context.current_field}で今日やることは何ですか？")
        
        # 一般的な提案
        if not suggestions:
            suggestions.extend([
                "今日のタスクを教えてください",
                "圃場の状況を確認したいです",
                "作業の完了を報告したいです",
                "農薬の推奨を知りたいです"
            ])
        
        return suggestions[:5]  # 最大5つまで
    
    def get_context_summary(self, user_id: str) -> str:
        """文脈の要約を生成"""
        context = self.get_context(user_id)
        summary_parts = []
        
        if context.current_task:
            summary_parts.append(f"現在のタスク: {context.current_task}")
        
        if context.current_field:
            summary_parts.append(f"対象圃場: {context.current_field}")
        
        if context.current_crop:
            summary_parts.append(f"作物: {context.current_crop}")
        
        if context.working_date:
            summary_parts.append(f"作業日: {context.working_date}")
        
        if context.recent_questions:
            recent_count = len(context.recent_questions)
            summary_parts.append(f"最近の質問数: {recent_count}")
        
        if context.work_history:
            work_count = len(context.work_history)
            summary_parts.append(f"作業履歴数: {work_count}")
        
        if not summary_parts:
            return "文脈情報がありません"
        
        return " | ".join(summary_parts)
    
    def clear_context(self, user_id: str) -> None:
        """文脈をクリア"""
        if user_id in self.contexts:
            del self.contexts[user_id]
        logger.info(f"Cleared context for user {user_id}")
    
    def cleanup_old_contexts(self, days_threshold: int = 7) -> None:
        """古い文脈を削除"""
        cutoff_date = datetime.now() - timedelta(days=days_threshold)
        
        users_to_remove = []
        for user_id, context in self.contexts.items():
            if context.updated_at < cutoff_date:
                users_to_remove.append(user_id)
        
        for user_id in users_to_remove:
            del self.contexts[user_id]
        
        logger.info(f"Cleaned up {len(users_to_remove)} old contexts")
    
    def export_context(self, user_id: str) -> Dict[str, Any]:
        """文脈をエクスポート"""
        context = self.get_context(user_id)
        return {
            **asdict(context),
            "created_at": context.created_at.isoformat(),
            "updated_at": context.updated_at.isoformat()
        }
    
    def import_context(self, user_id: str, context_data: Dict[str, Any]) -> None:
        """文脈をインポート"""
        # 日付文字列を変換
        if "created_at" in context_data:
            context_data["created_at"] = datetime.fromisoformat(context_data["created_at"])
        if "updated_at" in context_data:
            context_data["updated_at"] = datetime.fromisoformat(context_data["updated_at"])
        
        self.contexts[user_id] = ConversationContext(**context_data)
        logger.info(f"Imported context for user {user_id}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        total_contexts = len(self.contexts)
        active_contexts = sum(1 for ctx in self.contexts.values() 
                            if ctx.updated_at > datetime.now() - timedelta(hours=24))
        
        avg_questions = 0
        avg_work_history = 0
        
        if total_contexts > 0:
            avg_questions = sum(len(ctx.recent_questions) for ctx in self.contexts.values()) / total_contexts
            avg_work_history = sum(len(ctx.work_history) for ctx in self.contexts.values()) / total_contexts
        
        return {
            "total_contexts": total_contexts,
            "active_contexts_24h": active_contexts,
            "average_questions_per_user": round(avg_questions, 2),
            "average_work_history_per_user": round(avg_work_history, 2)
        }