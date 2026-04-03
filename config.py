from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Qwen CLI configuration
    QWEN_MODEL: str = "qwen2.5-coder"
    QWEN_CLI_PATH: str = "qwen"  # Command to run qwen-cli
    QWEN_TIMEOUT: int = 300  # Max time for CLI response (seconds)
    
    # API configuration
    API_KEY: Optional[str] = None  # Optional API key for authentication
    API_BASE_PATH: str = "/v1"
    
    # Model configuration
    MAX_TOKENS: int = 4096
    TEMPERATURE: float = 0.7
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
