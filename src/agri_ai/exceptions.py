"""
農業AI システム用カスタム例外クラス
"""

from typing import Optional, Dict, Any


class AgriAIException(Exception):
    """農業AI基底例外"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
    
    def __str__(self) -> str:
        return self.message


class DatabaseConnectionError(AgriAIException):
    """データベース接続エラー"""
    
    def __init__(self, message: str = "データベースとの接続に問題があります", **kwargs):
        super().__init__(message, error_code="DB_CONNECTION_ERROR", **kwargs)


class DatabaseQueryError(AgriAIException):
    """データベースクエリエラー"""
    
    def __init__(self, message: str = "データベースクエリでエラーが発生しました", **kwargs):
        super().__init__(message, error_code="DB_QUERY_ERROR", **kwargs)


class AgentProcessingError(AgriAIException):
    """エージェント処理エラー"""
    
    def __init__(self, message: str = "AI処理中にエラーが発生しました", **kwargs):
        super().__init__(message, error_code="AGENT_PROCESSING_ERROR", **kwargs)


class ValidationError(AgriAIException):
    """バリデーションエラー"""
    
    def __init__(self, message: str = "入力内容に問題があります", **kwargs):
        super().__init__(message, error_code="VALIDATION_ERROR", **kwargs)


class ConfigurationError(AgriAIException):
    """設定エラー"""
    
    def __init__(self, message: str = "設定に問題があります", **kwargs):
        super().__init__(message, error_code="CONFIG_ERROR", **kwargs)


class LINEBotError(AgriAIException):
    """LINE Bot エラー"""
    
    def __init__(self, message: str = "LINE Bot処理中にエラーが発生しました", **kwargs):
        super().__init__(message, error_code="LINEBOT_ERROR", **kwargs)


class NLPProcessingError(AgriAIException):
    """自然言語処理エラー"""
    
    def __init__(self, message: str = "自然言語処理でエラーが発生しました", **kwargs):
        super().__init__(message, error_code="NLP_PROCESSING_ERROR", **kwargs)


class APIError(AgriAIException):
    """外部API呼び出しエラー"""
    
    def __init__(self, message: str = "外部API呼び出しでエラーが発生しました", **kwargs):
        super().__init__(message, error_code="API_ERROR", **kwargs)


class AuthenticationError(AgriAIException):
    """認証エラー"""
    
    def __init__(self, message: str = "認証に失敗しました", **kwargs):
        super().__init__(message, error_code="AUTH_ERROR", **kwargs)


class RateLimitError(AgriAIException):
    """レート制限エラー"""
    
    def __init__(self, message: str = "レート制限に達しました", **kwargs):
        super().__init__(message, error_code="RATE_LIMIT_ERROR", **kwargs)


class TimeoutError(AgriAIException):
    """タイムアウトエラー"""
    
    def __init__(self, message: str = "処理がタイムアウトしました", **kwargs):
        super().__init__(message, error_code="TIMEOUT_ERROR", **kwargs)


# エラーコードとメッセージのマッピング
ERROR_MESSAGES = {
    "DB_CONNECTION_ERROR": "データベースとの接続に問題があります。しばらくしてからお試しください。",
    "DB_QUERY_ERROR": "データベースクエリでエラーが発生しました。もう一度お試しください。",
    "AGENT_PROCESSING_ERROR": "AI処理中にエラーが発生しました。もう一度お試しください。",
    "VALIDATION_ERROR": "入力内容に問題があります。確認してください。",
    "CONFIG_ERROR": "システム設定に問題があります。管理者にお問い合わせください。",
    "LINEBOT_ERROR": "LINE Bot処理中にエラーが発生しました。もう一度お試しください。",
    "NLP_PROCESSING_ERROR": "メッセージの解析でエラーが発生しました。もう一度お試しください。",
    "API_ERROR": "外部API呼び出しでエラーが発生しました。しばらくしてからお試しください。",
    "AUTH_ERROR": "認証に失敗しました。設定を確認してください。",
    "RATE_LIMIT_ERROR": "利用制限に達しました。しばらくしてからお試しください。",
    "TIMEOUT_ERROR": "処理がタイムアウトしました。もう一度お試しください。",
    "GENERAL_ERROR": "申し訳ございません。システムエラーが発生しました。"
}


def get_user_friendly_message(error_code: str) -> str:
    """ユーザーフレンドリーなエラーメッセージを取得"""
    return ERROR_MESSAGES.get(error_code, ERROR_MESSAGES["GENERAL_ERROR"])