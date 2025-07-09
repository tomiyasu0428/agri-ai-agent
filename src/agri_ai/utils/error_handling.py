"""
エラーハンドリングユーティリティ
"""

import logging
import functools
from typing import Callable, Any, Optional, Type, Union
from datetime import datetime

from ..exceptions import (
    AgriAIException, 
    DatabaseConnectionError,
    DatabaseQueryError,
    AgentProcessingError,
    NLPProcessingError,
    LINEBotError,
    APIError,
    TimeoutError,
    get_user_friendly_message
)


class ErrorHandler:
    """エラーハンドリングユーティリティクラス"""
    
    @staticmethod
    def handle_async_error(
        operation: str,
        logger: logging.Logger,
        default_exception: Type[AgriAIException] = AgriAIException,
        return_error_message: bool = False
    ):
        """非同期関数用エラーハンドリングデコレータ"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except AgriAIException as e:
                    logger.error(f"AgriAI Error in {operation}: {e.message}", extra={
                        "error_code": e.error_code,
                        "context": e.context,
                        "operation": operation
                    })
                    if return_error_message:
                        return get_user_friendly_message(e.error_code)
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error in {operation}: {str(e)}", extra={
                        "operation": operation,
                        "error_type": type(e).__name__
                    })
                    if return_error_message:
                        return get_user_friendly_message("GENERAL_ERROR")
                    raise default_exception(f"{operation}中にエラーが発生しました: {str(e)}")
            return wrapper
        return decorator
    
    @staticmethod
    def handle_sync_error(
        operation: str,
        logger: logging.Logger,
        default_exception: Type[AgriAIException] = AgriAIException,
        return_error_message: bool = False
    ):
        """同期関数用エラーハンドリングデコレータ"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except AgriAIException as e:
                    logger.error(f"AgriAI Error in {operation}: {e.message}", extra={
                        "error_code": e.error_code,
                        "context": e.context,
                        "operation": operation
                    })
                    if return_error_message:
                        return get_user_friendly_message(e.error_code)
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error in {operation}: {str(e)}", extra={
                        "operation": operation,
                        "error_type": type(e).__name__
                    })
                    if return_error_message:
                        return get_user_friendly_message("GENERAL_ERROR")
                    raise default_exception(f"{operation}中にエラーが発生しました: {str(e)}")
            return wrapper
        return decorator
    
    @staticmethod
    def log_and_reraise(
        logger: logging.Logger,
        operation: str,
        exception: Exception,
        context: Optional[dict] = None
    ):
        """エラーをログに記録して再発生させる"""
        if isinstance(exception, AgriAIException):
            logger.error(
                f"AgriAI Error in {operation}: {exception.message}",
                extra={
                    "error_code": exception.error_code,
                    "context": {**(exception.context or {}), **(context or {})},
                    "operation": operation
                }
            )
        else:
            logger.error(
                f"Unexpected error in {operation}: {str(exception)}",
                extra={
                    "operation": operation,
                    "error_type": type(exception).__name__,
                    "context": context or {}
                }
            )
        raise exception
    
    @staticmethod
    def create_error_response(
        exception: Union[Exception, str],
        operation: str,
        logger: logging.Logger,
        include_details: bool = False
    ) -> dict:
        """エラーレスポンスを作成"""
        timestamp = datetime.now().isoformat()
        
        if isinstance(exception, AgriAIException):
            error_code = exception.error_code
            message = get_user_friendly_message(error_code)
            context = exception.context if include_details else {}
            
            logger.error(f"Error in {operation}: {exception.message}", extra={
                "error_code": error_code,
                "context": context,
                "operation": operation
            })
            
            return {
                "success": False,
                "error_code": error_code,
                "message": message,
                "timestamp": timestamp,
                "operation": operation,
                **({"context": context} if include_details else {})
            }
        
        elif isinstance(exception, Exception):
            error_code = "GENERAL_ERROR"
            message = get_user_friendly_message(error_code)
            
            logger.error(f"Unexpected error in {operation}: {str(exception)}", extra={
                "operation": operation,
                "error_type": type(exception).__name__
            })
            
            return {
                "success": False,
                "error_code": error_code,
                "message": message,
                "timestamp": timestamp,
                "operation": operation,
                **({"details": str(exception)} if include_details else {})
            }
        
        else:
            # 文字列の場合
            return {
                "success": False,
                "error_code": "GENERAL_ERROR",
                "message": str(exception),
                "timestamp": timestamp,
                "operation": operation
            }


class DatabaseErrorHandler:
    """データベース関連エラーハンドリング"""
    
    @staticmethod
    def handle_connection_error(logger: logging.Logger):
        """データベース接続エラーハンドリング"""
        return ErrorHandler.handle_async_error(
            "database connection",
            logger,
            DatabaseConnectionError,
            return_error_message=True
        )
    
    @staticmethod
    def handle_query_error(logger: logging.Logger):
        """データベースクエリエラーハンドリング"""
        return ErrorHandler.handle_async_error(
            "database query",
            logger,
            DatabaseQueryError,
            return_error_message=True
        )


class AgentErrorHandler:
    """エージェント関連エラーハンドリング"""
    
    @staticmethod
    def handle_processing_error(logger: logging.Logger):
        """エージェント処理エラーハンドリング"""
        return ErrorHandler.handle_async_error(
            "agent processing",
            logger,
            AgentProcessingError,
            return_error_message=True
        )


class NLPErrorHandler:
    """自然言語処理関連エラーハンドリング"""
    
    @staticmethod
    def handle_processing_error(logger: logging.Logger):
        """NLP処理エラーハンドリング"""
        return ErrorHandler.handle_async_error(
            "NLP processing",
            logger,
            NLPProcessingError,
            return_error_message=True
        )


class LINEBotErrorHandler:
    """LINE Bot関連エラーハンドリング"""
    
    @staticmethod
    def handle_message_error(logger: logging.Logger):
        """メッセージ処理エラーハンドリング"""
        return ErrorHandler.handle_async_error(
            "LINE Bot message processing",
            logger,
            LINEBotError,
            return_error_message=True
        )
    
    @staticmethod
    def handle_api_error(logger: logging.Logger):
        """LINE Bot API エラーハンドリング"""
        return ErrorHandler.handle_async_error(
            "LINE Bot API",
            logger,
            LINEBotError,
            return_error_message=True
        )


# 共通エラーハンドラーのインスタンス
error_handler = ErrorHandler()
db_error_handler = DatabaseErrorHandler()
agent_error_handler = AgentErrorHandler()
nlp_error_handler = NLPErrorHandler()
linebot_error_handler = LINEBotErrorHandler()