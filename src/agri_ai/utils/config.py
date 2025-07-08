"""
Configuration management for the Agricultural AI Agent.
"""

import os
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseSettings, Field

load_dotenv()


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    mongodb_uri: str = Field(..., env="MONGODB_URI")
    mongodb_database: str = Field(default="agri_ai_db", env="MONGODB_DATABASE")
    
    # OpenAI
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    
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
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()