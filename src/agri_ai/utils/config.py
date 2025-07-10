"""
Configuration management for the Agricultural AI Agent.
"""

import os
from typing import Optional
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field, validator, ValidationError

from ..exceptions import ConfigurationError

load_dotenv()


class Environment(str, Enum):
    """環境タイプ"""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


@dataclass
class EnvironmentConfig:
    """環境固有の設定"""
    name: str
    debug: bool
    log_level: str
    timeout_seconds: int
    max_agents: int
    agent_ttl_minutes: int


# 環境別設定
ENVIRONMENT_CONFIGS = {
    Environment.DEVELOPMENT: EnvironmentConfig(
        name="development",
        debug=True,
        log_level="DEBUG",
        timeout_seconds=60,
        max_agents=10,
        agent_ttl_minutes=60
    ),
    Environment.PRODUCTION: EnvironmentConfig(
        name="production",
        debug=False,
        log_level="INFO",
        timeout_seconds=30,
        max_agents=100,
        agent_ttl_minutes=30
    ),
    Environment.TESTING: EnvironmentConfig(
        name="testing",
        debug=True,
        log_level="DEBUG",
        timeout_seconds=10,
        max_agents=5,
        agent_ttl_minutes=5
    )
}


class Settings(BaseSettings):
    """Application settings."""
    
    # Environment
    environment: Environment = Field(default=Environment.DEVELOPMENT, env="ENVIRONMENT")
    
    # Database
    mongodb_uri: str = Field(..., env="MONGODB_URI")
    mongodb_database: str = Field(default="agri_ai_db", env="MONGODB_DATABASE")
    
    # AI APIs
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    google_api_key: Optional[str] = Field(None, env="GOOGLE_API_KEY")
    
    # LINE Bot
    line_channel_access_token: Optional[str] = Field(None, env="LINE_CHANNEL_ACCESS_TOKEN")
    line_channel_secret: Optional[str] = Field(None, env="LINE_CHANNEL_SECRET")
    
    # Airtable
    airtable_api_key: Optional[str] = Field(None, env="AIRTABLE_API_KEY")
    airtable_base_id: Optional[str] = Field(None, env="AIRTABLE_BASE_ID")
    
    # Google Cloud
    google_cloud_project: Optional[str] = Field(None, env="GOOGLE_CLOUD_PROJECT")
    google_application_credentials: Optional[str] = Field(None, env="GOOGLE_APPLICATION_CREDENTIALS")
    
    # Application
    debug: Optional[bool] = Field(None, env="DEBUG")
    log_level: Optional[str] = Field(None, env="LOG_LEVEL")
    
    # Performance
    max_agents: Optional[int] = Field(None, env="MAX_AGENTS")
    agent_ttl_minutes: Optional[int] = Field(None, env="AGENT_TTL_MINUTES")
    request_timeout_seconds: Optional[int] = Field(None, env="REQUEST_TIMEOUT_SECONDS")
    
    # LINE Bot specific
    max_message_length: int = Field(default=2000, env="MAX_MESSAGE_LENGTH")
    max_conversation_history: int = Field(default=50, env="MAX_CONVERSATION_HISTORY")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._apply_environment_defaults()
        self._validate_configuration()
    
    def _apply_environment_defaults(self):
        """環境に応じたデフォルト値を適用"""
        env_config = ENVIRONMENT_CONFIGS.get(self.environment)
        if env_config:
            if self.debug is None:
                self.debug = env_config.debug
            if self.log_level is None:
                self.log_level = env_config.log_level
            if self.max_agents is None:
                self.max_agents = env_config.max_agents
            if self.agent_ttl_minutes is None:
                self.agent_ttl_minutes = env_config.agent_ttl_minutes
            if self.request_timeout_seconds is None:
                self.request_timeout_seconds = env_config.timeout_seconds
    
    def _validate_configuration(self):
        """設定の検証"""
        errors = []
        
        # MongoDB設定の検証
        if not self.mongodb_uri or self.mongodb_uri.startswith("your_"):
            errors.append("MongoDB URI が設定されていません")
        
        # AI API設定の検証
        if not self.openai_api_key and not self.google_api_key:
            errors.append("OpenAI API Key または Google API Key のいずれかが必要です")
        
        if self.openai_api_key and self.openai_api_key.startswith("your_"):
            self.openai_api_key = None
        
        if self.google_api_key and self.google_api_key.startswith("your_"):
            self.google_api_key = None
        
        # LINE Bot設定の検証（LINE Bot機能を使用する場合）
        if self.line_channel_access_token or self.line_channel_secret:
            if not self.line_channel_access_token or self.line_channel_access_token.startswith("your_"):
                errors.append("LINE Channel Access Token が設定されていません")
            if not self.line_channel_secret or self.line_channel_secret.startswith("your_"):
                errors.append("LINE Channel Secret が設定されていません")
        
        if errors:
            raise ConfigurationError(
                "設定エラー: " + ", ".join(errors),
                context={"errors": errors}
            )
    
    @validator('mongodb_uri')
    def validate_mongodb_uri(cls, v):
        """MongoDB URIの基本的な検証"""
        if not v.startswith('mongodb://') and not v.startswith('mongodb+srv://'):
            raise ValueError('MongoDB URI は mongodb:// または mongodb+srv:// で始まる必要があります')
        return v
    
    @validator('max_agents')
    def validate_max_agents(cls, v):
        """最大エージェント数の検証"""
        if v is not None and v < 1:
            raise ValueError('最大エージェント数は1以上である必要があります')
        return v
    
    @validator('agent_ttl_minutes')
    def validate_agent_ttl(cls, v):
        """エージェントTTLの検証"""
        if v is not None and v < 1:
            raise ValueError('エージェントTTLは1分以上である必要があります')
        return v
    
    @property
    def is_line_bot_enabled(self) -> bool:
        """LINE Bot機能が有効かどうか"""
        return bool(self.line_channel_access_token and self.line_channel_secret)
    
    @property
    def is_production(self) -> bool:
        """本番環境かどうか"""
        return self.environment == Environment.PRODUCTION
    
    @property
    def is_development(self) -> bool:
        """開発環境かどうか"""
        return self.environment == Environment.DEVELOPMENT
    
    @property
    def is_testing(self) -> bool:
        """テスト環境かどうか"""
        return self.environment == Environment.TESTING
    
    def get_ai_model_config(self) -> dict:
        """AIモデル設定を取得"""
        config = {
            "temperature": 0.1,
            "max_tokens": 1000,
            "timeout": self.request_timeout_seconds
        }
        
        if self.google_api_key:
            config.update({
                "provider": "google",
                "model": "gemini-2.5-flash",
                "api_key": self.google_api_key
            })
        elif self.openai_api_key:
            config.update({
                "provider": "openai",
                "model": "gpt-4",
                "api_key": self.openai_api_key
            })
        
        return config


class ConfigManager:
    """設定管理シングルトン"""
    _instance = None
    _settings = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            try:
                cls._settings = Settings()
            except ValidationError as e:
                raise ConfigurationError(
                    f"設定の検証に失敗しました: {str(e)}",
                    context={"validation_errors": e.errors()}
                )
        return cls._instance
    
    @property
    def settings(self) -> Settings:
        """設定を取得"""
        return self._settings
    
    def reload_settings(self):
        """設定を再読み込み"""
        try:
            self._settings = Settings()
        except ValidationError as e:
            raise ConfigurationError(
                f"設定の再読み込みに失敗しました: {str(e)}",
                context={"validation_errors": e.errors()}
            )


# シングルトンインスタンス
_config_manager = ConfigManager()


def get_settings() -> Settings:
    """設定を取得（後方互換性のため）"""
    return _config_manager.settings


def get_config_manager() -> ConfigManager:
    """設定マネージャーを取得"""
    return _config_manager